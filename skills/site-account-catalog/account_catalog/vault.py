import os
from pathlib import Path
import secrets
import time

from . import crypto, protectors
from .adapters import binding
from .codec import Failure, canonical, fields, identifier, version
from .storage import atomic_json, check_path, read_json


def manifest(record):
    fields(record, ("schema_version", "generation", "key_id", "protector", "bindings"))
    version(record)
    for field in ("generation", "key_id"):
        identifier(record[field])
    if record["protector"] not in {crypto.PORTABLE, protectors.DPAPI, protectors.SYSTEMD}:
        raise Failure("unavailable")
    if not isinstance(record["bindings"], list) or len(record["bindings"]) > 100:
        raise Failure()
    ids = [binding(row)["target_id"] for row in record["bindings"]]
    if len(ids) != len(set(ids)):
        raise Failure()
    return record


class Vault:
    def __init__(self, store):
        self.store, self.key, self.key_id = store, None, None

    def metadata(self):
        return manifest(self.store.read("manifest.json"))

    def locked(self):
        try:
            state = self.store.read("state.json")
            fields(state, ("schema_version", "locked", "unlock_until"))
            version(state)
            if type(state["unlock_until"]) not in (int, float):
                return True
            return state["locked"] is not False or not time.time() < state["unlock_until"] <= time.time() + 901
        except Failure:
            return True

    def lock(self):
        self.store.write(("state.json",), {"schema_version": 1, "locked": True, "unlock_until": 0})
        self.drop_key()

    def drop_key(self):
        self.key, self.key_id = None, None

    def unlock(self, phrase=None):
        meta = self.metadata()
        wrapped = self.store.read(meta["generation"], "key.json")
        key = protectors.unwrap(wrapped, meta["protector"], meta["key_id"], self.store.broker, phrase)
        self.store.write(("state.json",), {"schema_version": 1, "locked": False, "unlock_until": time.time() + 900})
        self.key, self.key_id = key, meta["key_id"]

    def values(self, meta, credential_id):
        if self.locked():
            self.drop_key()
            raise Failure("unlock_required")
        if self.key_id != meta["key_id"]:
            self.drop_key()
            if meta["protector"] == crypto.PORTABLE:
                raise Failure("unlock_required")
            wrapped = self.store.read(meta["generation"], "key.json")
            self.key = protectors.unwrap(wrapped, meta["protector"], meta["key_id"], self.store.broker)
            self.key_id = meta["key_id"]
        return crypto.open_credential(self.store.read(meta["generation"], identifier(credential_id) + ".json"),
                                      credential_id, meta["key_id"], self.key)

    def save(self, credential_id, values):
        meta = self.metadata()
        if self.locked() or self.key_id != meta["key_id"]:
            raise Failure("unlock_required")
        folder = check_path(self.store.path(meta["generation"]), self.store.broker)
        nonces = []
        for path in folder.glob("*.json"):
            if path.name != "key.json":
                record = self.store.read(meta["generation"], path.name)
                nonces.append(crypto.decode(record["nonce_b64"], 12))
        document = crypto.seal(credential_id, meta["key_id"], self.key, values, nonces)
        self.store.write((meta["generation"], credential_id + ".json"), document)

    def register(self, target):
        binding(target)
        meta = self.metadata()
        if self.locked():
            raise Failure("unlock_required")
        if not self.store.path(meta["generation"], target["credential_id"] + ".json").exists():
            raise Failure("not_found")
        meta["bindings"] = [row for row in meta["bindings"] if row["target_id"] != target["target_id"]] + [target]
        self.store.write(("manifest.json",), manifest(meta))

    def initialize(self, recovery_path, phrase, protector=crypto.PORTABLE):
        if self.store.path("manifest.json").exists():
            raise Failure()
        self.lock()
        key_id, key = self._new_key(protector)
        generation = "gen-" + secrets.token_hex(12)
        self._recovery(recovery_path, key_id, key)
        self._stage(generation, key_id, key, phrase, protector, {})
        self.store.write(("manifest.json",), {"schema_version": 1, "generation": generation,
                         "key_id": key_id, "protector": protector, "bindings": []}, exclusive=True)
        self.drop_key()

    def _new_key(self, protector):
        if protector == protectors.SYSTEMD:
            record = protectors.systemd_payload(self.store.broker)
            key_id = identifier(record["key_id"])
            for folder in self.store.root.glob("gen-*"):
                if self.store.read(folder.name, "key.json")["key_id"] == key_id:
                    raise Failure()
            return key_id, crypto.recover(record, key_id)
        return "key-" + secrets.token_hex(12), crypto.new_key()

    def _recovery(self, path, key_id, key):
        path = Path(path).absolute()
        if path.is_relative_to(self.store.root):
            raise Failure("not_authorized")
        check_path(path.parent, self.store.broker)
        record = crypto.key_payload(key_id, key)
        atomic_json(path, record, exclusive=True)
        check_path(path, self.store.broker)
        if crypto.recover(read_json(path), key_id) != key:
            raise Failure()

    def _stage(self, generation, key_id, key, phrase, protector, documents):
        folder = self.store.path(generation)
        folder.mkdir(mode=0o700)
        check_path(folder, self.store.broker)
        wrapped = protectors.wrap(protector, key_id, key, phrase)
        self.store.write((generation, "key.json"), wrapped, exclusive=True)
        if protectors.unwrap(self.store.read(generation, "key.json"), protector, key_id, self.store.broker, phrase) != key:
            raise Failure()
        nonces = set()
        for credential_id, values in documents.items():
            record = crypto.seal(credential_id, key_id, key, values, nonces)
            nonces.add(crypto.decode(record["nonce_b64"], 12))
            self.store.write((generation, credential_id + ".json"), record, exclusive=True)
            if crypto.open_credential(self.store.read(generation, credential_id + ".json"), credential_id, key_id, key) != values:
                raise Failure()

    def restore(self, source, recovery_path, new_recovery_path, phrase, protector=crypto.PORTABLE):
        old_meta = manifest(source.read("manifest.json"))
        old_key = crypto.recover(read_json(check_path(recovery_path, self.store.broker)), old_meta["key_id"])
        documents = {}
        folder = check_path(source.path(old_meta["generation"]), source.broker)
        for path in folder.glob("*.json"):
            if path.name != "key.json":
                credential_id = identifier(path.stem)
                documents[credential_id] = crypto.open_credential(source.read(old_meta["generation"], path.name),
                                                                 credential_id, old_meta["key_id"], old_key)
        key_id, key = self._new_key(protector)
        if key_id == old_meta["key_id"] or key == old_key:
            raise Failure()
        generation = "gen-" + secrets.token_hex(12)
        self._recovery(new_recovery_path, key_id, key)
        self._stage(generation, key_id, key, phrase, protector, documents)
        self.lock()
        self.store.write(("manifest.json",), {"schema_version": 1, "generation": generation, "key_id": key_id,
                         "protector": protector, "bindings": []})
        self.drop_key()

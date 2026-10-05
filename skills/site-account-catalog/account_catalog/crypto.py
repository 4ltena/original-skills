import os

from cryptography.exceptions import InvalidTag, UnsupportedAlgorithm
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

from .codec import Failure, canonical, decode, encode, fields, identifier, loads, version

PROTECTION = "aes-256-gcm-v1"
PORTABLE = "portable-passphrase-v1"
KDF = {"name": "argon2id", "version": 19, "memory_kib": 65536, "iterations": 3, "lanes": 4}


def new_key():
    return os.urandom(32)


def _key(key):
    if not isinstance(key, bytes) or len(key) != 32:
        raise Failure()
    return key


def _aad(namespace, meta):
    return canonical({"namespace": namespace, "metadata": meta})


def seal(credential_id, key_id, key, payload, used_nonces=()):
    identifier(credential_id)
    identifier(key_id)
    _key(key)
    fields(payload, (), ("username", "password", "passphrase", "token", "license_key"))
    if not payload or any(not isinstance(v, str) or len(v.encode("utf-8")) > 8192 for v in payload.values()):
        raise Failure()
    nonce = os.urandom(12)
    if nonce in used_nonces:
        raise Failure()
    meta = {"schema_version": 1, "credential_id": credential_id, "key_id": key_id, "protection": PROTECTION}
    plain = canonical({**meta, "values": payload})
    return {**meta, "nonce_b64": encode(nonce),
            "payload_b64": encode(AESGCM(key).encrypt(nonce, plain, _aad("account-catalog/credential/v1", meta)))}


def open_credential(record, credential_id, key_id, key):
    fields(record, ("schema_version", "credential_id", "key_id", "protection", "nonce_b64", "payload_b64"))
    version(record)
    identifier(credential_id)
    identifier(key_id)
    if record["credential_id"] != credential_id or record["key_id"] != key_id or record["protection"] != PROTECTION:
        raise Failure()
    meta = {k: record[k] for k in ("schema_version", "credential_id", "key_id", "protection")}
    try:
        plain = AESGCM(_key(key)).decrypt(decode(record["nonce_b64"], 12), decode(record["payload_b64"]),
                                         _aad("account-catalog/credential/v1", meta))
    except InvalidTag:
        raise Failure() from None
    payload = loads(plain)
    fields(payload, (*meta, "values"))
    if any(payload[k] != v for k, v in meta.items()):
        raise Failure()
    values = payload["values"]
    fields(values, (), ("username", "password", "passphrase", "token", "license_key"))
    if not values or any(not isinstance(v, str) or len(v.encode("utf-8")) > 8192 for v in values.values()):
        raise Failure()
    return values


def key_payload(key_id, key):
    return {"schema_version": 1, "key_id": identifier(key_id), "key_b64": encode(_key(key))}


def recover(record, key_id):
    fields(record, ("schema_version", "key_id", "key_b64"))
    version(record)
    if record["key_id"] != identifier(key_id):
        raise Failure()
    return decode(record["key_b64"], 32)


def _derive(phrase, salt):
    if not isinstance(phrase, str) or not 20 <= len(phrase) <= 1024:
        raise Failure("unlock_required")
    try:
        return Argon2id(salt=salt, length=32, iterations=3, lanes=4, memory_cost=65536).derive(phrase.encode("utf-8"))
    except (UnsupportedAlgorithm, MemoryError):
        raise Failure("unavailable") from None


def wrap_portable(key_id, key, phrase):
    salt, nonce = os.urandom(16), os.urandom(12)
    meta = {"schema_version": 1, "protector": PORTABLE, "key_id": identifier(key_id),
            "kdf": dict(KDF), "salt_b64": encode(salt)}
    return {**meta, "nonce_b64": encode(nonce), "payload_b64": encode(AESGCM(_derive(phrase, salt)).encrypt(
        nonce, canonical(key_payload(key_id, key)), _aad("account-catalog/key-wrap/v1", meta)))}


def unwrap_portable(record, key_id, phrase):
    fields(record, ("schema_version", "protector", "key_id", "kdf", "salt_b64", "nonce_b64", "payload_b64"))
    version(record)
    if record["protector"] != PORTABLE or record["key_id"] != identifier(key_id) or record["kdf"] != KDF:
        raise Failure()
    if any(type(record["kdf"][k]) is not type(v) for k, v in KDF.items()):
        raise Failure()
    meta = {k: record[k] for k in ("schema_version", "protector", "key_id", "kdf", "salt_b64")}
    try:
        plain = AESGCM(_derive(phrase, decode(record["salt_b64"], 16))).decrypt(
            decode(record["nonce_b64"], 12), decode(record["payload_b64"], maximum=2048),
            _aad("account-catalog/key-wrap/v1", meta))
    except InvalidTag:
        raise Failure("unlock_required") from None
    return recover(loads(plain), key_id)

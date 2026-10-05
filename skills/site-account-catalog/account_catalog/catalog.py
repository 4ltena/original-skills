from pathlib import Path

from .codec import Failure, identifier, loads
from .storage import read_json

SECRET_FIELDS = {"password", "passphrase", "private_key", "private_key_path", "public_key_path",
                 "token", "api_token", "access_token", "refresh_token", "cookie", "cookies",
                 "recovery_key", "key_b64", "license_key", "activation_code", "secret"}
PUBLIC_FIELDS = {"username", "display_name", "profile_url", "role", "rights_holder", "licensee"}
KINDS = {"targets", "accounts", "identities", "licenses", "notations", "entitlements"}
SCHEMA = {
    "targets": {"service", "environment", "domains", "aliases", "account_id", "actions"},
    "accounts": {"identity_id", "service"},
    "identities": {"username", "display_name", "profile_url", "role", "rights_holder", "licensee", "source_url"},
    "licenses": {"name", "spdx_expression", "source_url"},
    "notations": {"wording", "rights_holder_id", "licensee_id", "license_ids", "subject", "source_url"},
    "entitlements": {"product", "plan", "account_id", "checked_at", "expires_at", "source_url"},
}


def _nonsecret(value, depth=0):
    if depth > 16:
        raise Failure()
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower().replace("-", "_") in SECRET_FIELDS:
                raise Failure()
            _nonsecret(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _nonsecret(item, depth + 1)


class Catalog:
    def __init__(self, root):
        self.root = Path(root)

    def read(self, kind, record_id):
        if kind not in KINDS:
            raise Failure()
        identifier(record_id)
        path = self.root / kind / (record_id + ".json")
        if not path.exists():
            raise Failure("not_found")
        record = read_json(path)
        if not isinstance(record, dict) or type(record.get("schema_version")) is not int or record["schema_version"] != 2:
            raise Failure()
        if record.get("id") != record_id:
            raise Failure()
        if set(record) - {"id", "schema_version"} - SCHEMA[kind]:
            raise Failure()
        for name, value in record.items():
            if name in {"domains", "aliases", "actions", "license_ids"}:
                if not isinstance(value, list) or any(not isinstance(item, str) or len(item) > 256 for item in value):
                    raise Failure()
                if name == "license_ids":
                    for item in value:
                        identifier(item)
            elif name != "schema_version" and (not isinstance(value, str) or len(value) > 8192):
                raise Failure()
            if name.endswith("_id"):
                identifier(value)
        _nonsecret(record)
        return record

    def legacy(self, site_id):
        identifier(site_id)
        path = self.root / "entries" / (site_id + ".json")
        if not path.exists():
            raise Failure("not_found")
        record = read_json(path)
        if (not isinstance(record, dict) or type(record.get("schema_version")) is not int
                or record["schema_version"] != 1 or record.get("id") != site_id):
            raise Failure()
        _nonsecret(record)
        for array in ("accounts", "license_notations"):
            rows = record.get(array)
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise Failure()
            ids = [identifier(row.get("id")) for row in rows]
            if len(ids) != len(set(ids)):
                raise Failure()
        return record

    def identity(self, identity_id, field, site_id=None):
        if field not in PUBLIC_FIELDS:
            raise Failure()
        if site_id is None:
            try:
                record = self.read("identities", identity_id)
            except Failure as exc:
                if exc.code == "not_found":
                    return {"status": "needs_user", "missing": [field]}
                raise
        else:
            rows = [row for row in self.legacy(site_id)["accounts"] if row["id"] == identity_id]
            if not rows:
                return {"status": "needs_user", "missing": [field]}
            record = rows[0]
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            return {"status": "needs_user", "missing": [field]}
        return {"status": "confirmed", "value": value}

    def notation(self, notation_id):
        record = self.read("notations", notation_id)
        text = record.get("wording")
        if not isinstance(text, str) or not text.strip():
            return {"status": "needs_user", "missing": ["wording"]}
        for field in ("rights_holder_id", "licensee_id"):
            if field in record:
                value = self.identity(identifier(record[field]), "display_name")
                if value["status"] != "confirmed":
                    return {"status": "needs_user", "missing": [field]}
        return {"status": "confirmed", "value": text}

    def find(self, query):
        if not isinstance(query, str) or not 1 <= len(query) <= 256:
            raise Failure()
        key = query.casefold()
        matches = []
        for kind in ("entries", "targets"):
            folder = self.root / kind
            if not folder.exists():
                continue
            for path in sorted(folder.glob("*.json"))[:1000]:
                record = self.legacy(path.stem) if kind == "entries" else self.read(kind, path.stem)
                terms = [record.get("service", ""), record["id"]]
                aliases, domains = record.get("aliases", []), record.get("domains", [])
                if not isinstance(aliases, list) or not isinstance(domains, list):
                    raise Failure()
                terms += aliases + domains
                if any(not isinstance(term, str) for term in terms):
                    raise Failure()
                if key in {term.casefold() for term in terms}:
                    matches.append({"id": record["id"], "kind": kind})
        return {"status": "found" if len(matches) == 1 else "needs_user", "matches": matches}

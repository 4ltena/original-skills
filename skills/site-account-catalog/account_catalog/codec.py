import base64
import json
import re

LIMIT = 65536
ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z", re.ASCII)
ERRORS = frozenset({"not_found", "not_authorized", "unlock_required", "authentication_failed",
                    "host_key_mismatch", "timeout", "unavailable", "invalid_record"})


class Failure(Exception):
    def __init__(self, code="invalid_record"):
        self.code = code if code in ERRORS else "invalid_record"
        super().__init__(self.code)


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise Failure()
    return value


def fields(record, required, optional=()):
    if not isinstance(record, dict) or set(record) - set(required) - set(optional) or set(required) - set(record):
        raise Failure()
    return record


def version(record):
    if type(record.get("schema_version")) is not int or record["schema_version"] != 1:
        raise Failure()


def _pairs(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise Failure()
        result[name] = value
    return result


def loads(data, limit=LIMIT):
    try:
        if not isinstance(data, bytes) or len(data) > limit:
            raise Failure()
        return json.loads(data.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(Failure()))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise Failure() from None


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise Failure() from None


def encode(value):
    return base64.b64encode(value).decode("ascii")


def decode(value, length=None, maximum=LIMIT):
    try:
        if not isinstance(value, str) or len(value) > maximum * 2:
            raise Failure()
        raw = base64.b64decode(value, validate=True)
        if len(raw) > maximum or (length is not None and len(raw) != length) or encode(raw) != value:
            raise Failure()
        return raw
    except (ValueError, UnicodeError):
        raise Failure() from None


def result(target, status="authenticated", error=None, healthy=None):
    out = {"schema_version": 1, "target_id": identifier(target), "status": status}
    if status not in {"authenticated", "needs_user", "failed"}:
        raise Failure()
    if error is not None:
        if error not in ERRORS:
            raise Failure()
        out["error_code"] = error
    if healthy is not None:
        if type(healthy) is not bool:
            raise Failure()
        out["healthy"] = healthy
    return out

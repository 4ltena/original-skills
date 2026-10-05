import os
import sys
from pathlib import Path

from .codec import Failure, canonical, decode, encode, fields, loads, version
from .crypto import PORTABLE, key_payload, recover, unwrap_portable, wrap_portable
from .storage import check_path

DPAPI = "windows-dpapi-user-v1"
SYSTEMD = "linux-systemd-credential-v1"


def wrap(protector, key_id, key, phrase=None):
    if protector == PORTABLE:
        return wrap_portable(key_id, key, phrase)
    if protector == DPAPI:
        from .windows import dpapi
        return {"schema_version": 1, "protector": DPAPI, "key_id": key_id,
                "payload_b64": encode(dpapi(canonical(key_payload(key_id, key))))}
    if protector == SYSTEMD:
        return {"schema_version": 1, "protector": SYSTEMD, "key_id": key_id,
                "credential_name": "account-catalog-key"}
    raise Failure("unavailable")


def unwrap(record, protector, key_id, broker, phrase=None):
    if protector == PORTABLE:
        return unwrap_portable(record, key_id, phrase)
    if protector == DPAPI:
        fields(record, ("schema_version", "protector", "key_id", "payload_b64"))
        version(record)
        if record["protector"] != DPAPI or record["key_id"] != key_id:
            raise Failure()
        from .windows import dpapi
        return recover(loads(dpapi(decode(record["payload_b64"], maximum=8192), True)), key_id)
    if protector == SYSTEMD:
        fields(record, ("schema_version", "protector", "key_id", "credential_name"))
        version(record)
        if (sys.platform != "linux" or record["protector"] != SYSTEMD or record["key_id"] != key_id
                or record["credential_name"] != "account-catalog-key"):
            raise Failure("unavailable")
        return recover(systemd_payload(broker), key_id)
    raise Failure("unavailable")


def systemd_payload(broker):
    if sys.platform != "linux":
        raise Failure("unavailable")
    directory = os.environ.get("CREDENTIALS_DIRECTORY")
    if not directory or not Path(directory).is_absolute():
        raise Failure("unavailable")
    path = check_path(Path(directory) / "account-catalog-key", broker)
    try:
        with path.open("rb") as file:
            record = loads(file.read(2049), limit=2048)
        recover(record, record.get("key_id"))
        return record
    except OSError:
        raise Failure("unavailable") from None

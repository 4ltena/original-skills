import os
from pathlib import Path
import stat
import tempfile

from .codec import Failure, LIMIT, canonical, fields, loads, version


def principal():
    if os.name == "nt":
        from .windows import current_sid
        return current_sid()
    return str(os.getuid())


def unprivileged():
    if os.name == "nt":
        from .windows import privileged
        if privileged():
            raise Failure("not_authorized")
    elif os.getuid() == 0 or os.geteuid() != os.getuid():
        raise Failure("not_authorized")


def check_path(path, broker, secret=True):
    path = Path(path).absolute()
    try:
        parts = [path, *path.parents]
        for i, item in enumerate(parts):
            info = item.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise Failure("not_authorized")
            if os.name == "nt":
                from .windows import private_acl
                private_acl(item, broker, secret=secret and i == 0)
            else:
                if info.st_uid not in {int(broker), 0}:
                    raise Failure("not_authorized")
                if info.st_mode & (0o077 if secret and i == 0 else 0o022):
                    raise Failure("not_authorized")
    except OSError:
        raise Failure("not_authorized") from None
    return path


def read_json(path):
    try:
        with Path(path).open("rb") as file:
            return loads(file.read(LIMIT + 1))
    except OSError:
        raise Failure("invalid_record") from None


def atomic_json(path, value, exclusive=False):
    path = Path(path)
    data = canonical(value)
    if len(data) > LIMIT:
        raise Failure()
    if os.name == "nt":
        from .windows import private_temp
        fd, name = private_temp(path.parent)
    else:
        fd, name = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        if exclusive:
            os.link(name, path)
            os.unlink(name)
        else:
            os.replace(name, path)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def roles(record, broker):
    fields(record, ("schema_version", "broker_id", "agent_ids"))
    version(record)
    agents = record["agent_ids"]
    if (record["broker_id"] != broker or not isinstance(agents, list) or not agents
            or len(agents) > 32 or any(not isinstance(item, str) or not item for item in agents)
            or len(agents) != len(set(agents)) or broker in agents
            or any(item in {"0", "S-1-5-18", "S-1-5-32-544"} for item in agents)):
        raise Failure("not_authorized")
    return frozenset(agents)


def deployment_roles(store):
    path = check_path(store.path("deployment.json"), store.broker)
    if os.name == "nt":
        from .windows import deployment_acl
        deployment_acl(path, store.broker)
    else:
        info = path.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise Failure("not_authorized")
    return roles(store.read("deployment.json"), store.broker)


class Store:
    def __init__(self, root, broker):
        self.root = Path(root).absolute()
        self.broker = broker
        check_path(self.root, broker)

    def path(self, *parts):
        target = self.root.joinpath(*parts)
        if not target.is_relative_to(self.root):
            raise Failure()
        return target

    def read(self, *parts):
        path = check_path(self.path(*parts), self.broker)
        return read_json(path)

    def write(self, parts, value, exclusive=False):
        path = self.path(*parts)
        check_path(path.parent, self.broker)
        if path.exists():
            check_path(path, self.broker)
        atomic_json(path, value, exclusive)

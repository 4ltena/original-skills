"""Generation-bound creation/update/deletion. Never adopts an existing Skill."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

MAXIMUM = 2 * 1024 * 1024
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
FORBIDDEN = {"synced", "vendor", "cache", "plugins", "profile", "memory"}


class OwnedError(ValueError):
    pass


def parse(raw):
    if len(raw) > MAXIMUM:
        raise OwnedError("registry too large")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise OwnedError("object required")
    return value


def check_slug(slug):
    if not isinstance(slug, str) or not SLUG.fullmatch(slug) or slug in FORBIDDEN:
        raise OwnedError("invalid managed slug")
    return slug


def validate_manifest(manifest):
    if not isinstance(manifest, dict) or set(manifest) != {'dirs', 'files'}:
        raise OwnedError('invalid manifest')
    if not all(isinstance(manifest[k], dict) for k in ('dirs', 'files')) or '' not in manifest['dirs'] or 'SKILL.md' not in manifest['files']:
        raise OwnedError('invalid payload manifest')
    for kind in ('dirs', 'files'):
        for path, value in manifest[kind].items():
            if not isinstance(path, str) or (path and any(not p or p in {'.', '..'} or '\\' in p or ':' in p for p in path.split('/'))):
                raise OwnedError('invalid manifest path')
            ident = value if kind == 'dirs' else value.get('id') if isinstance(value, dict) else None
            if not isinstance(ident, list) or len(ident) != 2 or any(type(n) is not int or n < 0 for n in ident):
                raise OwnedError('invalid manifest identity')
            if kind == 'files' and (set(value) != {'id', 'size', 'mtime', 'ctime', 'sha256'}
                    or not re.fullmatch(r'[a-f0-9]{64}', str(value.get('sha256', '')))
                    or any(type(value.get(k)) is not int or value[k] < 0 for k in ('size', 'mtime', 'ctime'))):
                raise OwnedError('invalid file manifest')


def validate_ledger(ledger):
    if not isinstance(ledger, dict) or set(ledger) != {'version', 'roots', 'entries'} or ledger['version'] != 1:
        raise OwnedError('invalid ledger version/schema')
    if not isinstance(ledger['roots'], dict) or not isinstance(ledger['entries'], dict):
        raise OwnedError('invalid ledger maps')
    for key, record in ledger['entries'].items():
        if not isinstance(record, dict) or not isinstance(record.get('root'), str) or not Path(record['root']).is_absolute():
            raise OwnedError('invalid registered root')
        check_slug(record.get('slug'))
        if key != hashlib.sha256((record['root'] + '\0' + record['slug']).encode()).hexdigest():
            raise OwnedError('invalid entry key')
        generation = record.get('generation')
        if not isinstance(generation, str) or not re.fullmatch(r'[a-f0-9]{32}', generation):
            raise OwnedError('invalid generation')
        state = record.get('state')
        if state not in {'creating', 'prepared-create', 'active', 'preparing-update', 'prepared-update', 'deleting', 'deleted'}:
            raise OwnedError('invalid transaction state')
        if state not in {'creating', 'deleted'}:
            validate_manifest(record.get('manifest'))
        if state in {'creating', 'prepared-create'} and record.get('stage') != '.gl-stage-' + generation:
            raise OwnedError('invalid creation stage')
        if state in {'preparing-update', 'prepared-update'}:
            validate_manifest(record.get('old'))
            if not re.fullmatch(r'\.gl-update-[a-f0-9]{32}', str(record.get('stage', ''))) or record.get('waiting') != '.gl-old-' + generation:
                raise OwnedError('invalid update intent')
        if state == 'deleting' and record.get('waiting') != '.gl-delete-' + generation:
            raise OwnedError('invalid deletion intent')
    return ledger


def identity(info):
    return [info.st_dev, info.st_ino]


def exclusive_rename(fd, source, target):
    """No check-then-overwrite fallback: require native exclusive rename."""
    import ctypes
    libc = ctypes.CDLL(None, use_errno=True)
    name, flag = ('renameatx_np', 4) if sys.platform == 'darwin' else ('renameat2', 1)
    function = getattr(libc, name, None)
    if function is None:
        raise OwnedError('atomic exclusive rename is unavailable')
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    if function(fd, os.fsencode(source), fd, os.fsencode(target), flag):
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number))


class PosixFS:
    def __init__(self, fd):
        self.fd = fd

    @classmethod
    @contextlib.contextmanager
    def root(cls, path):
        path = Path(path).absolute()
        fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
        try:
            for part in path.parts[1:]:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd); fd = child
            info = os.fstat(fd)
            if info.st_uid != os.getuid() or info.st_mode & 0o022:
                raise OwnedError("managed root must be user-owned and not writable by others")
            yield cls(fd)
        finally:
            os.close(fd)

    def ident(self):
        return identity(os.fstat(self.fd))

    def exists(self, name):
        try:
            os.stat(name, dir_fd=self.fd, follow_symlinks=False); return True
        except FileNotFoundError:
            return False

    def mkdir(self, name):
        os.mkdir(name, mode=0o700, dir_fd=self.fd)

    @contextlib.contextmanager
    def directory(self, name):
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.fd)
        try:
            info = os.fstat(fd)
            if info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise OwnedError("managed directories must be private")
            yield type(self)(fd)
        finally:
            os.close(fd)

    def names(self):
        return sorted(os.listdir(self.fd))

    def kind(self, name):
        info = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
        if stat.S_ISDIR(info.st_mode):
            return "dir"
        if stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
            return "file"
        raise OwnedError("symlink, hardlink or special file")

    def read(self, name):
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.fd)
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid()
                    or info.st_mode & 0o077 or info.st_size > MAXIMUM):
                raise OwnedError("unsafe payload file")
            raw = handle.read(MAXIMUM + 1)
            after = os.fstat(handle.fileno())
            # Reading may advance atime. Compare content/ownership identity instead.
            stable = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns',
                      'st_uid', 'st_mode', 'st_nlink')
            if any(getattr(after, key) != getattr(info, key) for key in stable):
                raise OwnedError("payload changed while reading")
            return raw, {"id": identity(info), "size": info.st_size,
                         "mtime": info.st_mtime_ns, "ctime": info.st_ctime_ns,
                         "sha256": hashlib.sha256(raw).hexdigest()}

    def write(self, name, raw):
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw); handle.flush(); os.fsync(handle.fileno())
        os.fsync(self.fd)

    def move(self, source, target, expected):
        if self.exists(target):
            raise OwnedError("move destination already exists")
        with self.directory(source) as original:
            if original.ident() != expected:
                raise OwnedError("directory replaced before move")
            exclusive_rename(self.fd, source, target)
            os.fsync(self.fd)
            with self.directory(target) as moved:
                if moved.ident() != expected or moved.ident() != original.ident():
                    raise OwnedError("directory raced during move; preserved without deletion")

    def unlink(self, name, expected):
        _, actual = self.read(name)
        if actual != expected:
            raise OwnedError("file changed before deletion")
        os.unlink(name, dir_fd=self.fd)
        os.fsync(self.fd)

    def rmdir(self, name, expected):
        with self.directory(name) as directory:
            if directory.ident() != expected or directory.names():
                raise OwnedError("directory changed before deletion")
            os.rmdir(name, dir_fd=self.fd)
        os.fsync(self.fd)


class PosixLedger:
    def __init__(self, data):
        self.data = Path(data).absolute()

    def __enter__(self):
        import fcntl
        self.context = PosixFS.root(self.data)
        self.parent = self.context.__enter__()
        try:
            if not self.parent.exists("growth-loop-owned"):
                self.parent.mkdir("growth-loop-owned")
            self.child_context = self.parent.directory("growth-loop-owned")
            self.fs = self.child_context.__enter__()
            self.lock = os.open("ledger.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=self.fs.fd)
            info = os.fstat(self.lock)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077 or info.st_uid != os.getuid():
                raise OwnedError("unsafe lock")
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return self
        except BaseException:
            self.__exit__(); raise

    def __exit__(self, *args):
        if not args:
            args = (None, None, None)
        if hasattr(self, "lock"):
            os.close(self.lock)
        if hasattr(self, "child_context"):
            self.child_context.__exit__(*args)
        self.context.__exit__(*args)

    def read(self):
        if not self.fs.exists("ledger.json"):
            return {"version": 1, "roots": {}, "entries": {}}
        return parse(self.fs.read("ledger.json")[0])

    def write(self, ledger):
        raw = json.dumps(ledger, ensure_ascii=False, allow_nan=False).encode()
        parse(raw)
        temp = "." + uuid.uuid4().hex + ".tmp"
        self.fs.write(temp, raw)
        os.replace(temp, "ledger.json", src_dir_fd=self.fs.fd, dst_dir_fd=self.fs.fd)
        os.fsync(self.fs.fd)


def tree(fs):
    result = {"dirs": {"": fs.ident()}, "files": {}}
    def walk(directory, prefix):
        for name in directory.names():
            if name in {".", ".."} or "/" in name or "\\" in name:
                raise OwnedError("unsafe filename")
            relative = prefix + name
            if directory.kind(name) == "dir":
                with directory.directory(name) as child:
                    result["dirs"][relative] = child.ident()
                    walk(child, relative + "/")
            else:
                _, record = directory.read(name)
                result["files"][relative] = record
            if len(result["files"]) + len(result["dirs"]) > 1024:
                raise OwnedError("too many payload paths")
    walk(fs, "")
    return result


def verify(root, name, expected, partial=False):
    with root.directory(name) as directory:
        actual = tree(directory)
    for kind in ("dirs", "files"):
        if partial:
            if any(expected[kind].get(path) != value for path, value in actual[kind].items()):
                raise OwnedError("remaining payload differs from deleting intent")
        elif actual[kind] != expected[kind]:
            raise OwnedError("payload changed outside growth-loop")
    return actual


def remove(root, name, manifest):
    """Delete only recorded, rechecked entries. No recursive wildcard deletion."""
    verify(root, name, manifest, partial=True)
    def walk(directory, prefix):
        for child in directory.names():
            key = prefix + child
            if directory.kind(child) == "dir":
                if key not in manifest["dirs"]:
                    raise OwnedError("unregistered directory")
                with directory.directory(child) as nested:
                    if nested.ident() != manifest["dirs"][key]:
                        raise OwnedError("directory replacement")
                    walk(nested, key + "/")
                directory.rmdir(child, manifest["dirs"][key])
            else:
                if key not in manifest["files"]:
                    raise OwnedError("unregistered file")
                directory.unlink(child, manifest["files"][key])
    with root.directory(name) as directory:
        if directory.ident() != manifest["dirs"][""]:
            raise OwnedError("root replacement")
        walk(directory, "")
    root.rmdir(name, manifest["dirs"][""])


def payload_files(payload, slug):
    if not isinstance(payload, dict) or not payload or len(payload) > 1024:
        raise OwnedError("payload is a path -> UTF-8 content object")
    if "SKILL.md" not in payload:
        raise OwnedError("SKILL.md required")
    total = 0
    result = {}
    for name, content in payload.items():
        parts = name.split("/") if isinstance(name, str) else []
        if (not parts or any(not part or part in {".", ".."} or part.startswith(".") or "\\" in part
                            or ":" in part or "\0" in part for part in parts)
                or not isinstance(content, str)):
            raise OwnedError("unsafe payload path/content")
        raw = content.encode("utf-8"); total += len(raw)
        if total > MAXIMUM:
            raise OwnedError("payload too large")
        result[name] = raw
    document = payload["SKILL.md"]
    frontmatter = re.match(r'^---\n(.*?)\n---(?:\n|$)', document, re.S)
    if not frontmatter or not re.search(r"^name:\s*[\"']?" + re.escape(slug) + r"[\"']?\s*$", frontmatter[1], re.M):
        raise OwnedError("Skill name must match slug")
    if not re.search(r"^description:\s*\S", frontmatter[1], re.M):
        raise OwnedError("Skill description required")
    return result


def populate(root, stage, payload):
    root.mkdir(stage)
    with root.directory(stage) as directory:
        for name, raw in sorted(payload.items()):
            parts = name.split("/")
            with contextlib.ExitStack() as stack:
                parent = directory
                for part in parts[:-1]:
                    if not parent.exists(part):
                        parent.mkdir(part)
                    parent = stack.enter_context(parent.directory(part))
                parent.write(parts[-1], raw)
        return tree(directory)


def fault(point):
    # Test-only failures leave precisely the same durable state as process interruption.
    if os.environ.get("GROWTH_LOOP_TEST_FAULT") == point:
        raise OwnedError("injected interruption: " + point)


class Manager:
    def __init__(self, root, data, auto_delete=False):
        self.path = str(Path(root).absolute())
        self.data = str(Path(data).absolute())
        self.auto_delete = auto_delete
        if any(part in {"..", ".system", "synced", "cache", "plugins", "vendor"} for part in Path(self.path).parts):
            raise OwnedError("managed root is a protected source")
        if '..' in Path(self.data).parts:
            raise OwnedError('parent traversal in state path')

    @contextlib.contextmanager
    def transaction(self):
        if os.name == "nt":
            from owned_windows import WindowsFS, WindowsLedger
            fs_type, ledger_type = WindowsFS, WindowsLedger
        else:
            fs_type, ledger_type = PosixFS, PosixLedger
        with fs_type.root(self.path) as fs, ledger_type(self.data) as store:
            ledger = store.read()
            validate_ledger(ledger)
            recorded = ledger["roots"].get(self.path)
            if recorded is not None and recorded != fs.ident():
                raise OwnedError("managed root replaced")
            ledger["roots"][self.path] = fs.ident()
            yield fs, store, ledger

    def key(self, slug):
        return hashlib.sha256((self.path + "\0" + check_slug(slug)).encode()).hexdigest()

    def create(self, slug, payload):
        files = payload_files(payload, check_slug(slug))
        with self.transaction() as (root, store, ledger):
            key = self.key(slug)
            previous = ledger["entries"].get(key)
            if root.exists(slug) or previous and previous.get("state") != "deleted":
                raise OwnedError("target exists or has an unfinished generation")
            generation = uuid.uuid4().hex
            record = {"root": self.path, "slug": slug, "generation": generation,
                      "state": "creating", "stage": ".gl-stage-" + generation}
            ledger["entries"][key] = record; store.write(ledger); fault("create-reserved")
            record["manifest"] = populate(root, record["stage"], files)
            record["state"] = "prepared-create"; store.write(ledger); fault("create-prepared")
            self.finish_publish(root, store, ledger, record)
            return {"generation": generation, "state": "active", "path": str(Path(self.path) / slug)}

    def finish_publish(self, root, store, ledger, record):
        slug, stage = record["slug"], record["stage"]
        if root.exists(stage):
            verify(root, stage, record["manifest"])
            if root.exists(slug):
                raise OwnedError("publish collision")
            root.move(stage, slug, record["manifest"]["dirs"][""])
        verify(root, slug, record["manifest"])
        fault("create-published")
        record["state"] = "active"; record.pop("stage"); store.write(ledger)

    def entry(self, ledger, slug, generation=None):
        record = ledger["entries"].get(self.key(slug))
        if not isinstance(record, dict) or record.get("root") != self.path or record.get("slug") != slug:
            raise OwnedError("not a growth-loop-created Skill")
        if generation is not None and record.get("generation") != generation:
            raise OwnedError("stale generation")
        if not re.fullmatch(r"[a-f0-9]{32}", str(record.get("generation", ""))):
            raise OwnedError("invalid generation")
        return record

    def status(self, slug):
        with self.transaction() as (root, store, ledger):
            record = self.entry(ledger, slug)
            if record["state"] == "active":
                verify(root, slug, record["manifest"])
            return {"generation": record["generation"], "state": record["state"],
                    "path": str(Path(self.path) / slug), "automatic_delete": self.auto_delete}

    def update(self, slug, generation, payload):
        files = payload_files(payload, check_slug(slug))
        with self.transaction() as (root, store, ledger):
            record = self.entry(ledger, slug, generation)
            if record["state"] != "active":
                raise OwnedError("generation is not active")
            verify(root, slug, record["manifest"])
            record["old"] = record["manifest"]
            record["stage"] = ".gl-update-" + uuid.uuid4().hex
            record["waiting"] = ".gl-old-" + generation
            record["state"] = "preparing-update"; store.write(ledger); fault("update-reserved")
            record["manifest"] = populate(root, record["stage"], files)
            record["state"] = "prepared-update"; store.write(ledger); fault("update-prepared")
            self.finish_update(root, store, ledger, record)
            return {"generation": generation, "state": "active"}

    def finish_update(self, root, store, ledger, record):
        slug, stage, waiting = record["slug"], record["stage"], record["waiting"]
        if root.exists(stage):
            verify(root, stage, record["manifest"])
            if root.exists(slug):
                if root.exists(waiting):
                    raise OwnedError("update has conflicting copies")
                verify(root, slug, record["old"])
                root.move(slug, waiting, record["old"]["dirs"][""])
                fault("update-old-moved")
            elif not root.exists(waiting):
                raise OwnedError("old generation missing")
            verify(root, waiting, record["old"], partial=True)
            root.move(stage, slug, record["manifest"]["dirs"][""])
        verify(root, slug, record["manifest"]); fault("update-published")
        if root.exists(waiting):
            remove(root, waiting, record["old"])
        record["state"] = "active"
        for key in ("stage", "old", "waiting"):
            record.pop(key)
        store.write(ledger)

    def delete(self, slug, generation, reason):
        if not self.auto_delete:
            raise OwnedError("owned automatic deletion is not enabled")
        if reason not in {"obsolete", "duplicate-merged", "explicit-request"}:
            raise OwnedError("evidence-based deletion reason required; age/name is insufficient")
        with self.transaction() as (root, store, ledger):
            record = self.entry(ledger, slug, generation)
            if record["state"] != "active":
                raise OwnedError("generation is not active")
            verify(root, slug, record["manifest"])
            record["state"] = "deleting"; record["waiting"] = ".gl-delete-" + generation
            store.write(ledger); fault("delete-intent")
            self.finish_delete(root, store, ledger, record)
            return {"generation": generation, "state": "deleted"}

    def finish_delete(self, root, store, ledger, record):
        slug, waiting = record["slug"], record["waiting"]
        if root.exists(slug):
            if root.exists(waiting):
                raise OwnedError("delete has conflicting copies")
            verify(root, slug, record["manifest"])
            root.move(slug, waiting, record["manifest"]["dirs"][""])
        if root.exists(waiting):
            verify(root, waiting, record["manifest"], partial=True); fault("delete-moved")
            remove(root, waiting, record["manifest"]); fault("delete-removed")
        # Neither source nor waiting exists: only close this generation, never find another by name.
        record.clear(); record.update({"root": self.path, "slug": slug,
            "generation": waiting.removeprefix(".gl-delete-"), "state": "deleted"})
        store.write(ledger)

    def recover(self, slug, generation):
        with self.transaction() as (root, store, ledger):
            record = self.entry(ledger, slug, generation)
            if record["state"] == "prepared-create":
                self.finish_publish(root, store, ledger, record)
            elif record["state"] == "prepared-update":
                self.finish_update(root, store, ledger, record)
            elif record["state"] == "deleting" and self.auto_delete:
                self.finish_delete(root, store, ledger, record)
            else:
                raise OwnedError("incomplete/unverified transaction requires inspection, not adoption")
            return {"generation": generation, "state": record["state"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("create", "status", "update", "delete", "recover"))
    parser.add_argument("slug")
    parser.add_argument("--generation")
    parser.add_argument("--reason", choices=("obsolete", "duplicate-merged", "explicit-request"))
    parser.add_argument("--binding", default=str(Path(__file__).resolve().parents[1] / "binding.json"))
    args = parser.parse_args()
    try:
        binding = parse(Path(args.binding).read_bytes())
        root, data = Path(binding["root"]), Path(binding["data"])
        if not root.is_absolute() or not data.is_absolute() or type(binding.get("version")) is not int or binding["version"] != 1:
            raise OwnedError("invalid local binding")
        # Bootstrap only the explicit state directory, never a skill path inferred from its name.
        for path in [*reversed(data.parents), data]:
            if path.is_symlink() or path.exists() and getattr(path.lstat(), 'st_file_attributes', 0) & 0x400:
                raise OwnedError('unsafe state path')
        data.mkdir(mode=0o700, parents=True, exist_ok=True)
        manager = Manager(root, data, binding.get("auto_delete") is True)
        if args.operation in {"delete", "update", "recover"} and not args.generation:
            raise OwnedError("generation required")
        if args.operation == "create":
            result = manager.create(args.slug, parse(sys.stdin.buffer.read(MAXIMUM + 1)))
        elif args.operation == "update":
            result = manager.update(args.slug, args.generation, parse(sys.stdin.buffer.read(MAXIMUM + 1)))
        elif args.operation == "delete":
            result = manager.delete(args.slug, args.generation, args.reason)
        elif args.operation == "recover":
            result = manager.recover(args.slug, args.generation)
        else:
            result = manager.status(args.slug)
        print(json.dumps(result, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("growth-loop owned: " + str(exc), file=sys.stderr); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

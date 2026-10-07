"""Windows ownership filesystem: pin ancestors, reject reparse points, delete by handle."""
import contextlib
import ctypes as c
from ctypes import wintypes as w
import hashlib
import os
from pathlib import Path

from owned import OwnedError, MAXIMUM, parse
import owned_windows_store as win

set_info = win.bind(win.k, 'SetFileInformationByHandle', [w.HANDLE, c.c_int, c.c_void_p, w.DWORD])
DELETE = 0x10000


def ident(details):
    return [details.volume, (details.index_high << 32) | details.index_low]


class WindowsFS:
    def __init__(self, path, store, handle):
        self.path, self.store, self.handle = Path(path), store, handle

    @classmethod
    @contextlib.contextmanager
    def root(cls, path):
        store = win.WindowsStore(path, error=OwnedError, bounded_json=parse, max_state=MAXIMUM)
        try:
            for ancestor in [*reversed(Path(path).parents), Path(path)]:
                handle = store._open(ancestor, directory=True)
                store.handles.append(handle)
                store._check(handle, directory=True, security=False)
            yield cls(path, store, store.handles[-1])
        finally:
            store.__exit__()

    def ident(self):
        return ident(self.store._check(self.handle, directory=True, security=False))

    def target(self, name):
        if not name or '/' in name or '\\' in name or name in {'.', '..'}:
            raise OwnedError('invalid child name')
        return self.path / name

    def exists(self, name):
        try:
            self.target(name).lstat(); return True
        except FileNotFoundError:
            return False

    def mkdir(self, name):
        win.checked(win.mkdir(str(self.target(name)), c.byref(self.store.sa)))

    @contextlib.contextmanager
    def directory(self, name):
        target = self.target(name)
        handle = self.store._open(target, directory=True)
        try:
            self.store._check(handle, directory=True)
            yield type(self)(target, self.store, handle)
        finally:
            win.close(handle)

    def names(self):
        # The directory handle denies delete sharing while enumeration uses its pinned path.
        return sorted(os.listdir(self.path))

    def kind(self, name):
        details = self.target(name).lstat()
        if getattr(details, 'st_file_attributes', 0) & 0x400:
            raise OwnedError('reparse point')
        if self.target(name).is_dir():
            return 'dir'
        if self.target(name).is_file():
            return 'file'
        raise OwnedError('special file')

    def read_handle(self, handle):
        info = self.store._check(handle)
        buffer, count = c.create_string_buffer(MAXIMUM + 1), w.DWORD()
        win.checked(win.readfile(handle, buffer, MAXIMUM + 1, c.byref(count), None))
        after = self.store._check(handle)
        if bytes(info) != bytes(after):
            # Last-access timestamp may change while reading; compare write/identity/size instead.
            if (ident(info), info.high, info.low, info.write.dwHighDateTime, info.write.dwLowDateTime) != (
                    ident(after), after.high, after.low, after.write.dwHighDateTime, after.write.dwLowDateTime):
                raise OwnedError('payload changed while reading')
        raw = buffer.raw[:count.value]
        return raw, {'id': ident(info), 'size': (info.high << 32) | info.low,
            'mtime': (info.write.dwHighDateTime << 32) | info.write.dwLowDateTime,
            'ctime': (info.creation.dwHighDateTime << 32) | info.creation.dwLowDateTime,
            'sha256': hashlib.sha256(raw).hexdigest()}

    def read(self, name):
        handle = self.store._open(self.target(name), 0x80000000 | win.READ_CONTROL, share=1)
        try:
            return self.read_handle(handle)
        finally:
            win.close(handle)

    def write(self, name, raw):
        handle = self.store._open(self.target(name), 0x40000000 | win.READ_CONTROL, share=0, disposition=1)
        try:
            self.store._check(handle)
            count = w.DWORD()
            win.checked(win.writefile(handle, raw, len(raw), c.byref(count), None))
            if count.value != len(raw):
                raise OwnedError('partial payload write')
            win.checked(win.flush(handle))
        finally:
            win.close(handle)

    def move(self, source, target, expected):
        destination = str(self.target(target))
        handle = self.store._open(self.target(source), DELETE | win.READ_CONTROL | 0x80,
                                  share=3, directory=True)
        try:
            if ident(self.store._check(handle, directory=True)) != expected or self.exists(target):
                raise OwnedError('move identity/collision')
            class Rename(c.Structure):
                _fields_ = [('replace', w.BOOL), ('root', w.HANDLE), ('length', w.DWORD),
                            ('name', w.WCHAR * (len(destination.encode('utf-16-le')) // 2 + 1))]
            value = Rename(False, None, len(destination.encode('utf-16-le')), destination)
            win.checked(set_info(handle, 3, c.byref(value), c.sizeof(value)))
        finally:
            win.close(handle)

    def unlink(self, name, expected):
        handle = self.store._open(self.target(name), DELETE | 0x80000000 | win.READ_CONTROL, share=1)
        try:
            if self.read_handle(handle)[1] != expected:
                raise OwnedError('file changed before deletion')
            flag = w.BOOL(True)
            win.checked(set_info(handle, 4, c.byref(flag), c.sizeof(flag)))
        finally:
            win.close(handle)

    def rmdir(self, name, expected):
        handle = self.store._open(self.target(name), DELETE | win.READ_CONTROL | 0x80, share=3, directory=True)
        try:
            if ident(self.store._check(handle, directory=True)) != expected or os.listdir(self.target(name)):
                raise OwnedError('directory changed before deletion')
            flag = w.BOOL(True)
            win.checked(set_info(handle, 4, c.byref(flag), c.sizeof(flag)))
        finally:
            win.close(handle)


class WindowsLedger:
    NAME = hashlib.sha256(b'growth-loop-owned-ledger').hexdigest() + '.state.json'

    def __init__(self, data):
        self.store = win.WindowsStore(data, error=OwnedError, bounded_json=parse, max_state=MAXIMUM)

    def __enter__(self):
        self.store.__enter__()
        try:
            self.lock = self.store.lock('ownership-ledger')
            self.lock.__enter__()
            return self
        except BaseException:
            self.store.__exit__(); raise

    def __exit__(self, *args):
        self.lock.__exit__(*args)
        self.store.__exit__(*args)

    def read(self):
        return self.store.read(self.NAME) or {'version': 1, 'roots': {}, 'entries': {}}

    def write(self, ledger):
        self.store.write(self.NAME, ledger)

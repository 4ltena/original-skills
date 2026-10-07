"""Windows handle-based private checkpoint storage."""
import contextlib
import ctypes as c
from ctypes import wintypes as w
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

k = c.WinDLL('kernel32', use_last_error=True)
a = c.WinDLL('advapi32', use_last_error=True)
HANDLE = w.HANDLE
INVALID = c.c_void_p(-1).value
READ_CONTROL = 0x20000
class SA(c.Structure):
    _fields_ = [('length', w.DWORD), ('descriptor', c.c_void_p), ('inherit', w.BOOL)]
class INFO(c.Structure):
    _fields_ = [('attributes', w.DWORD), ('creation', w.FILETIME), ('access', w.FILETIME), ('write', w.FILETIME), ('volume', w.DWORD), ('high', w.DWORD), ('low', w.DWORD), ('links', w.DWORD), ('index_high', w.DWORD), ('index_low', w.DWORD)]
class ACL(c.Structure):
    _fields_ = [('revision', c.c_byte), ('reserved', c.c_byte), ('size', w.WORD), ('count', w.WORD), ('reserved2', w.WORD)]

def bind(lib, name, args, result=w.BOOL):
    f = getattr(lib, name)
    f.argtypes, f.restype = args, result
    return f
create = bind(k, 'CreateFileW', [w.LPCWSTR,w.DWORD,w.DWORD,c.POINTER(SA),w.DWORD,w.DWORD,HANDLE], HANDLE)
close = bind(k, 'CloseHandle', [HANDLE])
info = bind(k, 'GetFileInformationByHandle', [HANDLE,c.POINTER(INFO)])
mkdir = bind(k, 'CreateDirectoryW', [w.LPCWSTR,c.POINTER(SA)])
move = bind(k, 'MoveFileExW', [w.LPCWSTR,w.LPCWSTR,w.DWORD])
readfile = bind(k, 'ReadFile', [HANDLE,c.c_void_p,w.DWORD,c.POINTER(w.DWORD),c.c_void_p])
writefile = bind(k, 'WriteFile', [HANDLE,c.c_void_p,w.DWORD,c.POINTER(w.DWORD),c.c_void_p])
flush = bind(k, 'FlushFileBuffers', [HANDLE])
getsecurity = bind(a, 'GetSecurityInfo', [HANDLE,w.DWORD,w.DWORD,c.POINTER(c.c_void_p),c.c_void_p,c.POINTER(c.c_void_p),c.c_void_p,c.POINTER(c.c_void_p)],w.DWORD)
getace = bind(a, 'GetAce', [c.c_void_p,w.DWORD,c.POINTER(c.c_void_p)])
equalsid = bind(a, 'EqualSid', [c.c_void_p,c.c_void_p])
sddl = bind(a, 'ConvertStringSecurityDescriptorToSecurityDescriptorW', [w.LPCWSTR,w.DWORD,c.POINTER(c.c_void_p),c.c_void_p])
free = bind(k, 'LocalFree', [c.c_void_p], c.c_void_p)
getprocess = bind(k, 'GetCurrentProcess', [], HANDLE)
opentoken = bind(a, 'OpenProcessToken', [HANDLE,w.DWORD,c.POINTER(HANDLE)])
gettoken = bind(a, 'GetTokenInformation', [HANDLE,c.c_int,c.c_void_p,w.DWORD,c.POINTER(w.DWORD)])
sidstring = bind(a, 'ConvertSidToStringSidW', [c.c_void_p,c.POINTER(w.LPWSTR)])

def checked(result):
    if not result:
        raise c.WinError(c.get_last_error())
    return result

def identity():
    token = HANDLE()
    checked(opentoken(getprocess(), 8, c.byref(token)))
    try:
        size = w.DWORD()
        gettoken(token, 1, None, 0, c.byref(size))
        buffer = c.create_string_buffer(size.value)
        checked(gettoken(token, 1, buffer, size, c.byref(size)))
        sid = c.cast(buffer, c.POINTER(c.c_void_p))[0]
        value = w.LPWSTR()
        checked(sidstring(sid, c.byref(value)))
        try:
            return buffer, sid, value.value
        finally:
            free(c.cast(value,c.c_void_p))
    finally:
        close(token)

class WindowsStore:
    def __init__(self, data, *, error, bounded_json, max_state=16384):
        if not data:
            raise error('PLUGIN_DATA is required')
        self.base = Path(os.path.abspath(data))
        self.error, self.parse, self.maximum = error, bounded_json, max_state
        self.handles = []
        self.identity_buffer, self.sid, sid = identity()
        self.descriptor = c.c_void_p()
        checked(sddl(f'O:{sid}D:P(A;;FA;;;{sid})',1,c.byref(self.descriptor),None))
        self.sa = SA(c.sizeof(SA),self.descriptor,False)

    def _open(self, path, access=READ_CONTROL | 0x80, share=3, disposition=3, directory=False):
        handle = create(str(path),access | (1 if directory else 0),share,c.byref(self.sa),disposition,0x200000 | (0x2000000 if directory else 0),None)
        if handle == INVALID:
            raise c.WinError(c.get_last_error())
        return handle

    def _check(self, handle, directory=False, security=True):
        details = INFO()
        checked(info(handle,c.byref(details)))
        if details.attributes & 0x400 or bool(details.attributes & 0x10) != directory or (not directory and details.links != 1):
            raise self.error('Unsafe filesystem object')
        if not directory and (details.high or details.low > self.maximum):
            raise self.error('State exceeds size limit')
        if security:
            owner, dacl, descriptor = c.c_void_p(),c.c_void_p(),c.c_void_p()
            status = getsecurity(handle,1,5,c.byref(owner),None,c.byref(dacl),None,c.byref(descriptor))
            if status:
                raise c.WinError(status)
            try:
                if not equalsid(owner,self.sid) or not dacl:
                    raise self.error('State must have a private owner DACL')
                header = c.cast(dacl,c.POINTER(ACL)).contents
                owner_allowed = False
                for index in range(header.count):
                    ace = c.c_void_p()
                    checked(getace(dacl,index,c.byref(ace)))
                    kind = c.cast(ace,c.POINTER(c.c_ubyte))[0]
                    if kind == 0:
                        if not equalsid(c.c_void_p(ace.value+8),self.sid):
                            raise self.error('State grants access to another principal')
                        owner_allowed = True
                    elif kind != 1:
                        raise self.error('Unsupported state ACE')
                if not owner_allowed:
                    raise self.error('Owner access is missing')
            finally:
                free(descriptor)
        return details

    def __enter__(self):
        try:
            # Pin every ancestor without delete sharing; reject junctions and symlinks.
            for path in [*reversed(self.base.parents),self.base]:
                handle = self._open(path,directory=True)
                self.handles.append(handle)
                self._check(handle,directory=True,security=False)
            self.directory = self.base / 'goal-checkpoint'
            if not mkdir(str(self.directory),c.byref(self.sa)) and c.get_last_error() != 183:
                raise c.WinError(c.get_last_error())
            handle = self._open(self.directory,directory=True)
            self.handles.append(handle)
            self._check(handle,directory=True)
            return self
        except BaseException:
            self.__exit__()
            raise

    def __exit__(self,*args):
        for handle in reversed(self.handles):
            close(handle)
        self.handles.clear()
        if self.descriptor:
            free(self.descriptor)
            self.descriptor = None

    def _path(self,name):
        if not re.fullmatch(r'(?:[a-f0-9]{64}\.(?:state\.json|index\.json|lock)|\.[a-f0-9]{32}\.tmp)',name):
            raise self.error('Invalid state filename')
        return self.directory / name

    @contextlib.contextmanager
    def lock(self,session):
        name = hashlib.sha256(session.encode()).hexdigest()+'.lock'
        try:
            handle = self._open(self._path(name),0xC0000000 | READ_CONTROL,0,4)
        except OSError as exc:
            if exc.winerror == 32:
                raise self.error('Another event is updating state') from exc
            raise
        try:
            self._check(handle)
            yield
        finally:
            close(handle)

    def read(self,name):
        try:
            handle = self._open(self._path(name),0x80000000 | READ_CONTROL)
        except OSError as exc:
            if exc.winerror == 2:
                return None
            raise
        try:
            self._check(handle)
            buffer, count = c.create_string_buffer(self.maximum+1), w.DWORD()
            checked(readfile(handle,buffer,self.maximum+1,c.byref(count),None))
            return self.parse(buffer.raw[:count.value])
        finally:
            close(handle)

    def write(self,name,value,recover=False):
        raw = json.dumps(value,ensure_ascii=False,allow_nan=False).encode()
        self.parse(raw)
        try:
            self.read(name)
        except (json.JSONDecodeError,UnicodeDecodeError,self.error):
            if not recover:
                raise
            handle = self._open(self._path(name))
            try:
                self._check(handle)
            finally:
                close(handle)
        temporary = self._path('.'+uuid.uuid4().hex+'.tmp')
        handle = self._open(temporary,0x40000000 | READ_CONTROL,0,1)
        try:
            try:
                self._check(handle)
                count = w.DWORD()
                checked(writefile(handle,raw,len(raw),c.byref(count),None))
                if count.value != len(raw):
                    raise self.error('Incomplete state write')
                checked(flush(handle))
            finally:
                close(handle)
            checked(move(str(temporary),str(self._path(name)),9))
        finally:
            temporary.unlink(missing_ok=True)



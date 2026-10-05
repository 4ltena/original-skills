import ctypes
from ctypes import wintypes as W
import os
import secrets

from .codec import Failure

if os.name == "nt":
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)

    def _bind(dll, name, restype, *args):
        fn = getattr(dll, name)
        fn.restype, fn.argtypes = restype, args
        return fn

    close = _bind(kernel, "CloseHandle", W.BOOL, W.HANDLE)
    free = _bind(kernel, "LocalFree", W.HANDLE, W.HANDLE)
    process = _bind(kernel, "GetCurrentProcess", W.HANDLE)
    thread = _bind(kernel, "GetCurrentThread", W.HANDLE)
    open_process = _bind(kernel, "OpenProcess", W.HANDLE, W.DWORD, W.BOOL, W.DWORD)
    open_token = _bind(advapi, "OpenProcessToken", W.BOOL, W.HANDLE, W.DWORD, ctypes.POINTER(W.HANDLE))
    open_thread_token = _bind(advapi, "OpenThreadToken", W.BOOL, W.HANDLE, W.DWORD, W.BOOL, ctypes.POINTER(W.HANDLE))
    token_info = _bind(advapi, "GetTokenInformation", W.BOOL, W.HANDLE, ctypes.c_int, W.LPVOID, W.DWORD, ctypes.POINTER(W.DWORD))
    sid_string = _bind(advapi, "ConvertSidToStringSidW", W.BOOL, W.LPVOID, ctypes.POINTER(W.LPWSTR))
    revert = _bind(advapi, "RevertToSelf", W.BOOL)
    impersonate = _bind(advapi, "ImpersonateNamedPipeClient", W.BOOL, W.HANDLE)
    server_pid = _bind(kernel, "GetNamedPipeServerProcessId", W.BOOL, W.HANDLE, ctypes.POINTER(W.ULONG))


def _sid(ptr):
    text = W.LPWSTR()
    if not sid_string(ptr, ctypes.byref(text)):
        raise Failure("not_authorized")
    try:
        return text.value
    finally:
        free(text)


def _token_sid(token):
    needed = W.DWORD()
    token_info(token, 1, None, 0, ctypes.byref(needed))
    buf = ctypes.create_string_buffer(needed.value)
    if not token_info(token, 1, buf, len(buf), ctypes.byref(needed)):
        raise Failure("not_authorized")
    return _sid(ctypes.c_void_p.from_buffer(buf).value)


def current_sid():
    token = W.HANDLE()
    if not open_token(process(), 8, ctypes.byref(token)):
        raise Failure("not_authorized")
    try:
        return _token_sid(token)
    finally:
        close(token)


def privileged():
    token = W.HANDLE()
    if not open_token(process(), 8, ctypes.byref(token)):
        raise Failure("not_authorized")
    try:
        needed = W.DWORD()
        token_info(token, 2, None, 0, ctypes.byref(needed))
        buf = ctypes.create_string_buffer(needed.value)
        if not token_info(token, 2, buf, len(buf), ctypes.byref(needed)):
            raise Failure("not_authorized")
        class GROUP(ctypes.Structure):
            _fields_ = [("sid", W.LPVOID), ("attributes", W.DWORD)]
        class GROUPS(ctypes.Structure):
            _fields_ = [("count", W.DWORD), ("groups", GROUP * W.DWORD.from_buffer(buf).value)]
        return any(_sid(item.sid) in {"S-1-5-32-544", "S-1-5-18"} for item in GROUPS.from_buffer(buf).groups)
    finally:
        close(token)


def peer_sid(pipe):
    token = W.HANDLE()
    if not impersonate(pipe):
        raise Failure("not_authorized")
    try:
        if not open_thread_token(thread(), 8, True, ctypes.byref(token)):
            raise Failure("not_authorized")
        return _token_sid(token)
    finally:
        if token:
            close(token)
        if not revert():
            os._exit(1)


def verify_server(pipe, expected):
    pid = W.ULONG()
    if not server_pid(pipe, ctypes.byref(pid)):
        raise Failure("not_authorized")
    handle = open_process(0x1000, False, pid.value)
    token = W.HANDLE()
    if not handle:
        raise Failure("not_authorized")
    try:
        if not open_token(handle, 8, ctypes.byref(token)) or _token_sid(token) != expected:
            raise Failure("not_authorized")
    finally:
        if token:
            close(token)
        close(handle)


class BLOB(ctypes.Structure):
    _fields_ = [("size", W.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def dpapi(data, decrypt=False):
    if os.name != "nt":
        raise Failure("unavailable")
    raw = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source, out = BLOB(len(data), raw), BLOB()
    fn = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes = [ctypes.POINTER(BLOB), W.LPVOID, W.LPVOID, W.LPVOID, W.LPVOID, W.DWORD, ctypes.POINTER(BLOB)]
    fn.restype = W.BOOL
    if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(out)):
        raise Failure("unlock_required" if decrypt else "unavailable")
    try:
        return ctypes.string_at(out.data, out.size)
    finally:
        ctypes.memset(out.data, 0, out.size)
        free(out.data)


def private_acl(path, broker, secret=True):
    get_security = _bind(advapi, "GetNamedSecurityInfoW", W.DWORD, W.LPWSTR, W.DWORD, W.DWORD,
                         ctypes.POINTER(W.LPVOID), W.LPVOID, ctypes.POINTER(W.LPVOID), W.LPVOID,
                         ctypes.POINTER(W.LPVOID))
    get_ace = _bind(advapi, "GetAce", W.BOOL, W.LPVOID, W.DWORD, ctypes.POINTER(W.LPVOID))
    owner, dacl, descriptor = W.LPVOID(), W.LPVOID(), W.LPVOID()
    if get_security(str(path), 1, 5, ctypes.byref(owner), None, ctypes.byref(dacl), None, ctypes.byref(descriptor)):
        raise Failure("not_authorized")
    try:
        trusted = {broker, "S-1-5-18", "S-1-5-32-544",
                   "S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464"}
        if not owner or _sid(owner) not in trusted or not dacl:
            raise Failure("not_authorized")
        count = ctypes.c_ushort.from_address(dacl.value + 4).value
        for i in range(count):
            ace = W.LPVOID()
            if not get_ace(dacl, i, ctypes.byref(ace)):
                raise Failure("not_authorized")
            typ = ctypes.c_ubyte.from_address(ace.value).value
            flags = ctypes.c_ubyte.from_address(ace.value + 1).value
            if flags & 8:
                continue
            if typ not in (0, 1):
                raise Failure("not_authorized")
            if typ == 0:
                mask = W.DWORD.from_address(ace.value + 4).value
                prohibited = 0xFFFFFFFF if secret else 0x500D0156
                if _sid(ace.value + 8) not in trusted and mask & prohibited:
                    raise Failure("not_authorized")
    finally:
        free(descriptor)


def deployment_acl(path, broker):
    private_acl(path, broker)
    get_security = _bind(advapi, "GetNamedSecurityInfoW", W.DWORD, W.LPWSTR, W.DWORD, W.DWORD,
                         ctypes.POINTER(W.LPVOID), W.LPVOID, ctypes.POINTER(W.LPVOID), W.LPVOID,
                         ctypes.POINTER(W.LPVOID))
    owner, dacl, descriptor = W.LPVOID(), W.LPVOID(), W.LPVOID()
    if get_security(str(path), 1, 5, ctypes.byref(owner), None, ctypes.byref(dacl), None, ctypes.byref(descriptor)):
        raise Failure("not_authorized")
    try:
        admins = {"S-1-5-18", "S-1-5-32-544"}
        if _sid(owner) not in admins:
            raise Failure("not_authorized")
        get_ace = _bind(advapi, "GetAce", W.BOOL, W.LPVOID, W.DWORD, ctypes.POINTER(W.LPVOID))
        for i in range(ctypes.c_ushort.from_address(dacl.value + 4).value):
            ace = W.LPVOID()
            if not get_ace(dacl, i, ctypes.byref(ace)):
                raise Failure("not_authorized")
            if ctypes.c_ubyte.from_address(ace.value).value == 0:
                mask = W.DWORD.from_address(ace.value + 4).value
                if _sid(ace.value + 8) not in admins and mask & 0x500D0156:
                    raise Failure("not_authorized")
    finally:
        free(descriptor)


def private_temp(directory):
    import msvcrt
    class SECURITY(ctypes.Structure):
        _fields_ = [("length", W.DWORD), ("descriptor", W.LPVOID), ("inherit", W.BOOL)]
    convert = _bind(advapi, "ConvertStringSecurityDescriptorToSecurityDescriptorW", W.BOOL,
                    W.LPWSTR, W.DWORD, ctypes.POINTER(W.LPVOID), W.LPVOID)
    create = _bind(kernel, "CreateFileW", W.HANDLE, W.LPWSTR, W.DWORD, W.DWORD, W.LPVOID,
                   W.DWORD, W.DWORD, W.HANDLE)
    descriptor = W.LPVOID()
    sddl = f"D:P(A;;GA;;;SY)(A;;GA;;;BA)(A;;GA;;;{current_sid()})"
    if not convert(sddl, 1, ctypes.byref(descriptor), None):
        raise Failure("not_authorized")
    from pathlib import Path
    path = Path(directory) / (".pending-" + secrets.token_hex(16))
    handle = None
    try:
        security = SECURITY(ctypes.sizeof(SECURITY), descriptor, False)
        handle = create(str(path), 0x40000000, 0, ctypes.byref(security), 1, 0x80, None)
        if handle == ctypes.c_void_p(-1).value:
            raise Failure("not_authorized")
        fd = msvcrt.open_osfhandle(handle, os.O_WRONLY | os.O_BINARY)
        handle = None
        return fd, str(path)
    finally:
        if handle and handle != ctypes.c_void_p(-1).value:
            close(handle)
        free(descriptor)

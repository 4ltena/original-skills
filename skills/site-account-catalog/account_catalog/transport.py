import ctypes
from ctypes import wintypes as W
import os
from pathlib import Path
import socket
import stat
import struct
import sys

from .codec import Failure, canonical, fields, identifier, loads, version
from .storage import check_path, principal

MAX_REQUEST = 16384


def peer_uid(connection):
    if sys.platform == "linux":
        return str(struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))[1])
    if sys.platform == "darwin":
        uid, gid = ctypes.c_uint(), ctypes.c_uint()
        libc = ctypes.CDLL(None, use_errno=True)
        fn = libc.getpeereid
        fn.argtypes, fn.restype = [ctypes.c_int, ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint)], ctypes.c_int
        if fn(connection.fileno(), ctypes.byref(uid), ctypes.byref(gid)) != 0:
            raise Failure("not_authorized")
        return str(uid.value)
    raise Failure("unavailable")


def _receive(connection, maximum):
    chunks, count = [], 0
    while True:
        chunk = connection.recv(min(4096, maximum + 1 - count))
        if not chunk:
            break
        count += len(chunk)
        if count > maximum:
            raise Failure()
        chunks.append(chunk)
        if b"\n" in chunk:
            break
    payload = b"".join(chunks)
    if not payload.endswith(b"\n") or payload.count(b"\n") != 1:
        raise Failure()
    return loads(payload[:-1], maximum)


def validate_response(response, target):
    fields(response, ("schema_version", "target_id", "status"), ("error_code", "healthy"))
    version(response)
    from .codec import ERRORS
    if (response["target_id"] != target or response["status"] not in {"authenticated", "needs_user", "failed"}
            or ("error_code" in response and response["error_code"] not in ERRORS)
            or ("healthy" in response and type(response["healthy"]) is not bool)):
        raise Failure()
    return response


def _pipe_name(name):
    return "\\\\.\\pipe\\account-catalog-" + identifier(name)


def send(endpoint, broker_id, request):
    if principal() == broker_id or broker_id in {"0", "S-1-5-18", "S-1-5-32-544"}:
        raise Failure("not_authorized")
    if os.name == "nt":
        response = _windows_client(_pipe_name(endpoint), broker_id, request)
    else:
        if not broker_id.isdecimal() or not Path(endpoint).is_absolute():
            raise Failure()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(15)
            try:
                connection.connect(endpoint)
                if peer_uid(connection) != broker_id:
                    raise Failure("not_authorized")
                connection.sendall(canonical(request) + b"\n")
                response = _receive(connection, 4096)
            except (TimeoutError, socket.timeout):
                raise Failure("timeout") from None
            except OSError:
                raise Failure("unavailable") from None
    return validate_response(response, request["target_id"])


def serve(endpoint, broker, stop, management=False):
    if os.name == "nt":
        return _windows_server(_pipe_name(endpoint), broker, stop, management)
    path = Path(endpoint).absolute()
    check_path(path.parent, broker.vault.store.broker, secret=False)
    if path.exists():
        raise Failure("unavailable")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        server.bind(str(path))
        os.chmod(path, 0o600 if management else 0o660)
        server.listen(8)
        server.settimeout(1)
        while not stop.is_set():
            try:
                connection, _ = server.accept()
            except socket.timeout:
                continue
            with connection:
                connection.settimeout(5)
                try:
                    caller = peer_uid(connection)
                    request = _receive(connection, MAX_REQUEST)
                    response = broker.manage(request, caller) if management else broker.execute(request, caller)
                    connection.sendall(canonical(response) + b"\n")
                except (Failure, OSError, ValueError):
                    continue
    finally:
        server.close()
        if path.exists() and path.lstat().st_uid == os.getuid() and stat.S_ISSOCK(path.lstat().st_mode):
            path.unlink()


if os.name == "nt":
    from .windows import kernel, advapi, _bind, close, free, peer_sid, verify_server

    class SECURITY(ctypes.Structure):
        _fields_ = [("length", W.DWORD), ("descriptor", W.LPVOID), ("inherit", W.BOOL)]

    class OVERLAPPED(ctypes.Structure):
        _fields_ = [("internal", ctypes.c_size_t), ("internal_high", ctypes.c_size_t),
                    ("offset", W.DWORD), ("offset_high", W.DWORD), ("event", W.HANDLE)]

    create_pipe = _bind(kernel, "CreateNamedPipeW", W.HANDLE, W.LPWSTR, W.DWORD, W.DWORD, W.DWORD,
                        W.DWORD, W.DWORD, W.DWORD, ctypes.POINTER(SECURITY))
    create_file = _bind(kernel, "CreateFileW", W.HANDLE, W.LPWSTR, W.DWORD, W.DWORD, W.LPVOID,
                        W.DWORD, W.DWORD, W.HANDLE)
    connect_pipe = _bind(kernel, "ConnectNamedPipe", W.BOOL, W.HANDLE, ctypes.POINTER(OVERLAPPED))
    disconnect_pipe = _bind(kernel, "DisconnectNamedPipe", W.BOOL, W.HANDLE)
    read_file = _bind(kernel, "ReadFile", W.BOOL, W.HANDLE, W.LPVOID, W.DWORD, ctypes.POINTER(W.DWORD), ctypes.POINTER(OVERLAPPED))
    write_file = _bind(kernel, "WriteFile", W.BOOL, W.HANDLE, W.LPVOID, W.DWORD, ctypes.POINTER(W.DWORD), ctypes.POINTER(OVERLAPPED))
    create_event = _bind(kernel, "CreateEventW", W.HANDLE, W.LPVOID, W.BOOL, W.BOOL, W.LPWSTR)
    wait_event = _bind(kernel, "WaitForSingleObject", W.DWORD, W.HANDLE, W.DWORD)
    overlapped_result = _bind(kernel, "GetOverlappedResult", W.BOOL, W.HANDLE, ctypes.POINTER(OVERLAPPED), ctypes.POINTER(W.DWORD), W.BOOL)
    cancel = _bind(kernel, "CancelIoEx", W.BOOL, W.HANDLE, ctypes.POINTER(OVERLAPPED))
    convert_sd = _bind(advapi, "ConvertStringSecurityDescriptorToSecurityDescriptorW", W.BOOL,
                       W.LPWSTR, W.DWORD, ctypes.POINTER(W.LPVOID), W.LPVOID)


def _operation(handle, mode, data=None, timeout=5000):
    op = OVERLAPPED()
    op.event = create_event(None, True, False, None)
    if not op.event:
        raise Failure("unavailable")
    transferred = W.DWORD()
    buffer = ctypes.create_string_buffer(data) if mode == "write" else ctypes.create_string_buffer(MAX_REQUEST + 1)
    pending = False
    try:
        if mode == "connect":
            ok = connect_pipe(handle, ctypes.byref(op))
        else:
            fn = write_file if mode == "write" else read_file
            ok = fn(handle, buffer, len(data) if mode == "write" else MAX_REQUEST + 1,
                    ctypes.byref(transferred), ctypes.byref(op))
        error = ctypes.get_last_error()
        if mode == "connect" and not ok and error == 535:
            return b""
        if not ok:
            if error != 997:
                raise Failure("unavailable")
            pending = True
            if wait_event(op.event, timeout) != 0:
                cancel(handle, ctypes.byref(op))
                overlapped_result(handle, ctypes.byref(op), ctypes.byref(transferred), True)
                pending = False
                raise Failure("timeout")
            if not overlapped_result(handle, ctypes.byref(op), ctypes.byref(transferred), False):
                pending = False
                raise Failure("unavailable")
            pending = False
        if mode == "write" and transferred.value != len(data):
            raise Failure("unavailable")
        return buffer.raw[:transferred.value] if mode == "read" else b""
    finally:
        if pending:
            cancel(handle, ctypes.byref(op))
            overlapped_result(handle, ctypes.byref(op), ctypes.byref(transferred), True)
        close(op.event)


def _windows_client(name, broker_id, request, management=False):
    handle = create_file(name, 3, 0, None, 3, 0x40000000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise Failure("unavailable")
    try:
        verify_server(handle, broker_id)
        _operation(handle, "write", canonical(request))
        response = loads(_operation(handle, "read"), 4096)
        if not management:
            validate_response(response, request["target_id"])
        _operation(handle, "write", b"ack")
        return response
    finally:
        close(handle)


def _windows_server(name, broker, stop, management=False):
    import re
    while not stop.is_set():
        callers = [] if management else sorted({caller for row in broker.vault.metadata()["bindings"] for caller in row["callers"]})
        owner = broker.vault.store.broker
        if (len(callers) > 32 or any(not re.fullmatch(r"S-1-5-(?:\d+-)*\d+", c) or c == owner
                                   or c in {"S-1-5-18", "S-1-5-32-544"} for c in callers)):
            raise Failure("not_authorized")
        descriptor = W.LPVOID()
        sddl = f"D:P(A;;GA;;;SY)(A;;GA;;;{owner})" + "".join(f"(A;;0x3;;;{c})" for c in callers)
        if not convert_sd(sddl, 1, ctypes.byref(descriptor), None):
            raise Failure("not_authorized")
        attributes = SECURITY(ctypes.sizeof(SECURITY), descriptor, False)
        handle = create_pipe(name, 3 | 0x40000000 | 0x80000, 4 | 2 | 8, 1, 4096, MAX_REQUEST, 0, ctypes.byref(attributes))
        free(descriptor)
        if handle == ctypes.c_void_p(-1).value:
            raise Failure("unavailable")
        try:
            _operation(handle, "connect", timeout=1000)
            request = loads(_operation(handle, "read"), MAX_REQUEST)
            caller = peer_sid(handle)
            response = broker.manage(request, caller) if management else broker.execute(request, caller)
            _operation(handle, "write", canonical(response))
            if _operation(handle, "read") != b"ack":
                raise Failure()
        except Failure:
            pass
        finally:
            disconnect_pipe(handle)
            close(handle)


def send_management(endpoint, request):
    owner = principal()
    if os.name == "nt":
        response = _windows_client(_pipe_name(endpoint), owner, request, management=True)
    else:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(30)
            connection.connect(endpoint)
            if peer_uid(connection) != owner:
                raise Failure("not_authorized")
            connection.sendall(canonical(request) + b"\n")
            response = _receive(connection, 4096)
    fields(response, ("schema_version", "status"), ("error_code",))
    version(response)
    from .codec import ERRORS
    if response["status"] not in {"completed", "failed"} or response.get("error_code", "unavailable") not in ERRORS:
        raise Failure()
    if response["status"] != "completed":
        raise Failure(response.get("error_code", "unavailable"))
    return response

"""Identify the process listening on a configured Windows loopback endpoint."""

import ctypes
from ctypes import wintypes
from ipaddress import ip_address
import socket
from urllib.parse import urlsplit


class _TcpRow(ctypes.Structure):
    _fields_ = [(name, wintypes.DWORD) for name in (
        "state", "local_addr", "local_port", "remote_addr", "remote_port", "pid",
    )]


class _Tcp6Row(ctypes.Structure):
    _fields_ = [
        ("local_addr", ctypes.c_ubyte * 16), ("local_scope", wintypes.DWORD),
        ("local_port", wintypes.DWORD), ("remote_addr", ctypes.c_ubyte * 16),
        ("remote_scope", wintypes.DWORD), ("remote_port", wintypes.DWORD),
        ("state", wintypes.DWORD), ("pid", wintypes.DWORD),
    ]


def owns_listener(endpoint: str, pid: int) -> bool:
    """Return whether *pid* owns the exact IP address and port in *endpoint*."""
    parsed = urlsplit(endpoint)
    port = parsed.port
    if not port:
        raise ValueError("Expected a loopback endpoint with an explicit port")
    return port in listener_ports(parsed.hostname or "", pid)


def listener_ports(hostname: str, pid: int) -> tuple[int, ...]:
    """Return the listening ports owned by *pid* on this numeric loopback address."""
    address = ip_address(hostname)
    if not address.is_loopback:
        raise ValueError("Expected a numeric loopback address")
    family = socket.AF_INET if address.version == 4 else socket.AF_INET6
    row_type = _TcpRow if address.version == 4 else _Tcp6Row
    get_table = ctypes.WinDLL("iphlpapi").GetExtendedTcpTable
    get_table.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), wintypes.BOOL,
                          wintypes.ULONG, ctypes.c_int, wintypes.ULONG]
    get_table.restype = wintypes.DWORD
    size = wintypes.DWORD()
    result = get_table(None, ctypes.byref(size), False, family, 3, 0)
    if result != 122:  # ERROR_INSUFFICIENT_BUFFER
        raise ctypes.WinError(result)
    while True:
        capacity = size.value
        buffer = ctypes.create_string_buffer(capacity)
        result = get_table(buffer, ctypes.byref(size), False, family, 3, 0)
        if not result:
            break
        if result != 122 or size.value <= capacity:
            raise ctypes.WinError(result)

    count = wintypes.DWORD.from_buffer(buffer).value
    rows = (row_type * count).from_buffer(buffer, ctypes.sizeof(wintypes.DWORD))
    ports = set()
    for row in rows:
        local_addr = (ctypes.string_at(ctypes.byref(row, row_type.local_addr.offset), 4)
                      if address.version == 4 else bytes(row.local_addr))
        if row.pid == pid and row.state == 2 and local_addr == address.packed:
            ports.add(socket.ntohs(row.local_port))
    return tuple(sorted(ports))


def process_creation_filetime(handle: int) -> int:
    """Read the creation FILETIME from a borrowed Windows process handle."""
    get_times = ctypes.WinDLL("kernel32", use_last_error=True).GetProcessTimes
    get_times.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    get_times.restype = wintypes.BOOL
    created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
    if not get_times(handle, ctypes.byref(created), ctypes.byref(exited),
                     ctypes.byref(kernel), ctypes.byref(user)):
        raise ctypes.WinError(ctypes.get_last_error())
    return (created.dwHighDateTime << 32) | created.dwLowDateTime

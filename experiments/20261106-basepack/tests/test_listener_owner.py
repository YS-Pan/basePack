import ctypes
import os
import socket
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from basepack.runtime import listener_owner
from basepack.runtime.listener_owner import listener_ports, owns_listener, process_creation_filetime


pytestmark = pytest.mark.skipif(os.name != "nt", reason="uses Windows TCP tables")


@pytest.mark.parametrize("family,host,url_host", [
    (socket.AF_INET, "127.0.0.1", "127.0.0.1"),
    (socket.AF_INET6, "::1", "[::1]"),
])
def test_listener_must_match_process_address_and_port(family, host, url_host):
    with socket.socket(family, socket.SOCK_STREAM) as listener:
        listener.bind((host, 0))
        listener.listen()
        port = listener.getsockname()[1]
        endpoint = f"http://{url_host}:{port}"
        assert owns_listener(endpoint, os.getpid())
        assert port in listener_ports(host, os.getpid())
        assert listener_ports(host, 0) == ()
        assert not owns_listener(endpoint, 0)
        assert not owns_listener(f"http://{url_host}:{port % 65535 + 1}", os.getpid())
        if family == socket.AF_INET:
            assert not owns_listener(f"http://127.0.0.2:{port}", os.getpid())
    assert not owns_listener(endpoint, os.getpid())
    assert port not in listener_ports(host, os.getpid())


def test_wildcard_listener_is_not_an_exact_address_match():
    with socket.socket() as listener:
        listener.bind(("0.0.0.0", 0))
        listener.listen()
        assert not owns_listener(f"http://127.0.0.1:{listener.getsockname()[1]}", os.getpid())
        assert listener.getsockname()[1] not in listener_ports("127.0.0.1", os.getpid())


def test_dynamic_listeners_return_all_matching_ports_in_order():
    with socket.socket() as first, socket.socket() as second:
        first.bind(("127.0.0.1", 0))
        second.bind(("127.0.0.1", 0))
        first.listen()
        second.listen()
        expected = {first.getsockname()[1], second.getsockname()[1]}
        actual = listener_ports("127.0.0.1", os.getpid())
        assert expected.issubset(actual)
        assert actual == tuple(sorted(set(actual)))


def test_creation_time_uses_borrowed_child_handle():
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        creation = process_creation_filetime(child._handle)
        unix_seconds = (creation - 116444736000000000) / 10_000_000
        assert abs(time.time() - unix_seconds) < 60
        assert process_creation_filetime(child._handle) == creation
        assert child.poll() is None
    finally:
        child.terminate()
        child.wait()


def test_creation_time_preserves_windows_error():
    with pytest.raises(OSError) as error:
        process_creation_filetime(0)
    assert error.value.winerror == 6  # ERROR_INVALID_HANDLE


@pytest.mark.parametrize("grows", [True, False])
def test_table_growth_retries_only_when_the_required_size_increases(monkeypatch, grows):
    calls = []

    def get_table(buffer, size, _ordered, _family, _table_class, _reserved):
        size = ctypes.cast(size, ctypes.POINTER(ctypes.wintypes.DWORD))
        calls.append(size.contents.value)
        if len(calls) == 1:
            size.contents.value = 4
            return 122
        if len(calls) == 2:
            if grows:
                size.contents.value = 4 + ctypes.sizeof(listener_owner._TcpRow)
            return 122
        ctypes.wintypes.DWORD.from_buffer(buffer).value = 1
        row = listener_owner._TcpRow.from_buffer(buffer, 4)
        row.state = 2
        row.local_addr = int.from_bytes(socket.inet_aton("127.0.0.1"), "little")
        row.local_port = socket.htons(12345)
        row.pid = os.getpid()
        return 0

    class Function:
        def __call__(self, *args):
            return get_table(*args)

    monkeypatch.setattr(ctypes, "WinDLL", lambda _: SimpleNamespace(GetExtendedTcpTable=Function()))
    if grows:
        assert owns_listener("http://127.0.0.1:12345", os.getpid())
        assert len(calls) == 3
    else:
        with pytest.raises(OSError) as error:
            owns_listener("http://127.0.0.1:12345", os.getpid())
        assert error.value.winerror == 122
        assert len(calls) == 2

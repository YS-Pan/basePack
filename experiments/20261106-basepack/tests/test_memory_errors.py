from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from basepack.memory.store import Memory


def test_prepare_rejects_directory_before_database_access(tmp_path):
    (tmp_path / "资料.png").mkdir()
    memory = Memory(SimpleNamespace(root=tmp_path, raw={"memory": {}}))
    with pytest.raises(ValueError, match=r"files, not directories.*Get-ChildItem -File"):
        memory.prepare(["资料.png"])


def test_sql_413_reports_actual_request_size_and_keeps_original_error(monkeypatch):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(413)
            self.end_headers()
            self.wfile.write(b"request too large")

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setenv("TEST_MEMORY_PASSWORD", "test")
        connection = {"endpoint": f"http://127.0.0.1:{server.server_port}", "username": "root",
                      "password_env": "TEST_MEMORY_PASSWORD", "namespace": "ns", "database": "db",
                      "project_id": "project"}
        memory = Memory(SimpleNamespace(raw={"memory": connection}))
        with pytest.raises(HTTPError) as failure:
            memory._execute("RETURN '中文';")
        assert failure.value.code == 413
        assert len(received) == 1
        notes = " ".join(failure.value.__notes__)
        assert "request too large" in notes
        assert f"{len(received[0])} bytes" in notes
        assert "server capacity is unknown" in notes
        assert "expected versions" in notes and "atomicity" in notes and "relation endpoints" in notes
    finally:
        server.shutdown()
        thread.join()
        server.server_close()

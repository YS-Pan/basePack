from base64 import b64encode
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest

from basepack.memory.store import Memory
from basepack.project.config import load_project_config
from basepack.project.init import init_project


@pytest.fixture
def config(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    return load_project_config(init_project(tmp_path / "project", machine, max_concurrent_subagents=12, concurrency_source="test fixture"))


def _write_password(config, text, encoding="utf-8"):
    config.memory_password_file.parent.mkdir(parents=True, exist_ok=True)
    config.memory_password_file.write_bytes(text.encode(encoding))


def test_missing_credential_file_keeps_file_error_and_does_not_use_environment(config, monkeypatch):
    monkeypatch.setenv("BASEPACK_MEMORY_PASSWORD", "unused-legacy-environment")
    with pytest.raises(FileNotFoundError) as error:
        Memory(config)
    assert Path(error.value.filename) == config.memory_password_file
    assert not config.memory_dir.exists()


def test_unreadable_credential_file_keeps_permission_error(config, monkeypatch):
    _write_password(config, "private-read-test")
    original_read = Path.read_bytes
    error = PermissionError(13, "credential read denied", str(config.memory_password_file))
    reads = []
    def read_bytes(path):
        if path == config.memory_password_file:
            reads.append(path)
            raise error
        return original_read(path)
    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    with pytest.raises(PermissionError) as failure:
        Memory(config)
    assert failure.value is error
    assert reads == [config.memory_password_file]
    assert original_read(config.memory_password_file) == b"private-read-test"


@pytest.mark.parametrize("password, encoding", [
    ("private-401-test", "utf-8"), ("", "utf-8"), (" keep-whitespace\n", "utf-8"),
    (" keep-crlf\r\n", "utf-8"), ("bom-secret", "utf-8-sig"), (" bom-crlf\r\n", "utf-8-sig")])
def test_client_uses_file_exactly_and_preserves_401_without_retry(config, monkeypatch, password, encoding):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(self.headers.get("Authorization"))
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"authentication rejected")

        def log_message(self, *_):
            pass

    _write_password(config, password, encoding)
    monkeypatch.setenv("BASEPACK_MEMORY_PASSWORD", "unused-legacy-environment")
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config.raw["memory"]["endpoint"] = f"http://127.0.0.1:{server.server_port}"
    try:
        with pytest.raises(HTTPError) as error:
            Memory(config)._execute("RETURN true;")
        assert error.value.code == 401
        assert "authentication rejected" in " ".join(error.value.__notes__)
        assert received == ["Basic " + b64encode(("root:" + password).encode("utf-8")).decode("ascii")]
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_real_authentication_rejects_missing_and_wrong_credentials_before_write(config, monkeypatch):
    required = {"BASEPACK_MEMORY_TEST_ENDPOINT", "BASEPACK_MEMORY_TEST_PASSWORD_FILE"}
    if not required <= os.environ.keys():
        pytest.skip("requires an actual disposable authenticated SurrealDB server")
    _write_password(config, Path(os.environ["BASEPACK_MEMORY_TEST_PASSWORD_FILE"]).read_bytes().decode("utf-8-sig"))
    config.raw["memory"].update(endpoint=os.environ["BASEPACK_MEMORY_TEST_ENDPOINT"],
                                 namespace="credential_test_" + uuid4().hex, database="memory")
    monkeypatch.setenv("BASEPACK_MEMORY_PASSWORD", "unused-legacy-environment")
    memory = Memory(config)
    memory.install_schema()
    memory._execute("DEFINE TABLE auth_probe SCHEMALESS;")
    connection = config.raw["memory"]
    sql = (f"USE NS {connection['namespace']} DB {connection['database']}; "
           "CREATE auth_probe:missing CONTENT { attempted: true };")
    request = Request(connection["endpoint"] + "/sql", sql.encode("utf-8"),
                      {"Content-Type": "text/plain", "Accept": "application/json",
                       "Origin": "http://127.0.0.1:18762"})
    try:
        with urlopen(request, timeout=10) as response:
            statements = json.load(response)
            unauthenticated = {"http_status": response.status, "statements": statements}
        assert any(statement["status"] == "ERR" for statement in statements)
    except HTTPError as error:
        assert error.code in (401, 403)
        unauthenticated = {"http_status": error.code, "body": error.read().decode("utf-8")}
    assert memory._execute("SELECT * FROM auth_probe;")[0] == []
    _write_password(config, "wrong-" + uuid4().hex)
    with pytest.raises(HTTPError) as wrong:
        Memory(config)._execute("CREATE auth_probe:wrong;")
    assert wrong.value.code == 401
    assert memory._execute("SELECT * FROM auth_probe;")[0] == []
    (config.root.parent / "authentication-result.json").write_text(json.dumps({
        "unauthenticated_simple_post": unauthenticated, "wrong_credential_http_status": wrong.value.code,
        "rows_after_both_attempts": [], "authorization_from_file_succeeded": True,
        "legacy_password_environment_ignored": True}, ensure_ascii=False, indent=2), encoding="utf-8")

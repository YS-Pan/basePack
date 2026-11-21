from contextlib import contextmanager
from io import BytesIO
import json
from pathlib import Path
from subprocess import CalledProcessError
import sys
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from basepack.runtime import backup


@pytest.fixture
def target(tmp_path, monkeypatch):
    credential = tmp_path / "credential.txt"
    credential.write_bytes("backup fixture\r\npassword".encode("utf-8-sig"))
    connection = {"namespace": "team", "database": "memory", "username": "test-user",
                  "endpoint": "http://127.0.0.1:18102"}
    config = SimpleNamespace(memory_password_file=credential, raw={"memory": connection})
    state = SimpleNamespace(config=config, events=[], namespaces={}, admitted=False, identity_error=None,
                            lease=SimpleNamespace(endpoint="http://127.0.0.1:39155"))

    @contextmanager
    def operation(project):
        assert project is config
        state.admitted = True
        try:
            yield state.lease
        finally:
            state.admitted = False

    class FixtureMemory:
        def __init__(self, project):
            assert project is config
            self.config = config
            self.connection = connection
            self._authorization = "Basic fixture"

        def verify_project(self):
            assert state.admitted
            state.events.append("verify")
            if state.identity_error is not None:
                raise state.identity_error

        def _execute(self, sql, *, check_project):
            assert state.admitted and not check_project
            if sql == "INFO FOR ROOT;":
                state.events.append("inspect")
                return [{"namespaces": state.namespaces}]
            assert sql == "BEGIN; DEFINE NAMESPACE `team`; USE NS `team`; DEFINE DATABASE `memory`; COMMIT;"
            state.events.append("claim")

    monkeypatch.setattr(backup, "memory_operation", operation)
    monkeypatch.setattr(backup, "Memory", FixtureMemory)
    monkeypatch.setattr(backup, "_target", lambda *_: "registered")
    monkeypatch.setattr(backup, "_load", lambda _: (None, {"surreal_exe": "registered-surreal.exe"}))
    monkeypatch.setenv("SURREAL_TOKEN", "unrelated token")
    return state


@pytest.mark.parametrize("dynamic", [True, False])
def test_export_uses_admitted_or_fixed_endpoint(target, tmp_path, monkeypatch, dynamic):
    file = tmp_path / "备份.surql"
    if not dynamic:
        target.lease = None
    endpoint = "http://127.0.0.1:39155" if dynamic else "http://127.0.0.1:18102"

    def run(argv, *, check, env, **options):
        assert target.admitted
        assert check and env["SURREAL_PASS"] == "backup fixture\r\npassword"
        assert env["SURREAL_USER"] == "test-user" and env["NO_PROXY"] == "*"
        assert "SURREAL_TOKEN" not in env
        assert argv[:-1] == ["registered-surreal.exe", "export", "--endpoint", endpoint,
                            "--auth-level", "root", "--namespace", "team", "--database", "memory", "--"]
        assert Path(argv[-1]) != file
        target.events.append("export")
        Path(argv[-1]).write_text("exported", encoding="utf-8")

    monkeypatch.setattr(backup.subprocess, "run", run)
    assert backup.transfer(target.config, "export", str(file)) == {
        "status": "exported", "endpoint": endpoint, "file": str(file),
    }
    assert target.events == ["verify", "export"]
    assert file.read_text(encoding="utf-8") == "exported"
    assert not target.admitted


def test_failed_export_preserves_previous_backup(target, tmp_path, monkeypatch):
    file = tmp_path / "backup.surql"
    file.write_text("previous", encoding="utf-8")

    def run(argv, **options):
        assert target.admitted
        Path(argv[-1]).write_text("incomplete", encoding="utf-8")
        raise CalledProcessError(1, argv)

    monkeypatch.setattr(backup.subprocess, "run", run)
    with pytest.raises(CalledProcessError):
        backup.transfer(target.config, "export", str(file))
    assert file.read_text(encoding="utf-8") == "previous"
    assert list(tmp_path.glob("*.surql")) == [file]
    assert not target.admitted


def test_import_claims_fresh_target_and_verifies_inside_same_admission(target, tmp_path, monkeypatch):
    file = tmp_path / "restore.surql"
    payload = b"OPTION IMPORT;\n" + b" " * 103981
    file.write_bytes(payload)

    def open_import(request):
        assert target.admitted
        assert request.full_url == target.lease.endpoint + "/import"
        assert request.get_method() == "POST"
        assert request.get_header("Content-length") == str(len(payload))
        assert request.get_header("Content-type") == "application/octet-stream"
        assert request.get_header("Authorization") == "Basic fixture"
        assert request.get_header("Surreal-ns") == "team" and request.get_header("Surreal-db") == "memory"
        assert Path(request.data.name) == file and request.data.read() == payload
        target.events.append("import")
        return BytesIO(b"[]")

    monkeypatch.setattr(backup, "managed_opener", lambda: SimpleNamespace(open=open_import))
    assert backup.transfer(target.config, "import", str(file))["status"] == "imported"
    assert target.events == ["inspect", "claim", "import", "verify"]
    assert not target.admitted


def test_import_preserves_http_status_and_server_details(target, tmp_path, monkeypatch):
    file = tmp_path / "restore.surql"
    file.touch()
    failure = HTTPError(target.lease.endpoint + "/import", 422, "Unprocessable Entity", None,
                        BytesIO(b'[{"result":"record constraint failed"}]'))

    def fail_import(request):
        raise failure

    monkeypatch.setattr(backup, "managed_opener", lambda: SimpleNamespace(open=fail_import))
    with pytest.raises(HTTPError) as error:
        backup.transfer(target.config, "import", str(file))
    assert error.value is failure
    assert error.value.__notes__ == ['[{"result":"record constraint failed"}]']
    assert target.events == ["inspect", "claim"]
    assert not target.admitted


def test_import_requires_matching_project_after_successful_upload(target, tmp_path, monkeypatch):
    file = tmp_path / "restore.surql"
    file.touch()
    target.identity_error = ValueError("Memory database belongs to another project")
    monkeypatch.setattr(backup, "managed_opener", lambda: SimpleNamespace(open=lambda _: BytesIO(b"[]")))
    with pytest.raises(ValueError, match="belongs to another project"):
        backup.transfer(target.config, "import", str(file))
    assert target.events == ["inspect", "claim", "verify"]
    assert not target.admitted


@pytest.mark.parametrize("previously_used", [True, False])
def test_import_refuses_existing_or_unowned_targets(target, tmp_path, monkeypatch, previously_used):
    file = tmp_path / "restore.surql"
    file.touch()
    if previously_used:
        target.namespaces = {"team": "DEFINE NAMESPACE team"}
        reason = "fresh, independent store"
    else:
        target.lease = None
        reason = "dynamic endpoint or a registered idle timeout"
    monkeypatch.setattr(backup, "managed_opener", lambda: pytest.fail("Unsafe import started"))
    with pytest.raises(ValueError, match=reason):
        backup.transfer(target.config, "import", str(file))
    assert target.events == (["inspect"] if previously_used else [])
    assert not target.admitted


def test_runtime_cli_routes_native_memory_transfer(monkeypatch, capsys):
    from basepack.__main__ import main
    from basepack.project import config

    monkeypatch.setattr(config, "load_project_config", lambda path: path)
    monkeypatch.setattr(backup, "transfer",
                        lambda project, action, file: {"config": project, "action": action, "file": file})
    monkeypatch.setattr(sys, "argv", ["basepack", "--config", "fixture.toml",
                                     "runtime", "export", "memory", "backup.surql"])
    assert main() == 0
    assert json.loads(capsys.readouterr().out) == {
        "config": "fixture.toml", "action": "export", "file": "backup.surql",
    }

"""Target identity and start admission for managed user tasks."""

from errno import ECONNREFUSED
from http.client import RemoteDisconnected
from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

import pytest

from basepack.embedding import identity
from basepack.runtime import activity_server, control, launcher, listener_owner, surreal_process, windows
from basepack.runtime.recovery import EMBEDDING_DRAINING_HEADER


def test_registration_records_windowless_launcher(monkeypatch, tmp_path):
    python = tmp_path / "runtime" / "Scripts" / "python.exe"
    pythonw = python.with_name("pythonw.exe")
    pythonw.parent.mkdir(parents=True)
    pythonw.touch()
    target = {"python": str(python), "task_name": "BasePack.User.Embedding",
              "endpoint": "http://127.0.0.1:18288", "model_root": str(tmp_path), "settings": {}}
    monkeypatch.setattr(control, "_target", lambda *_: target)
    monkeypatch.setattr(control, "_registered_python", Mock())
    monkeypatch.setattr(identity, "embedding_identity", lambda _: "test-identity")
    register = Mock(return_value={"status": "registered"})
    monkeypatch.setattr(windows, "register_task", register)

    control.register(SimpleNamespace(machine=None), "embedding", surreal_exe=None, store=None,
                     create_store=False, at_logon=False)

    binding_path = control._binding_path(target)
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    assert binding == {"target": target, "launcher_python": str(pythonw), "embedding_identity": "test-identity"}
    register.assert_called_once_with(target["task_name"], pythonw,
                                     ["-I", "-B", "-u", "-m", "basepack.runtime.launcher", str(binding_path)],
                                     binding_path.parent, at_logon=False)


@pytest.mark.parametrize("launcher_name", ["python.exe", "pythonw.exe"])
def test_management_uses_registered_launcher(monkeypatch, tmp_path, launcher_name):
    python = tmp_path / "runtime" / "Scripts" / "python.exe"
    target = {"python": str(python), "task_name": "BasePack.User.Embedding", "endpoint": "http://127.0.0.1:18288"}
    binding = {"target": target}
    if launcher_name == "pythonw.exe":
        binding["launcher_python"] = str(python.with_name(launcher_name))
    binding_path = control._binding_path(target)
    binding_path.parent.mkdir(parents=True)
    binding_path.write_text(json.dumps(binding), encoding="utf-8")
    monkeypatch.setattr(control, "_target", lambda *_: target)
    operate = Mock(return_value={"status": "stopped"})
    monkeypatch.setattr(windows, "task_operation", operate)

    assert control.manage_embedding(None, "stop")["status"] == "stopped"
    operate.assert_called_once_with("stop", target["task_name"], python.with_name(launcher_name),
                                    ["-I", "-B", "-u", "-m", "basepack.runtime.launcher", str(binding_path)],
                                    binding_path.parent)


@pytest.mark.parametrize("launcher_name", ["python.exe", "pythonw.exe"])
def test_launcher_runs_worker_with_bound_interpreter_and_redirected_logs(monkeypatch, tmp_path, launcher_name):
    python = tmp_path / "runtime" / "Scripts" / "python.exe"
    expected_python = python.with_name(launcher_name)
    target = {"python": str(python), "component": "embedding", "task_name": "BasePack.User.Embedding"}
    binding = {"target": target}
    if launcher_name == "pythonw.exe":
        binding["launcher_python"] = str(expected_python)
    binding_path = control._binding_path(target)
    binding_path.parent.mkdir(parents=True)
    binding_path.write_text(json.dumps(binding), encoding="utf-8")
    monkeypatch.setattr(launcher.sys, "executable", str(expected_python))
    monkeypatch.setattr(launcher, "install_process_job", Mock())
    monkeypatch.setattr(launcher.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    run = Mock(return_value=SimpleNamespace(returncode=0))
    monkeypatch.setattr(launcher.subprocess, "run", run)

    assert launcher.main(binding_path, embedding_worker=False) == 0
    assert run.call_args.args == ([str(expected_python), "-I", "-B", "-u", "-m", "basepack.runtime.launcher",
                                  str(binding_path), "--embedding-worker"],)
    assert run.call_args.kwargs["stdout"].name == str(binding_path.with_suffix(".log"))
    assert run.call_args.kwargs["stderr"] == launcher.subprocess.STDOUT
    assert run.call_args.kwargs["creationflags"] == launcher.subprocess.CREATE_NO_WINDOW

    worker = Mock()
    monkeypatch.setattr(launcher, "_embedding", worker)
    assert launcher.main(binding_path, embedding_worker=True) == 0
    worker.assert_called_once_with(binding, binding_path.with_suffix(".log"))

    monkeypatch.setattr(launcher.sys, "executable", str(python.with_name("other.exe")))
    with pytest.raises(ValueError, match="bound interpreter"):
        launcher.main(binding_path, embedding_worker=True)


def test_recovery_uses_running_controller_not_target_interpreter(monkeypatch, tmp_path):
    controller = tmp_path / "controller" / "python.exe"
    target = {
        "python": str(tmp_path / "workspace" / "python.exe"),
        "config": str(tmp_path / "machine.toml"),
        "task_name": "BasePack.User.Embedding",
        "endpoint": "http://127.0.0.1:18288",
    }
    monkeypatch.setattr(control, "_target", lambda *_: target)
    monkeypatch.setattr(control, "_load", lambda _: (None, {}))
    monkeypatch.setattr(control, "_controller_python", lambda: controller)

    argv = control.start_command(None, "embedding")["argv"]
    assert argv == [
        str(controller), "-I", "-B", "-m", "basepack", "runtime",
        "--machine-config", target["config"], "start", "embedding",
    ]


def test_stopped_task_cannot_claim_an_occupied_port(monkeypatch, tmp_path):
    target = {
        "python": str(Path("runtime/python.exe")),
        "task_name": "BasePack.User.Embedding",
        "endpoint": "http://127.0.0.1:18288",
    }
    monkeypatch.setattr(control, "_target", lambda *_: target)
    monkeypatch.setattr(control, "_load", lambda _: (tmp_path / "binding.json", {"target": target}))
    monkeypatch.setattr(control, "_port_in_use", lambda _: True)
    operations = []

    def operate(action, *_):
        operations.append(action)
        return {"status": "stopped"}

    monkeypatch.setattr(windows, "task_operation", operate)
    with pytest.raises(RuntimeError, match="Endpoint already in use"):
        control.manage_embedding(None, "start")
    assert operations == ["status", "status"]


@pytest.mark.parametrize("joined, marked", [("running", False), ("queued", False), ("start-requested", True)])
def test_embedding_start_replaces_a_retiring_task_after_its_listener_closes(monkeypatch, tmp_path, joined, marked):
    target = {"component": "embedding", "python": str(Path("runtime/python.exe")),
              "task_name": "BasePack.User.Embedding", "endpoint": "http://127.0.0.1:18288"}
    binding = {"target": target, "embedding_identity": "fixture"}
    monkeypatch.setattr(control, "_target", lambda *_: target)
    monkeypatch.setattr(control, "_load", lambda _: (tmp_path / "binding.json", binding))
    port_in_use = Mock(side_effect=[True, False])
    monkeypatch.setattr(control, "_port_in_use", port_in_use)
    monkeypatch.setattr(control, "sleep", Mock())
    expected_operations = iter([
        ("status", "running"), ("start", joined),
        ("status", "running"),
        ("status", "stopped"), ("status", "stopped"), ("status", "stopped"),
        ("status", "stopped"), ("status", "stopped"), ("start", "start-requested"),
    ])

    def operate(action, *_):
        expected, state = next(expected_operations)
        assert action == expected
        return {"status": state, "last_task_result": 0}

    expected_requests = iter(["draining" if marked else "disconnected", "disconnected", "refused", "health", "info"])

    def open_(url, *, timeout):
        path = url.rsplit("/", 1)[-1]
        stage = next(expected_requests)
        if stage == "draining":
            assert path == "health"
            raise HTTPError(url, 503, "draining", {EMBEDDING_DRAINING_HEADER: "1"}, BytesIO())
        if stage == "disconnected":
            assert path == "health"
            raise RemoteDisconnected("retiring listener closed before its response")
        if stage == "refused":
            assert path == "health"
            raise URLError(ConnectionRefusedError(ECONNREFUSED, "retired"))
        assert path == stage
        response = BytesIO(b'{"model":{"embedding_identity":"fixture"}}')
        response.status = 200
        return response

    monkeypatch.setattr(windows, "task_operation", operate)
    monkeypatch.setattr(control, "managed_opener", lambda: SimpleNamespace(open=open_))
    result = control.manage_embedding(None, "start")
    assert result["status"] == "start-requested"
    assert result["health"] == 200
    assert result["model"]["embedding_identity"] == "fixture"
    assert list(expected_operations) == list(expected_requests) == []
    assert port_in_use.call_count == 2


def test_embedding_start_joins_replacement_started_by_another_caller(monkeypatch, tmp_path):
    target = {"component": "embedding", "task_name": "BasePack.User.Embedding",
              "endpoint": "http://127.0.0.1:18288"}
    binding = {"target": target, "embedding_identity": "fixture"}
    operate = Mock(side_effect=[{"status": "stopped"}, {"status": "running"}, {"status": "running"}])
    monkeypatch.setattr(control, "_port_in_use", lambda _: True)
    response = BytesIO(b'{"model":{"embedding_identity":"fixture"}}')
    health = BytesIO()
    health.status = 200
    open_ = Mock(side_effect=[health, response])
    monkeypatch.setattr(control, "managed_opener", lambda: SimpleNamespace(open=open_))

    started = control._request_start(operate, target["endpoint"])
    result = control._wait_ready(binding, tmp_path / "binding.log", started, operate)
    assert [call.args for call in operate.call_args_list] == [("status",), ("status",), ("start",)]
    assert result["status"] == "running" and result["health"] == 200


def test_dynamic_memory_readiness_uses_only_unique_owned_listening_port(monkeypatch):
    from contextlib import contextmanager

    process = SimpleNamespace(pid=13, poll=lambda: None)
    listeners = Mock(return_value=(49288,))
    monkeypatch.setattr(listener_owner, "listener_ports", listeners)
    monkeypatch.setattr(listener_owner, "owns_listener", Mock(side_effect=AssertionError))

    @contextmanager
    def ready(url, *, timeout):
        assert url == "http://127.0.0.1:49288/ready"
        yield SimpleNamespace(status=200)

    monkeypatch.setattr(launcher, "managed_opener", lambda: SimpleNamespace(open=ready))
    assert launcher._wait_owned_ready("http://127.0.0.1:0", process) == "http://127.0.0.1:49288"
    assert listeners.call_count == 2
    listeners.assert_called_with("127.0.0.1", process.pid)
    listeners.return_value = (49288, 49111)
    with pytest.raises(RuntimeError, match="Expected one SurrealDB listener"):
        launcher._wait_owned_ready("http://127.0.0.1:0", process)


@pytest.mark.parametrize("fresh", [True, False])
def test_dynamic_memory_fresh_store_has_no_default_namespace(monkeypatch, tmp_path, fresh):
    path = tmp_path / "binding.json"
    store = tmp_path / "store"
    password = tmp_path / "password.txt"
    password.write_text("test", encoding="utf-8")
    if fresh:
        path.with_suffix(".create").touch()
    else:
        store.mkdir()
        (store / "manifest").touch()

    target = {"endpoint": "http://127.0.0.1:0", "memory_dir": str(tmp_path),
              "password_file": str(password), "username": "root"}
    binding = {"target": target, "store": str(store), "surreal_exe": "surreal.exe"}
    launch = Mock(return_value=SimpleNamespace(_handle=7, pid=13))
    monkeypatch.delenv("SURREAL_NO_DEFAULTS", raising=False)
    monkeypatch.setattr(surreal_process, "launch_surreal", launch)
    monkeypatch.setattr(listener_owner, "process_creation_filetime", lambda handle: 42)
    monkeypatch.setattr(launcher, "_wait_owned_ready", lambda *_: "http://127.0.0.1:49288")

    async def run_activity(binding_path, process, *, instance, idle_seconds, pending_publications):
        assert binding_path == path and idle_seconds is None
        assert instance["origin"] == "http://127.0.0.1"
        assert instance["pid"] == 13 and instance["created_filetime"] == 42
        assert instance["endpoint"] == "http://127.0.0.1:49288"
        assert pending_publications() == []
        return 0

    monkeypatch.setattr(activity_server, "run_activity", run_activity)
    assert launcher._memory(binding, path, None) == 0
    assert launch.call_args.args[0][2:6] == ["--bind", "127.0.0.1:0", "--allow-origin", "http://127.0.0.1"]
    assert launch.call_args.kwargs["env"].get("SURREAL_NO_DEFAULTS") == ("true" if fresh else None)
    assert not path.with_suffix(".create").exists()

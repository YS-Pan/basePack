from errno import ECONNREFUSED
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import sys
from threading import Thread
from types import SimpleNamespace
from urllib.error import HTTPError, URLError

import pytest

from basepack.__main__ import main
from basepack.embedding import admin, client
from basepack.memory import store
from basepack.project.config import load_project_config
from basepack.project.init import init_project
from basepack.runtime import activity, control
from basepack.runtime.recovery import EMBEDDING_DRAINING_HEADER


@pytest.fixture
def project(tmp_path):
    machine_path = tmp_path / "machine.toml"
    machine_path.write_text('schema_version=1\n[embedding]\nendpoint="http://127.0.0.1:18081"\n'
                            'windows_task=true\n', encoding="utf-8")
    path = init_project(tmp_path / "project", machine_path, max_concurrent_subagents=1,
                        concurrency_source="test fixture")
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("[memory]\n", "[memory]\nwindows_task=true\n"), encoding="utf-8")
    config = load_project_config(path)
    config.memory_password_file.parent.mkdir(parents=True, exist_ok=True)
    config.memory_password_file.write_text("test credential", encoding="utf-8")
    return config


def _cli(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["basepack", *map(str, args)])
    return main()


def test_runtime_cli_routes_project_registration_and_start(project, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(control, "register", lambda config, *args, **kwargs:
                        calls.append((config.path, args, kwargs)) or {"registered": True})
    monkeypatch.setattr(control, "manage", lambda config, *args:
                        calls.append((config.path, args)) or {"ready": True})
    exe, database = project.root / "surreal.exe", project.memory_dir / "新的库"
    assert _cli(monkeypatch, "--config", project.path, "runtime", "register", "memory", "--surreal-exe", exe,
                "--store", database, "--create-store", "--at-logon", "--idle-seconds", 1800) == 0
    assert json.loads(capsys.readouterr().out) == {"registered": True}
    assert _cli(monkeypatch, "--config", project.path, "runtime", "start", "memory") == 0
    assert json.loads(capsys.readouterr().out) == {"ready": True}
    assert calls == [(project.path, ("memory",), dict(surreal_exe=str(exe), store=str(database),
                                                     create_store=True, at_logon=True, idle_seconds=1800)),
                     (project.path, ("memory", "start"))]


def test_idle_runtime_refuses_before_first_database_request(project, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(control, "_load", lambda _: (tmp_path / "binding.json", {"idle_seconds": 30}))
    command = {"argv": [sys.executable, "--version"]}
    monkeypatch.setattr(control, "start_command", lambda *_: command)
    monkeypatch.setattr(store, "managed_opener", lambda: pytest.fail("SQL opened without activity"))

    assert _cli(monkeypatch, "--config", project.path, "memory", "brief") == 3
    response = json.loads(capsys.readouterr().out)
    assert response["status"] == "runtime_start_required"
    assert response["argv"] == command["argv"]


@pytest.mark.parametrize("args", [("runtime", "--machine-config", "unused", "register", "embedding"),
                                  ("runtime", "--machine-config", "unused", "start", "memory")])
def test_machine_config_requires_existing_embedding_task(monkeypatch, capsys, args):
    with pytest.raises(SystemExit) as error:
        _cli(monkeypatch, *args)
    assert error.value.code == 2
    assert "only for an existing embedding task" in capsys.readouterr().err


@pytest.mark.parametrize("action", ["start", "status", "stop", "unregister"])
def test_runtime_cli_routes_existing_machine_task(project, monkeypatch, capsys, action):
    monkeypatch.setattr(control, "manage_embedding", lambda machine, action:
                        {"machine": str(machine.path), "action": action})
    assert _cli(monkeypatch, "runtime", "--machine-config", project.machine_config, action, "embedding") == 0
    assert json.loads(capsys.readouterr().out) == {"machine": str(project.machine_config), "action": action}


@pytest.mark.parametrize("managed", [True, False])
def test_embedding_stop_uses_selected_backend(project, monkeypatch, capsys, managed):
    if not managed:
        text = project.machine_config.read_text(encoding="utf-8")
        project.machine_config.write_text(text.replace("windows_task=true\n", ""), encoding="utf-8")
    monkeypatch.setattr(admin, "stop", lambda machine: {"mode": "SCM"})
    monkeypatch.setattr(control, "manage_embedding", lambda machine, action: {"mode": "task", "action": action})
    assert _cli(monkeypatch, "embedding", "--machine-config", project.machine_config, "stop") == 0
    assert json.loads(capsys.readouterr().out) == ({"mode": "task", "action": "stop"} if managed else {"mode": "SCM"})


def _refusal():
    return URLError(ConnectionRefusedError(ECONNREFUSED, "fixture connection refused"))


@pytest.mark.parametrize("operation, component, transport, request_path", [
    (("memory", "brief"), "memory", store, "/sql"),
    (("embed", "--text", "text"), "embedding", client, "/predict"),
    (("memory", "embed"), "embedding", admin, "/health"),
])
def test_cli_returns_initial_runtime_refusal_once(project, monkeypatch, capsys, operation, component, transport,
                                                  request_path):
    original = _refusal()
    command = {"task": "任务", "argv": [sys.executable, "--version"]}
    opens = []

    def refuse(request, *, timeout):
        opens.append(request if isinstance(request, str) else request.full_url)
        raise original

    def start_command(config, name):
        assert name == component
        assert config.path == (project.path if component == "memory" else project.machine_config)
        return command

    monkeypatch.setattr(control, "start_command", start_command)
    monkeypatch.setattr(transport, "managed_opener", lambda: SimpleNamespace(open=refuse))
    assert _cli(monkeypatch, "--config", project.path, *operation) == 3
    output = capsys.readouterr()
    assert json.loads(output.out) == {"status": "runtime_start_required", "component": component,
                                     "error": str(original), **command}
    assert output.err == ""
    assert len(opens) == 1 and opens[0].endswith(request_path)


@pytest.mark.parametrize("resource", ["health", "info"])
def test_embedding_status_can_report_retirement(project, monkeypatch, capsys, resource):
    requests = []
    command = {"argv": [sys.executable, "--version"]}

    def open_(url, *, timeout):
        requests.append(url.rsplit("/", 1)[-1])
        if requests[-1] == resource:
            raise HTTPError(url, 503, "retiring", {EMBEDDING_DRAINING_HEADER: "1"}, BytesIO())
        response = BytesIO()
        response.status = 200
        return response

    monkeypatch.setattr(control, "start_command", lambda *_: command)
    monkeypatch.setattr(admin, "managed_opener", lambda: SimpleNamespace(open=open_))
    assert _cli(monkeypatch, "--config", project.path, "memory", "embed") == 3
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "runtime_start_required" and output["argv"] == command["argv"]
    assert requests == (["health", "info"] if resource == "info" else ["health"])


def test_memory_refusal_after_first_open_preserves_original(project, monkeypatch):
    original = _refusal()
    calls = []

    def open_(request, *, timeout):
        calls.append(request.full_url)
        if len(calls) == 1:
            return BytesIO(b'[{"status":"OK","result":1}]')
        raise original

    monkeypatch.setattr(store, "raise_if_managed_refusal", lambda *_: pytest.fail("recovery offered after first open"))
    monkeypatch.setattr(store, "managed_opener", lambda: SimpleNamespace(open=open_))
    with pytest.raises(URLError) as error:
        store.Memory(project)._execute("RETURN 1;")
    assert error.value is original
    assert len(calls) == 2


def test_publication_marker_refusal_preserves_uncertain_commit(project, monkeypatch):
    import websocket

    marker_error = _refusal()
    lost_commit = ConnectionResetError("lost commit response")
    rpc_methods = []

    def send(message):
        rpc_methods.append(json.loads(message)["method"])

    def recv():
        method = rpc_methods[-1]
        if method == "commit":
            raise lost_commit
        return json.dumps({"result": {"begin": "transaction", "query": []}.get(method)})

    def refuse(request, *, timeout):
        assert request.full_url.endswith("/sql")
        raise marker_error

    monkeypatch.setattr(websocket, "create_connection", lambda *_, **kw:
                        SimpleNamespace(send=send, recv=recv, close=lambda: None))
    monkeypatch.setattr(store, "managed_opener", lambda: SimpleNamespace(open=refuse))
    monkeypatch.setattr(store, "raise_if_managed_refusal", lambda *_: pytest.fail("marker offered recovery"))
    with pytest.raises(store.PublicationOutcomeUnknown) as error:
        store.Memory(project)._publish(["BEGIN;", "RETURN 1;", "COMMIT;"])
    assert error.value.__cause__ is lost_commit
    assert error.value.verification_error is marker_error
    assert rpc_methods == ["signin", "use", "begin", "query", "commit"]


def test_dynamic_publication_and_marker_confirmation_reuse_the_current_admission(project, monkeypatch):
    import websocket

    project.raw["memory"]["endpoint"] = "http://127.0.0.1:0"
    memory = store.Memory(project)
    urls, rpc_methods, held = [], [], []

    def send(message):
        rpc_methods.append(json.loads(message)["method"])

    def recv():
        method = rpc_methods[-1]
        if method == "commit":
            raise ConnectionResetError("lost commit response")
        return json.dumps({"result": {"begin": "transaction", "query": []}.get(method)})

    def connect(url, **options):
        urls.append(url)
        assert options["origin"] == "http://127.0.0.1"
        assert options["http_no_proxy"] == ["127.0.0.1"] and options["redirect_limit"] == 0
        return SimpleNamespace(send=send, recv=recv, close=lambda: None)

    def open_(request, *, timeout):
        urls.append(request.full_url)
        assert request.get_header("Authorization").startswith("Basic ")
        if b"SELECT * FROM ONLY" in request.data:
            return BytesIO(b'[{"status":"OK","result":{"committed":true}}]')
        return BytesIO(b'[{"status":"OK","result":null}]')

    monkeypatch.setattr(websocket, "create_connection", connect)
    monkeypatch.setattr(store, "managed_opener", lambda: SimpleNamespace(open=open_))

    def generation(port):
        return SimpleNamespace(endpoint=f"http://127.0.0.1:{port}", origin="http://127.0.0.1",
                               hold=held.append, clear=held.remove)

    token = activity._current.set((project, generation(29000)))
    try:
        memory._publish(["BEGIN;", "RETURN 1;", "COMMIT;"])
    finally:
        activity._current.reset(token)
    assert urls == ["ws://127.0.0.1:29000/rpc", *["http://127.0.0.1:29000/sql"] * 2]
    assert not held
    assert rpc_methods == ["signin", "use", "begin", "query", "commit"]

    token = activity._current.set((project, generation(29001)))
    try:
        memory.verify_project()
    finally:
        activity._current.reset(token)
    assert urls[-1] == "http://127.0.0.1:29001/sql"


def test_dynamic_stale_registration_fails_before_contact(project, monkeypatch, tmp_path):
    path = tmp_path / "binding.json"
    path.write_text(json.dumps({"target": control._target(project, "memory")}), encoding="utf-8")
    project.raw["memory"]["endpoint"] = "http://127.0.0.1:0"
    monkeypatch.setattr(control, "_binding_path", lambda _: path)
    monkeypatch.setattr(activity, "contact", lambda *args, **kwargs: pytest.fail("stale binding admitted activity"))
    monkeypatch.setattr(store, "managed_opener", lambda: pytest.fail("stale binding opened SQL"))
    with pytest.raises(ValueError, match="Config differs from the installed Windows task binding"):
        store.Memory(project).verify_project()


def test_managed_health_preserves_redirect_response():
    paths = []

    class RedirectHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            paths.append(self.path)
            if self.path == "/health":
                self.send_response(302)
                self.send_header("Location", "/unexpected")
                self.end_headers()
            else:
                self.send_error(404)

        def log_message(self, *_):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler) as server:
        thread = Thread(target=server.serve_forever)
        thread.start()
        try:
            machine = SimpleNamespace(raw={"embedding": {"endpoint": f"http://127.0.0.1:{server.server_port}",
                                                         "windows_task": True}})
            with pytest.raises(HTTPError) as error:
                admin.status(machine)
            assert error.value.code == 302
            assert paths == ["/health"]
        finally:
            server.shutdown()
            thread.join()

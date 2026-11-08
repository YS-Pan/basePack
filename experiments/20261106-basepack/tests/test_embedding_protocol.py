"""Protocol and deployment registration contracts without model dependencies."""
import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import urllib.error
import urllib.request

import pytest

from basepack.embedding import registry
from basepack.embedding.registry import atomic_json, marker_path, read_marker
from basepack.embedding.transport import EmbeddingError, PROTOCOL_HEADER, PROTOCOL_VERSION, make_server, rpc
from basepack.project.config import load_machine_config


@contextlib.contextmanager
def running(server):
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()


def test_protocol_roundtrip_preserves_remote_errors_and_checks_marker_version():
    def dispatch(action, payload):
        if action == "fail":
            raise LookupError("original failure detail")
        return {"action": action, "payload": payload}

    with running(make_server("auth", dispatch)) as port:
        marker = {"port": port, "auth": "auth", "protocol_version": PROTOCOL_VERSION}
        assert rpc(marker, "echo", {"text": "中文"}, timeout=2) == {
            "action": "echo", "payload": {"text": "中文"}}
        with pytest.raises(EmbeddingError, match="LookupError: original failure detail") as caught:
            rpc(marker, "fail", timeout=2)
        assert "LookupError" in caught.value.detail["traceback"]
        for version in (None, PROTOCOL_VERSION + 1):
            with pytest.raises(ValueError, match="protocol version"):
                rpc(marker | {"protocol_version": version}, "echo", timeout=2)
        with pytest.raises(ValueError, match="protocol version"):
            rpc(marker | {"protocol_version": PROTOCOL_VERSION + 1}, "echo", timeout=2, allow_legacy=True)


def test_server_rejects_incompatible_request_protocol():
    with running(make_server("auth", lambda *_: {"accepted": True})) as port:
        request = urllib.request.Request(f"http://127.0.0.1:{port}/status", data=b"{}",
            headers={"Authorization": "Bearer auth", PROTOCOL_HEADER: str(PROTOCOL_VERSION + 1)})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with pytest.raises(urllib.error.HTTPError) as caught:
            opener.open(request, timeout=2)
        with caught.value as response:
            error = json.loads(response.read())
        assert error["error"] == "ValueError"
        assert "protocol version" in error["message"]


def test_legacy_transport_is_explicit_for_administration():
    class LegacyHandler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            assert self.headers["Authorization"] == "Bearer legacy-auth"
            raw = json.dumps({"stopping": self.path == "/stop"}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    with running(ThreadingHTTPServer(("127.0.0.1", 0), LegacyHandler)) as port:
        marker = {"port": port, "auth": "legacy-auth", "service_key": "old-deployment"}
        with pytest.raises(ValueError, match="protocol version"):
            rpc(marker, "stop", timeout=2)
        assert rpc(marker, "stop", timeout=2, allow_legacy=True) == {"stopping": True}
        with pytest.raises(ValueError, match="response protocol version"):
            rpc(marker | {"protocol_version": PROTOCOL_VERSION}, "status", timeout=2)


def test_registration_enforces_deployment_and_preserves_legacy_discovery(tmp_path, monkeypatch):
    path = tmp_path / "machine.toml"
    path.write_text("schema_version=1\n[shared]\nstate_dir='state'\n", encoding="utf-8")
    machine = load_machine_config(path)
    marker = marker_path(machine, "broker")
    assert marker == tmp_path / "state/embedding/broker.json"
    marker.parent.mkdir(parents=True)
    monkeypatch.setattr(registry, "deployment_fingerprint", lambda _: "running")
    data = {"protocol_version": PROTOCOL_VERSION, "deployment_fingerprint": "running", "auth": "secret"}
    atomic_json(marker, data)
    assert read_marker(machine, "broker") == data
    monkeypatch.setattr(registry, "deployment_fingerprint", lambda _: "changed")
    with pytest.raises(RuntimeError, match="different code/configuration"):
        read_marker(machine, "broker")
    assert read_marker(machine, "broker", require_match=False) == data
    legacy = {"service_key": "old", "auth": "legacy-secret", "port": 12345}
    atomic_json(marker, legacy)
    with pytest.raises(RuntimeError, match="protocol version"):
        read_marker(machine, "broker")
    assert read_marker(machine, "broker", require_match=False) == legacy


def test_deployment_fingerprint_covers_service_files_and_runtime_settings(tmp_path, monkeypatch):
    package = tmp_path / "package"
    assert {"embedding/registry.py", "embedding/identity.py", "embedding/process_owner.py",
            "embedding/supervisor.py", "embedding/worker.py", "embedding/qwen3_vl.py",
            "embedding/transport.py", "project/config.py"} <= set(registry.SERVICE_FILES)
    assert len(registry.SERVICE_FILES) == len(set(registry.SERVICE_FILES))
    for name in registry.SERVICE_FILES:
        target = package / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(name, encoding="utf-8")
    monkeypatch.setattr(registry, "__file__", str(package / "embedding/registry.py"))
    monkeypatch.setattr(registry, "embedding_identity", lambda _: "fixed-vector-semantics")
    path = tmp_path / "machine.toml"
    path.write_text("""schema_version=1
[shared]
state_dir='state'
[embedding]
model_root='model'
device='cuda:0'
max_length=2048
batch_size=4
max_pixels=1048576
idle_seconds=30
cpu_threads=2
gpu_memory_mib=9216
""", encoding="utf-8")
    machine = load_machine_config(path)
    original = registry.deployment_fingerprint(machine)
    for name in registry.SERVICE_FILES:
        target = package / name
        target.write_text(name + " changed", encoding="utf-8")
        assert registry.deployment_fingerprint(machine) != original, name
        target.write_text(name, encoding="utf-8")
    machine.raw["embedding"]["idle_seconds"] += 1
    assert registry.deployment_fingerprint(machine) != original
    machine.raw["embedding"]["idle_seconds"] -= 1
    machine.raw["shared"]["state_dir"] = "other-state"
    assert registry.deployment_fingerprint(machine) != original

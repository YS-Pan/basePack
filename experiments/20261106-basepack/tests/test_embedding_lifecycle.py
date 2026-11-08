"""Isolated lifecycle regressions; no model or shared machine service is used."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

from basepack.project.config import load_machine_config
from basepack.embedding import admin, supervisor, worker
from basepack.embedding.process_owner import process_alive
from basepack.embedding.registry import marker_path, read_marker, registry_lock
from basepack.embedding.transport import rpc


@pytest.fixture
def machine(tmp_path):
    model = tmp_path / "model"
    model.mkdir()
    (model / "model.lock.json").write_text(json.dumps({
        "model": "fixture", "hf_revision": "fixture", "files": [],
    }), encoding="utf-8")
    path = tmp_path / "machine.toml"
    path.write_text("""schema_version = 1
[shared]
state_dir = 'state'
[embedding]
model_root = 'model'
device = 'cuda:0'
max_length = 2048
batch_size = 4
max_pixels = 1048576
idle_seconds = 30
cpu_threads = 2
gpu_memory_mib = 9216
""", encoding="utf-8")
    return load_machine_config(path)


def await_marker(machine, kind, *, process=None):
    path = marker_path(machine, kind)
    until = time.monotonic() + 10
    while time.monotonic() < until:
        if process is not None:
            assert process.poll() is None
        if path.exists():
            marker = json.loads(path.read_text(encoding="utf-8"))
            if process is None or marker["pid"] == process.pid:
                return marker
        time.sleep(0.01)
    pytest.fail(f"{kind} endpoint was not registered: {path}")


def test_loaded_worker_exits_when_idle_and_keeps_startup_identity(machine, monkeypatch):
    machine.raw["embedding"]["idle_seconds"] = 0.2
    marker_path(machine, "worker").parent.mkdir(parents=True)
    closed = threading.Event()

    class FakeEmbedder:
        def __init__(self, options):
            assert isinstance(options, dict)
            assert options["idle_seconds"] == 0.2
            self.loaded = {"load_count": 1}

        def embed(self, values, **_):
            return {"inputs": values}

        def close(self):
            closed.set()

    thread = threading.Thread(target=worker.serve, args=(machine,),
                              kwargs={"runtime_factory": FakeEmbedder})
    thread.start()
    marker = await_marker(machine, "worker")
    try:
        monkeypatch.setattr(worker, "deployment_fingerprint", lambda _: "disk-changed")
        assert rpc(marker, "status", timeout=5)["deployment_fingerprint"] == marker["deployment_fingerprint"]
        result = rpc(marker, "embed", {"request_id": "idle-test", "inputs": ["text"],
                     "deadline": time.time() + 5}, timeout=5)
        assert result["inputs"] == ["text"]
        thread.join(timeout=5)
        assert not thread.is_alive()
        assert closed.is_set()
        assert not marker_path(machine, "worker").exists()
    finally:
        if thread.is_alive():
            rpc(marker, "stop", timeout=5)
            thread.join(timeout=5)


def test_supervisor_reports_startup_identity_and_admin_compares_target(machine, monkeypatch):
    thread = threading.Thread(target=supervisor.serve, args=(machine,))
    thread.start()
    marker = await_marker(machine, "broker")
    try:
        monkeypatch.setattr(supervisor, "deployment_fingerprint", lambda _: "disk-changed")
        machine.raw["embedding"]["max_length"] = 1024
        result = admin.status(machine)
        assert result["deployment_fingerprint"] == marker["deployment_fingerprint"]
        assert result["target_deployment_fingerprint"] != marker["deployment_fingerprint"]
        assert not result["deployment_matches"]
        with pytest.raises(RuntimeError, match="different code/configuration"):
            read_marker(machine, "broker")
        assert admin.stop(machine)["stopping"]
        thread.join(timeout=5)
        assert not thread.is_alive()
    finally:
        if thread.is_alive():
            admin.stop(machine)
            thread.join(timeout=5)


def test_admin_uses_old_marker_endpoint_and_credentials(machine):
    actions = []

    class LegacyHandler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            assert self.headers["Authorization"] == "Bearer legacy-credential"
            json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            actions.append(self.path)
            result = ({"service_key": "old-generation", "worker_pid": None}
                      if self.path == "/status" else {"stopping": True})
            raw = json.dumps(result).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(("127.0.0.1", 0), LegacyHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    path = marker_path(machine, "broker")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"pid": os.getpid(), "port": server.server_address[1],
        "auth": "legacy-credential", "service_key": "old-generation"}), encoding="utf-8")
    try:
        with pytest.raises(RuntimeError):
            read_marker(machine, "broker")
        result = admin.status(machine)
        assert result["deployment_fingerprint"] == "old-generation"
        assert not result["deployment_matches"]
        assert admin.stop(machine)["stopping"]
        assert actions == ["/status", "/stop"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object ownership")
def test_supervisor_crash_reclaims_worker_and_releases_registry_lock(machine):
    source = str(Path(supervisor.__file__).resolve().parents[2])
    processes = []
    worker_pid = None
    with (machine.path.parent / "supervisor.log").open("wb") as output:
        def launch():
            process = subprocess.Popen([sys.executable, "-m", "basepack.embedding.supervisor",
                "--machine-config", str(machine.path)], stdout=output, stderr=output,
                env=os.environ | {"PYTHONPATH": source}, creationflags=subprocess.CREATE_NO_WINDOW)
            processes.append(process)
            return process

        first = launch()
        try:
            marker = await_marker(machine, "broker", process=first)
            endpoint = rpc(marker, "ensure", {"deadline": time.time() + 10}, timeout=10)
            worker_pid = endpoint["pid"]
            assert process_alive(worker_pid)
            first.kill()
            first.wait(timeout=5)
            until = time.monotonic() + 5
            while process_alive(worker_pid) and time.monotonic() < until:
                time.sleep(0.01)
            assert not process_alive(worker_pid)
            with registry_lock(marker_path(machine, "broker").with_suffix(".lock")):
                pass
            second = launch()
            replacement = await_marker(machine, "broker", process=second)
            endpoint = rpc(replacement, "ensure", {"deadline": time.time() + 10}, timeout=10)
            assert endpoint["pid"] != worker_pid
            worker_pid = endpoint["pid"]
            assert admin.stop(machine)["stopping"]
            assert second.wait(timeout=10) == 0
            assert not process_alive(worker_pid)
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)

"""Regression for shared-request cancellation; these do not replace GPU acceptance."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

from basepack.config import load_machine
from basepack.embedding import worker
from basepack.embedding.client import EmbeddingClient
from basepack.embedding.transport import EmbeddingError, marker_path, read_marker, rpc


@pytest.fixture
def machine(tmp_path):
    model = tmp_path / "model"
    model.mkdir()
    (model / "model.lock.json").write_text(json.dumps({"model": "fixture", "hf_revision": "fixture", "files": []}))
    config = tmp_path / "machine.toml"
    config.write_text('''schema_version = 1
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
''')
    return load_machine(config)


def test_cancel_and_deadline_leave_another_request_and_the_model_alive(machine):
    marker_path(machine, "worker").parent.mkdir(parents=True)
    started, release = threading.Event(), threading.Event()

    class Runtime:
        loads = 0

        def __init__(self, _):
            Runtime.loads += 1
            self.loaded = {"load_count": Runtime.loads}

        def embed(self, values, **_):
            if values == ["blocked"]:
                started.set()
                assert release.wait(10)
            return {"inputs": values, "pid": 123}

        def close(self):
            pass

    server = threading.Thread(target=worker.serve, args=(machine,), kwargs={"runtime_factory": Runtime})
    server.start()
    until = time.monotonic() + 5
    while not marker_path(machine, "worker").exists():
        assert time.monotonic() < until
        time.sleep(0.01)
    marker = read_marker(machine, "worker")

    def embed(identifier, values, timeout=5):
        return rpc(marker, "embed", {"request_id": identifier, "inputs": values,
            "deadline": time.time() + timeout}, timeout=timeout + 2)

    try:
        with ThreadPoolExecutor() as pool:
            blocked = pool.submit(embed, "first", ["blocked"])
            assert started.wait(5)
            other = pool.submit(embed, "second", ["healthy"])
            assert rpc(marker, "cancel", {"request_id": "first", "deadline": time.time()+5}, timeout=5)["cancelled"]
            with pytest.raises(EmbeddingError, match="RequestCancelled"):
                blocked.result(timeout=2)
            with pytest.raises(EmbeddingError, match="RequestDeadline"):
                embed("expired", ["expire while queued"], timeout=0.05)
            release.set()
            assert other.result(timeout=5)["inputs"] == ["healthy"]
            assert embed("after", ["still alive"])["inputs"] == ["still alive"]
            assert Runtime.loads == 1
        # Cancellation arriving before its embed HTTP request must also be honoured.
        rpc(marker, "cancel", {"request_id": "early", "deadline": time.time()+5}, timeout=5)
        with pytest.raises(EmbeddingError, match="RequestCancelled"):
            embed("early", ["must not run"])
    finally:
        release.set()
        rpc(marker, "stop", timeout=5)
        server.join(timeout=5)
        assert not server.is_alive()


def test_concurrent_cold_ensure_and_status_share_one_worker(machine):
    """Real lightweight broker/worker processes, without importing Torch."""
    with (machine.path.parent / "broker.log").open("wb") as log:
        broker = subprocess.Popen([sys.executable, "-m", "basepack.embedding.broker",
            "--machine-config", str(machine.path)], stdout=log, stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        try:
            until = time.monotonic() + 10
            while not marker_path(machine, "broker").exists():
                assert broker.poll() is None
                assert time.monotonic() < until
                time.sleep(0.01)
            marker = read_marker(machine, "broker")
            # Expiring the first caller during endpoint startup must leave one reusable candidate.
            with pytest.raises(EmbeddingError, match="TimeoutError"):
                rpc(marker, "ensure", {"deadline": time.time() - 1}, timeout=5)
            with ThreadPoolExecutor() as pool:
                first = pool.submit(rpc, marker, "ensure", {"deadline": time.time() + 10}, timeout=10)
                states = [pool.submit(rpc, marker, "status", timeout=10) for _ in range(8)]
                second = pool.submit(rpc, marker, "ensure", {"deadline": time.time() + 10}, timeout=10)
                assert first.result()["pid"] == second.result()["pid"]
                assert all(state.result()["worker_starts"] <= 1 for state in states)
                assert rpc(marker, "status", timeout=5)["worker_starts"] == 1
            # A killed worker cannot leave a stale registration that prevents a new cold start.
            previous = first.result()
            from basepack.embedding.owned import process_alive
            import signal
            os.kill(previous["pid"], signal.SIGTERM if os.name == "nt" else signal.SIGKILL)
            replacement = rpc(marker, "ensure", {"deadline": time.time() + 10}, timeout=10)
            assert replacement["pid"] != previous["pid"]
            assert not process_alive(previous["pid"])
            # Administrative stop must still work after a code/configuration upgrade.
            machine.raw["embedding"]["max_length"] = 1024
            client = EmbeddingClient(machine)
            with pytest.raises(RuntimeError, match="different code/configuration"):
                client.status()
            assert client.stop_service()["stopping"]
            assert broker.wait(timeout=10) == 0
        finally:
            if broker.poll() is None:
                broker.kill()
                broker.wait()


def test_client_cancel_covers_cold_endpoint_startup(machine, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    client = EmbeddingClient(machine)
    monkeypatch.setattr(client, "_broker", lambda: {})

    def exchange(_, action, *args, **kwargs):
        assert action == "ensure"  # Cancelled input must never be sent to the worker.
        entered.set()
        assert release.wait(5)
        return {}

    monkeypatch.setattr("basepack.embedding.client.rpc", exchange)
    with ThreadPoolExecutor() as pool:
        request = pool.submit(client.embed, ["cold input"], request_id="cold")
        assert entered.wait(5)
        assert client.cancel("cold")["cancelled"]
        release.set()
        with pytest.raises(EmbeddingError, match="RequestCancelled"):
            request.result(timeout=5)

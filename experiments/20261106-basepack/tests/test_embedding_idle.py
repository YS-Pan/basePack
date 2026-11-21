"""Exercise managed admission, native queue completion and idle shutdown."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
import json
import multiprocessing as mp
import os
from socket import socket
from threading import Barrier
from time import monotonic, sleep
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener

import pytest

from basepack.embedding.client import EmbeddingClient
from basepack.embedding.idle import EmbeddingIdle, IdleCacheRequest, idle_seconds
from basepack.embedding.service import EmbeddingAPI, EmbeddingServer
from basepack.runtime.recovery import EMBEDDING_DRAINING_HEADER, refused


class GateAPI(EmbeddingAPI):
    def __init__(self, path, started, release):
        super().__init__({})
        self.path = path
        self.started = started
        self.release = release

    def setup(self, device):
        self.ready_at.value = monotonic()

    def predict(self, inputs):
        if isinstance(inputs, IdleCacheRequest):
            value = "cache"
        else:
            value = inputs[0]
            if value == "hold":
                self.started.set()
                assert self.release.wait(20)
        with self.path.open("a", encoding="utf-8") as stream:
            print(value, file=stream)
        return {"pid": os.getpid(), "input": value}


def run_fixture(port, api):
    if os.name == "nt":
        from basepack.runtime.job import install_process_job
        install_process_job()
    server = EmbeddingServer(api, accelerator="cpu", devices=1, restart_workers=True,
                             cache_seconds=0.25, stop_seconds=2)

    @server.app.get("/fixture-queue-depth")
    async def depth():
        return server._get_request_queue(api.api_path).qsize()

    server.run(host="127.0.0.1", port=port, num_api_servers=1, generate_client_file=False)


def until(check, timeout):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        if check():
            return
        sleep(0.02)
    pytest.fail(f"Timed out waiting for {check}")


def test_idle_defaults_and_managed_only_stop():
    assert idle_seconds({}, True) == (60, 1800)
    assert idle_seconds({}, False) == (60, None)
    assert idle_seconds({"idle_cache_seconds": 0.5, "idle_stop_seconds": 2}, True) == (0.5, 2)
    with pytest.raises(ValueError, match="must exceed"):
        idle_seconds({"idle_stop_seconds": 60}, True)


def test_replacement_model_gets_its_own_idle_cache_release_without_a_request():
    async def run():
        cache = asyncio.Queue()
        ready = SimpleNamespace(value=monotonic())
        idle = EmbeddingIdle(ready, 0.05, None)

        async def clear():
            cache.put_nowait(ready.value)

        monitor = asyncio.create_task(idle.monitor(clear, None))
        try:
            assert await asyncio.wait_for(cache.get(), 1) == ready.value
            ready.value = monotonic()
            assert await asyncio.wait_for(cache.get(), 1) == ready.value
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(cache.get(), 0.12)
        finally:
            monitor.cancel()
            with suppress(asyncio.CancelledError):
                await monitor

    asyncio.run(run())


def test_disconnect_and_queue_survive_deadlines_then_probe_only_service_retires(tmp_path):
    ctx = mp.get_context("spawn")
    with socket() as available:
        available.bind(("127.0.0.1", 0))
        port = available.getsockname()[1]
    endpoint = f"http://127.0.0.1:{port}"
    client = EmbeddingClient(SimpleNamespace(raw={"embedding": {"endpoint": endpoint}}))
    opener = build_opener(ProxyHandler({}))
    path = tmp_path / "worker-events"
    started, release = ctx.Event(), ctx.Event()
    process = ctx.Process(target=run_fixture, args=(port, GateAPI(path, started, release)))
    process.start()

    def healthy():
        assert process.is_alive(), process.exitcode
        try:
            with opener.open(endpoint + "/health", timeout=3) as response:
                return response.status == 200
        except URLError as error:
            if not refused(error):
                raise
            return False

    try:
        until(healthy, 60)
        with ThreadPoolExecutor() as pool:
            abandoned = pool.submit(client.embed, ["hold"], timeout=0.4)
            assert started.wait(3)
            with pytest.raises(TimeoutError):
                abandoned.result()
            # Even after both deadlines the disconnected request is still running.
            sleep(2)
            assert healthy()
            queued = pool.submit(client.embed, ["queued"], timeout=9)

            def in_queue():
                with opener.open(endpoint + "/fixture-queue-depth", timeout=2) as response:
                    return json.load(response) == 1

            until(in_queue, 3)
            release.set()
            first_pid = queued.result()["pid"]
        until(lambda: path.read_text().endswith("queued\ncache\n"), 3)
        assert client.embed(["next"]) == {"pid": first_pid, "input": "next"}
        until(lambda: path.read_text().endswith("next\ncache\n"), 3)

        def draining():
            for path in ("/info", "/health"):
                try:
                    with opener.open(endpoint + path, timeout=1) as response:
                        assert response.status == 200
                except HTTPError as error:
                    assert error.code == 503 and error.headers[EMBEDDING_DRAINING_HEADER] == "1"
                    if path == "/health":
                        return True
            return False

        until(draining, 5)
        # Allow time for both callers to be scheduled after observing the first 503.
        sleep(0.2)
        callers = Barrier(2, timeout=2)

        def rejected(project):
            callers.wait()
            with pytest.raises(HTTPError) as failure:
                client.embed([project], timeout=2)
            assert failure.value.code == 503
            assert failure.value.headers[EMBEDDING_DRAINING_HEADER] == "1"

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(rejected, ("project-a", "project-b")))
        process.join(10)
        assert process.exitcode == 0
        assert path.read_text().splitlines()[-5:] == ["hold", "queued", "cache", "next", "cache"]
    finally:
        release.set()
        if process.is_alive():
            process.terminate()
        process.join(5)

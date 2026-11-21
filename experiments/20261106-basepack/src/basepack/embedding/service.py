"""LitServe adapter for local embedding and its Windows user-task lifecycle."""

import asyncio
from contextlib import asynccontextmanager, suppress
from importlib.metadata import version
import logging
from multiprocessing import get_context
from pathlib import Path
import sys
from threading import Thread
from time import monotonic
from urllib.parse import urlsplit

from fastapi import HTTPException
from litserve import LitAPI, LitServer, configure_logging
from litserve.loops.base import _SENTINEL_VALUE
from litserve.server import RegularRequestHandler, _MCP_AVAILABLE
import uvicorn

from .identity import DTYPE, embedding_identity
from .idle import AdmissionMiddleware, EmbeddingIdle, IdleCacheRequest, idle_seconds
from .qwen3_vl import (
    SUPPORTED_CONTEXT_TOKENS, EmbeddingInputError, Qwen3VLEmbedder, attention_backend, resolve_device,
)


class EmbeddingAPI(LitAPI):
    def __init__(self, options, *, worker_log: Path | None = None):
        super().__init__(max_batch_size=1)
        self.options = options
        self.worker_log = worker_log
        self.ready_at = get_context("spawn").Value("d", 0.0)

    def setup(self, device):
        if self.worker_log is not None and (sys.stdout is None or sys.stderr is None):
            # A spawned Windows GUI process has no standard streams.
            stream = self.worker_log.open("a", encoding="utf-8", buffering=1)
            if sys.stdout is None:
                sys.stdout = stream
            if sys.stderr is None:
                sys.stderr = stream
            configure_logging(stream=stream)
        self.model = Qwen3VLEmbedder(self.options | {"device": device})
        self.ready_at.value = monotonic()

    def decode_request(self, request):
        if isinstance(request, IdleCacheRequest):
            return request
        return request["inputs"]

    def predict(self, inputs):
        if isinstance(inputs, IdleCacheRequest):
            self.model.release_unused_cache(idle=True)
            return {}
        try:
            return self.model.embed(inputs)
        except EmbeddingInputError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error


class EmbeddingServer(LitServer):
    def __init__(self, api, *, cache_seconds, stop_seconds, **kwargs):
        self.cache_seconds = cache_seconds
        self.stop_seconds = stop_seconds
        super().__init__(api, middlewares=[AdmissionMiddleware], **kwargs)

    def launch_single_inference_worker(self, lit_api, worker_id):
        lit_api.ready_at.value = 0.0
        return super().launch_single_inference_worker(lit_api, worker_id)

    @asynccontextmanager
    async def lifespan(self, app):
        async with super().lifespan(app):
            idle = EmbeddingIdle(self.lit_api.ready_at, self.cache_seconds, self.stop_seconds)
            app.state.embedding_idle = idle
            handler = RegularRequestHandler(self.lit_api, self)

            def clear_cache():
                return handler.handle_request(IdleCacheRequest(), IdleCacheRequest)

            monitor = asyncio.create_task(idle.monitor(clear_cache, self._shutdown_event.set))
            try:
                yield
            finally:
                monitor.cancel()
                with suppress(asyncio.CancelledError):
                    await monitor

    def _start_server(self, port, num_uvicorn_servers, log_level, sockets, uvicorn_worker_type, **kwargs):
        if self.stop_seconds is None:
            return super()._start_server(port, num_uvicorn_servers, log_level, sockets, uvicorn_worker_type, **kwargs)
        # LitServe 0.2.19 tries to terminate its Windows HTTP thread as a
        # process. Keep Uvicorn's shutdown handle for this single managed server.
        self.app.response_queue_id = 0
        if _MCP_AVAILABLE:
            from litserve.mcp import _LitMCPServerConnector
            self.mcp_server = _LitMCPServerConnector()
            self.mcp_server.connect_mcp_server(self.litapi_connector.get_mcp_tools(), self.app)
        self.http = uvicorn.Server(uvicorn.Config(self.app, port=port, log_level=log_level,
                                                  timeout_graceful_shutdown=self.uvicorn_graceful_timeout, **kwargs))
        thread = Thread(target=self.http.run, kwargs={"sockets": sockets}, name="LitServer-0")
        thread.start()
        return {0: thread}

    def _perform_graceful_shutdown(self, manager, uvicorn_workers, shutdown_reason):
        if self.stop_seconds is None or not uvicorn_workers:
            return super()._perform_graceful_shutdown(manager, uvicorn_workers, shutdown_reason)
        logging.getLogger("litserve").info("Graceful embedding stop (%s)", shutdown_reason)
        self.http.should_exit = True
        uvicorn_workers[0].join()
        self._get_request_queue(self.lit_api.api_path).put(_SENTINEL_VALUE)
        for worker in self.inference_workers:
            worker.join()
        self._transport.close()
        manager.shutdown()
        for worker in self.inference_workers:
            if worker.exitcode != 0:
                raise ChildProcessError(f"Embedding worker {worker.pid} exited with code {worker.exitcode}")


def serve(machine, *, worker_log: Path | None = None, managed=False):
    configured = machine.raw["embedding"]
    options = configured | {"model_root": str(machine.path_value("embedding", "model_root"))}
    device = resolve_device(configured["device"])
    options["device"] = str(device)
    endpoint = urlsplit(configured["endpoint"])
    cache_seconds, stop_seconds = idle_seconds(configured, managed)
    server = EmbeddingServer(
        EmbeddingAPI(options, worker_log=worker_log),
        cache_seconds=cache_seconds if device.type == "cuda" else None, stop_seconds=stop_seconds,
        accelerator=device.type,
        devices=[device.index if device.index is not None else 0] if device.type == "cuda" else 1,
        workers_per_device=1, timeout=configured["queue_timeout"], restart_workers=True,
        model_metadata={"embedding_identity": embedding_identity(options), "device": str(device), "dtype": DTYPE,
                        "attention_backend": attention_backend(device),
                        "supported_context_tokens": SUPPORTED_CONTEXT_TOKENS,
                        "gpu_memory_mib": configured.get("gpu_memory_mib", 0), "gpu_memory_semantics": "soft_target",
                        "basepack": version("basepack"), "litserve": version("litserve"),
                        "sentence_transformers": version("sentence-transformers")},
    )
    server.run(host=endpoint.hostname, port=endpoint.port, num_api_servers=1, generate_client_file=False)

"""Project-neutral client; it never spawns or owns the shared service."""
from __future__ import annotations

import threading
import time
import uuid

from basepack.project.config import MachineConfig
from .registry import marker_path, read_marker
from .transport import EmbeddingError, rpc


class EmbeddingClient:
    def __init__(self, machine: MachineConfig):
        self.machine = machine
        self._active = {}
        self._lock = threading.Lock()

    def _supervisor(self):
        if not marker_path(self.machine, "broker").exists():
            raise RuntimeError("embedding supervisor is not running; start python -m basepack embedding "
                               f"--machine-config {self.machine.path} serve outside the Condor job tree")
        return read_marker(self.machine, "broker")

    def embed(self, inputs, *, timeout=600, request_id=None, tokens_only=False):
        if timeout <= 0:
            raise ValueError("embedding timeout must be positive")
        request_id = request_id or uuid.uuid4().hex
        deadline = time.time() + timeout
        state = {"worker": None, "deadline": deadline, "cancelled": threading.Event()}
        with self._lock:
            if request_id in self._active:
                raise ValueError("duplicate active embedding request_id")
            self._active[request_id] = state
        try:
            worker = rpc(self._supervisor(), "ensure", {"deadline": deadline}, timeout=timeout)
            with self._lock:
                state["worker"] = worker
            if state["cancelled"].is_set():
                raise EmbeddingError({"error": "RequestCancelled", "message": "this embedding request was cancelled before queuing"})
            remaining = deadline - time.time()
            if remaining <= 0:
                raise TimeoutError("embedding deadline expired during worker endpoint startup")
            # A short transport allowance lets the server return its precise deadline result.
            return rpc(worker, "embed", {"inputs": inputs, "request_id": request_id,
                "deadline": deadline, "tokens_only": tokens_only}, timeout=remaining + 2)
        finally:
            with self._lock:
                self._active.pop(request_id)

    def cancel(self, request_id):
        with self._lock:
            state = self._active.get(request_id)
        if state is None:
            return {"request_id": request_id, "cancelled": False}
        state["cancelled"].set()
        if state["worker"] is None:
            return {"request_id": request_id, "cancelled": True, "queued": False}
        return rpc(state["worker"], "cancel", {"request_id": request_id,
                   "deadline": state["deadline"]}, timeout=5)

    def close(self):
        with self._lock:
            requests = list(self._active)
        return [self.cancel(request_id) for request_id in requests]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

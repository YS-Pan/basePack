"""One broker-owned model process with request-local cancellation and deadlines."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import os
import queue
import secrets
import threading
import time
import traceback

from basepack.project.config import load_machine_config
from .transport import atomic_json, instance_key, make_server, marker_path


@dataclass
class Request:
    payload: dict
    done: threading.Event = field(default_factory=threading.Event)
    cancelled: threading.Event = field(default_factory=threading.Event)
    response: dict | None = None


def serve(machine, *, runtime_factory=None):
    if runtime_factory is None:
        from .runtime import Runtime
        runtime_factory = Runtime
    pending = queue.Queue()
    requests, mutex = {}, threading.Lock()
    cancellations = {}
    stopping = threading.Event()
    state = {"current_request": None, "loaded": None, "last_active": time.monotonic()}

    def dispatch(action, payload):
        if action == "touch":
            with mutex:
                if not stopping.is_set():
                    state["last_active"] = time.monotonic()
                return {"stopping": stopping.is_set(), "pid": os.getpid()}
        if action == "status":
            return {"pid": os.getpid(), "queue_size": pending.qsize(),
                    "current_request": state["current_request"], "loaded": state["loaded"]}
        if action == "stop":
            stopping.set()
            return {"pid": os.getpid(), "stopping": True}
        request_id = payload["request_id"]
        if action == "cancel":
            with mutex:
                request = requests.get(request_id)
                if request:
                    request.cancelled.set()
                    request.response = {"error": "RequestCancelled", "message": "this embedding request was cancelled",
                                        "request_id": request_id, "pid": os.getpid()}
                    request.done.set()
                else:
                    # Cancel may arrive immediately before the embed connection.
                    cancellations[request_id] = payload["deadline"]
            return {"request_id": request_id, "cancelled": True, "queued": request is not None, "pid": os.getpid()}
        if action != "embed":
            raise ValueError(f"unknown embedding action: {action}")
        request = Request(payload)
        with mutex:
            if stopping.is_set():
                raise RuntimeError("embedding worker is stopping")
            for expired in [key for key, deadline in cancellations.items() if deadline < time.time()]:
                cancellations.pop(expired)
            if request_id in cancellations:
                cancellations.pop(request_id)
                return {"error": "RequestCancelled", "message": "this embedding request was cancelled before queuing",
                        "pid": os.getpid(), "request_id": request_id}
            if request_id in requests:
                raise ValueError("duplicate active embedding request_id")
            requests[request_id] = request
            pending.put(request)
            state["last_active"] = time.monotonic()
        remaining = payload["deadline"] - time.time()
        try:
            if remaining <= 0 or not request.done.wait(remaining):
                request.cancelled.set()
                return {"error": "RequestDeadline", "message": "embedding request deadline expired",
                        "request_id": request_id, "pid": os.getpid()}
            return request.response
        finally:
            with mutex:
                requests.pop(request_id)

    auth = secrets.token_hex(32)
    server = make_server(auth, dispatch)
    marker = {"pid": os.getpid(), "port": server.server_address[1], "auth": auth,
              "service_key": instance_key(machine), "created_at": time.time()}
    path = marker_path(machine, "worker")
    atomic_json(path, marker)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    runtime = None
    try:
        while not stopping.is_set():
            try:
                request = pending.get(timeout=0.5)
            except queue.Empty:
                with mutex:
                    if not requests and time.monotonic() - state["last_active"] >= machine.raw["embedding"]["idle_seconds"]:
                        stopping.set()
                        break
                continue
            payload = request.payload
            state["current_request"] = payload["request_id"]
            try:
                if request.cancelled.is_set() or time.time() >= payload["deadline"]:
                    continue
                if runtime is None:
                    runtime = runtime_factory(machine)
                    state["loaded"] = runtime.loaded
                if request.cancelled.is_set() or time.time() >= payload["deadline"]:
                    continue
                result = runtime.embed(payload["inputs"], tokens_only=payload.get("tokens_only", False),
                    cancelled=lambda: request.cancelled.is_set() or time.time() >= payload["deadline"])
                if not request.cancelled.is_set() and time.time() < payload["deadline"]:
                    request.response = {**result, "request_id": payload["request_id"]}
            except Exception as exc:
                request.response = {"error": type(exc).__name__, "message": str(exc),
                    "traceback": traceback.format_exc(), "pid": os.getpid(), "request_id": payload["request_id"]}
                if runtime is None:
                    stopping.set()
            finally:
                if request.response is None:
                    request.response = {"error": "RequestDeadline", "message": "embedding request deadline expired",
                                        "pid": os.getpid(), "request_id": payload["request_id"]}
                request.done.set()
                state["current_request"] = None
                state["last_active"] = time.monotonic()
                pending.task_done()
    finally:
        stopping.set()
        while not pending.empty():
            request = pending.get_nowait()
            request.response = {"error": "WorkerStopped", "message": "embedding worker stopped before request ran",
                                "pid": os.getpid()}
            request.done.set()
        if runtime is not None:
            runtime.close()
        server.shutdown()
        server.server_close()
        if path.exists():
            path.unlink()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine-config", required=True)
    args = parser.parse_args()
    serve(load_machine_config(args.machine_config))


if __name__ == "__main__":
    main()

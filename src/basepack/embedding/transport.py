"""Bounded loopback JSON transport and the single broker registry lock."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import secrets
import traceback

MAX_REQUEST_BYTES = 4 * 1024 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class EmbeddingError(RuntimeError):
    def __init__(self, detail):
        self.detail = detail
        super().__init__(f"{detail['error']}: {detail['message']}")


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def settings(machine):
    configured = machine.raw["embedding"]
    return {"model_root": str(machine.path_value("embedding", "model_root")),
            **{key: configured[key] for key in
               ("device", "max_length", "batch_size", "max_pixels", "idle_seconds", "cpu_threads")}}


def model_identity(machine):
    root = machine.path_value("embedding", "model_root")
    manifest = json.loads((root / "model.lock.json").read_text(encoding="utf-8"))
    selected = {key: settings(machine)[key] for key in ("max_length", "batch_size", "max_pixels")}
    return "Qwen3-VL:" + hashlib.sha256(json.dumps({
        "model": manifest["model"], "revision": manifest["hf_revision"],
        "files": manifest["files"], "dtype": "float16", "preprocessing": "basepack-v1",
        "limits": selected}, sort_keys=True).encode()).hexdigest()


def instance_key(machine):
    value = [model_identity(machine), settings(machine), machine.raw["embedding"]["gpu_memory_mib"],
             [hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
              for name in ("runtime.py", "worker.py", "broker.py", "transport.py")]]
    return hashlib.sha256(json.dumps(value).encode()).hexdigest()


def directory(machine):
    return machine.state_dir / "embedding"


def marker_path(machine, kind):
    return directory(machine) / f"{kind}.json"


def read_marker(machine, kind):
    path = marker_path(machine, kind)
    marker = json.loads(path.read_text(encoding="utf-8"))
    if marker["service_key"] != instance_key(machine):
        raise RuntimeError(f"embedding {kind} uses different code/configuration; stop it before restarting: {path}")
    return marker


def make_server(auth, dispatch):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            try:
                if not secrets.compare_digest(self.headers.get("Authorization", ""), "Bearer " + auth):
                    raise PermissionError("embedding loopback authentication failed")
                size = int(self.headers["Content-Length"])
                if not 0 <= size <= MAX_REQUEST_BYTES:
                    raise ValueError("embedding request exceeds 4 MiB")
                self.connection.settimeout(10)
                payload = json.loads(self.rfile.read(size))
                result = dispatch(self.path.removeprefix("/"), payload)
                status = 200
            except Exception as exc:
                result = {"error": type(exc).__name__, "message": str(exc),
                          "traceback": traceback.format_exc(), "pid": os.getpid()}
                status = 400
            raw = json.dumps(result, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                # A client deadline ended observation; other requests keep running.
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    return server


def rpc(marker, action, payload=None, *, timeout):
    raw = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
    if len(raw) > MAX_REQUEST_BYTES:
        raise ValueError("embedding JSON request exceeds 4 MiB")
    request = urllib.request.Request(f"http://127.0.0.1:{marker['port']}/{action}", data=raw,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + marker["auth"]})
    # Explicitly bypass proxy variables for this local IPC connection.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=timeout) as response:
            raw_response = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raw_response = exc.read(MAX_RESPONSE_BYTES + 1)
    if len(raw_response) > MAX_RESPONSE_BYTES:
        raise ValueError("embedding JSON response exceeds 2 MiB")
    result = json.loads(raw_response)
    if "error" in result:
        raise EmbeddingError(result)
    return result


@contextlib.contextmanager
def registry_lock(path):
    """An OS-held lock, released even when the broker crashes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0"); stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield

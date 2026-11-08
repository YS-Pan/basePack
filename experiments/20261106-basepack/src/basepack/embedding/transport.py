"""Bounded, versioned loopback JSON transport and remote errors."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import secrets
import traceback

PROTOCOL_VERSION = 1
PROTOCOL_HEADER = "X-BasePack-Protocol"
MAX_REQUEST_BYTES = 4 * 1024 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class EmbeddingError(RuntimeError):
    def __init__(self, detail):
        self.detail = detail
        super().__init__(f"{detail['error']}: {detail['message']}")


def make_server(auth, dispatch):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            try:
                if not secrets.compare_digest(self.headers.get("Authorization", ""), "Bearer " + auth):
                    raise PermissionError("embedding loopback authentication failed")
                if self.headers.get(PROTOCOL_HEADER) != str(PROTOCOL_VERSION):
                    raise ValueError(f"unsupported embedding protocol version: {self.headers.get(PROTOCOL_HEADER)!r}")
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
            self.send_header(PROTOCOL_HEADER, str(PROTOCOL_VERSION))
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                # A client deadline ended observation; other requests keep running.
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    return server


def rpc(marker, action, payload=None, *, timeout, allow_legacy=False):
    version = marker.get("protocol_version")
    if version != PROTOCOL_VERSION and not (allow_legacy and version is None):
        raise ValueError(f"unsupported embedding protocol version: {version!r}")
    raw = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
    if len(raw) > MAX_REQUEST_BYTES:
        raise ValueError("embedding JSON request exceeds 4 MiB")
    request = urllib.request.Request(f"http://127.0.0.1:{marker['port']}/{action}", data=raw,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + marker["auth"],
                 PROTOCOL_HEADER: str(PROTOCOL_VERSION)})
    # Explicitly bypass proxy variables for this local IPC connection.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        response = opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        version = response.headers.get(PROTOCOL_HEADER)
        if version != str(PROTOCOL_VERSION) and not (allow_legacy and version is None):
            raise ValueError(f"unsupported embedding response protocol version: {version!r}")
        raw_response = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw_response) > MAX_RESPONSE_BYTES:
        raise ValueError("embedding JSON response exceeds 2 MiB")
    result = json.loads(raw_response)
    if "error" in result:
        raise EmbeddingError(result)
    return result

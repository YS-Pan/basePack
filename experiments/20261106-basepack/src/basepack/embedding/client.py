"""Project-neutral HTTP client for the independently hosted LitServe service."""

import json
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from basepack.runtime.http import managed_opener
from basepack.runtime.recovery import managed, raise_if_managed_refusal


class EmbeddingClient:
    def __init__(self, machine):
        self.machine = machine
        self.endpoint = machine.raw["embedding"]["endpoint"].rstrip("/")

    def embed(self, inputs, *, timeout=600):
        """Wait at most timeout seconds; expiry does not cancel shared inference."""
        if timeout <= 0:
            raise ValueError("embedding timeout must be positive")
        request = Request(self.endpoint + "/predict",
                          data=json.dumps({"inputs": inputs}).encode("utf-8"),
                          headers={"Content-Type": "application/json"})
        opener = managed_opener() if managed(self.machine, "embedding") else build_opener(ProxyHandler({}))
        try:
            response = opener.open(request, timeout=timeout)
        except OSError as error:
            raise_if_managed_refusal(error, "embedding", self.machine)
            if isinstance(error, HTTPError):
                # Peek leaves the native error body available to its caller.
                body = error.fp.peek(4096)[:4096].decode("utf-8", errors="replace")
                error.add_note(f"Embedding service response (up to 4096 bytes): {body}")
            raise
        with response as stream:
            return json.load(stream)

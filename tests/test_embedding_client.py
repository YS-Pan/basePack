"""Client request-state regressions using an in-memory transport."""
from concurrent.futures import ThreadPoolExecutor
import threading

import pytest

from basepack.embedding.client import EmbeddingClient
from basepack.embedding.transport import EmbeddingError


@pytest.mark.parametrize("cancel", [False, True])
def test_duplicate_active_id_preserves_first_request(monkeypatch, cancel):
    client = EmbeddingClient(object())
    worker = {"endpoint": "fixture"}
    entered, release, cancelled = threading.Event(), threading.Event(), threading.Event()
    monkeypatch.setattr(client, "_supervisor", lambda: {})

    def exchange(marker, action, payload, **_):
        if action == "ensure":
            return worker
        assert marker is worker
        if action == "cancel":
            assert payload["request_id"] == "shared"
            cancelled.set()
            return {"request_id": "shared", "cancelled": True}
        assert action == "embed"
        if payload["request_id"] == "shared":
            entered.set()
            assert release.wait(5)
            if cancelled.is_set():
                raise EmbeddingError({"error": "RequestCancelled", "message": "cancelled"})
        return {"request_id": payload["request_id"], "inputs": payload["inputs"]}

    monkeypatch.setattr("basepack.embedding.client.rpc", exchange)
    with ThreadPoolExecutor() as pool:
        first = pool.submit(client.embed, ["first"], request_id="shared")
        try:
            assert entered.wait(5)
            with pytest.raises(ValueError, match="duplicate active embedding request_id"):
                client.embed(["duplicate"], request_id="shared")
            # The rejected call must neither remove nor replace the first call's state.
            assert client._active["shared"]["worker"] is worker
            assert pool.submit(client.embed, ["independent"], request_id="other").result(timeout=5) == {
                "request_id": "other", "inputs": ["independent"]}
            if cancel:
                assert client.cancel("shared")["cancelled"]
        finally:
            release.set()
        if cancel:
            with pytest.raises(EmbeddingError, match="RequestCancelled"):
                first.result(timeout=5)
        else:
            assert first.result(timeout=5) == {"request_id": "shared", "inputs": ["first"]}
    assert client._active == {}
    assert client.close() == []
    assert client.cancel("shared") == {"request_id": "shared", "cancelled": False}
    # A completed ID can be reused.
    cancelled.clear()
    assert client.embed(["reused"], request_id="shared")["inputs"] == ["reused"]

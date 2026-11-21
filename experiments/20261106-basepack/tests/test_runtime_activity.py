import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
from threading import Event
from time import monotonic, sleep
from types import SimpleNamespace

import pytest

from basepack.runtime import activity, control
from basepack.runtime.activity_server import run_activity


_INSTANCE = {"endpoint": "http://127.0.0.1:18288", "origin": "http://127.0.0.1:18288",
             "generation": "fixture", "pid": 13, "created_filetime": 42}


class _Process:
    def __init__(self):
        self.stopping = Event()
        self.exited = Event()
        self.failure = None
        self.stop_count = 0

    def stop(self):
        self.stop_count += 1
        self.stopping.set()
        if self.failure:
            raise self.failure
        assert self.exited.wait(5)

    def wait(self):
        assert self.exited.wait(8)
        return 0

    def poll(self):
        return 0 if self.exited.is_set() else None


def _wait_for(check):
    deadline = monotonic() + 3
    while not check():
        assert monotonic() < deadline
        sleep(0.01)


def _status(path):
    with activity.contact(path, "status") as (_, result):
        return result


@pytest.fixture
def running(tmp_path, request):
    path = tmp_path / "binding.json"
    process = _Process()
    publications = []
    idle_seconds = getattr(request, "param", 0.3)
    instance = _INSTANCE if idle_seconds is not None else _INSTANCE | {"origin": "http://127.0.0.1"}
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(lambda: asyncio.run(run_activity(path, process, instance=instance,
                                 idle_seconds=idle_seconds, pending_publications=lambda: list(publications))))
        try:
            _wait_for(activity.contact_path(path).exists)
            yield path, process, publications
        finally:
            process.exited.set()
            assert future.result(timeout=5) == 0


def test_only_final_completion_restarts_idle_deadline_and_drain_refuses_admission(running):
    path, process, _ = running
    with activity.contact(path, "operation") as (_, first):
        with activity.contact(path, "operation") as (_, second):
            assert first["status"] == second["status"] == "admitted"
            assert _status(path)["active_operations"] == 2
            assert not process.stopping.wait(0.35)
            with activity.contact(path, "stop") as (_, status):
                assert status["active_operations"] == 2
        assert not process.stopping.wait(0.35)
        before_last_close = monotonic()
    assert process.stopping.wait(3)
    assert monotonic() - before_last_close >= 0.29
    with activity.contact(path, "operation") as (_, status):
        assert status["status"] == "draining"


def test_unresolved_owned_publication_blocks_idle_until_recovery(running):
    path, process, publications = running
    publications.append("pending")
    _wait_for(lambda: "idle_blocked" in _status(path))
    assert not process.stopping.is_set()
    with activity.contact(path, "stop") as (_, status):
        assert status["idle_blocked"] == {"pending_publications": ["pending"]}
    publications.clear()
    with activity.contact(path, "operation") as (_, status):
        assert status["status"] == "admitted"
    assert process.stopping.wait(3)


def test_unresolved_ownerless_commit_survives_client_disconnect(running):
    path, process, _ = running
    confirmed, unknown = ("publication_" + digit * 32 for digit in "ab")
    with activity.contact(path, "operation") as (session, _):
        session.hold(confirmed)
        session.clear(confirmed)
        session.hold(unknown)
    _wait_for(lambda: "idle_blocked" in _status(path))
    assert _status(path)["idle_blocked"] == {"unresolved_publications": [unknown]}
    assert not process.stopping.is_set()
    with activity.contact(path, "stop") as (_, status):
        assert status["status"] == "draining"
    assert process.stopping.wait(3)


def test_failed_graceful_signal_keeps_launcher_and_refuses_second_signal(running):
    path, process, _ = running
    process.failure = OSError("fixture stop failure")
    _wait_for(lambda: _status(path)["status"] == "shutdown-failed")
    assert not process.exited.is_set()
    with activity.contact(path, "stop") as (_, status):
        assert status["shutdown_error"] == "fixture stop failure"
    assert process.stop_count == 1


@pytest.mark.parametrize("running", [None], indirect=True)
def test_dynamic_always_on_has_authenticated_generation_and_no_idle_deadline(running):
    path, process, _ = running
    with activity.contact(path, "operation") as (session, info):
        assert info["status"] == "admitted"
        assert session.endpoint == _INSTANCE["endpoint"]
        assert session.origin == "http://127.0.0.1"
        assert session.database_instance["generation"] == _INSTANCE["generation"]
    _wait_for(lambda: _status(path)["active_operations"] == 0)
    assert "idle_remaining_seconds" not in _status(path)
    assert not process.stopping.wait(0.4)

    with activity.contact(path, "stop") as (_, info):
        assert info["status"] == "draining"
    assert process.stopping.wait(3)


@pytest.mark.parametrize("running", [None], indirect=True)
def test_contact_cannot_mix_endpoint_and_generation_after_reload(running):
    path, _, _ = running
    contact = activity.contact_path(path)
    binding = json.loads(contact.read_text(encoding="utf-8"))
    binding["database_instance"]["generation"] = "different-generation"
    contact.write_text(json.dumps(binding), encoding="utf-8")
    with pytest.raises(activity.ActivityUnavailable, match="different database generation"):
        with activity.contact(path, "operation"):
            pytest.fail("mismatched generation was admitted")


def test_start_waits_for_draining_generation_before_demanding_fresh_task(monkeypatch, tmp_path):
    actions = []
    state = "running"
    generation = 0

    @contextmanager
    def contact(_path, action):
        nonlocal state
        assert action == "operation"
        if not generation:
            yield None, {"status": "draining"}
            state = "stopped"
        else:
            yield SimpleNamespace(database_instance=_INSTANCE, endpoint=_INSTANCE["endpoint"],
                                  origin=_INSTANCE["origin"]), {"status": "admitted"}

    def operate(action):
        nonlocal generation, state
        actions.append((action, state))
        if action == "start" and state == "stopped":
            state = "start-requested"
            generation += 1
        return {"status": state}

    monkeypatch.setattr(activity, "contact", contact)
    monkeypatch.setattr(control, "_port_in_use", lambda *_: False)
    monkeypatch.setattr(control, "managed_opener", lambda: SimpleNamespace(open=ready))

    @contextmanager
    def ready(*_, **_options):
        yield SimpleNamespace(status=200)

    binding = {"target": {"endpoint": "http://127.0.0.1:18288"}}
    assert control._activity_task(tmp_path / "binding.json", binding, "start", operate) == {
        "status": "start-requested", "health": 200, "endpoint": _INSTANCE["endpoint"],
        "database_instance": _INSTANCE,
    }
    assert actions == [("status", "running"), ("start", "running"), ("status", "stopped"),
                       ("status", "stopped"), ("start", "stopped")]


@pytest.mark.parametrize("running", [None], indirect=True)
def test_dynamic_start_and_status_use_resolved_database_endpoint(running, monkeypatch):
    path, _, _ = running
    monkeypatch.setattr(control, "_port_in_use", lambda *_: pytest.fail("attempted to connect to port zero"))
    calls = []

    @contextmanager
    def ready(url, *, timeout):
        calls.append(url)
        yield SimpleNamespace(status=200)

    monkeypatch.setattr(control, "managed_opener", lambda: SimpleNamespace(open=ready))
    binding = {"target": {"endpoint": activity.DYNAMIC_MEMORY_ENDPOINT}}
    operate = lambda action: {"status": "running"} if action in ("start", "status") else pytest.fail(action)
    for action in ("start", "status"):
        result = control._activity_task(path, binding, action, operate)
        assert result["endpoint"] == _INSTANCE["endpoint"]
        assert result["database_instance"]["generation"] == _INSTANCE["generation"]
        assert result["database_instance"]["pid"] == _INSTANCE["pid"]
    assert calls == [_INSTANCE["endpoint"] + "/ready"]

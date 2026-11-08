from argparse import Namespace
import json
import subprocess
import sys

import pytest

from basepack.jobs import CondorClient, JobSpec
from basepack.jobs import client as jobs_client
from basepack.jobs import cli


@pytest.fixture
def client():
    return CondorClient.__new__(CondorClient)


@pytest.mark.parametrize("state", ["queued", "running", "held"])
def test_wait_only_observes_and_never_cancels_active_work(client, state):
    observed = {"job_id": "123.0", "state": state, "terminal": False, "event_log": "events.log"}
    client.status = lambda job_id: observed
    client.cancel = lambda *args, **kwargs: pytest.fail("wait must not cancel")
    result = client.wait("123.0", timeout=0)
    assert result["state"] == state
    if state != "held":
        assert result["observation_expired"]


def test_wait_confirms_terminal_cleanup(client):
    client.status = lambda job_id: {"state": "completed", "terminal": True, "success": True}
    checked = []
    client._confirm_cleanup = lambda job_id: checked.append(job_id) or {"cleanup_confirmed": True}
    result = client.wait("123.0", timeout=0)
    assert result["success"] and result["cleanup_confirmed"]
    assert checked == ["123.0"]


@pytest.mark.parametrize("started,expected", [(None, "queue"), (5, "execution")])
def test_run_cancels_jobs_when_their_own_limit_expires(client, monkeypatch, started, expected):
    monkeypatch.setattr(jobs_client.time, "time", lambda: 20)
    client.submit = lambda spec: {"job_id": "123.0"}
    client.status = lambda job_id: {"state": "running" if started else "queued", "terminal": False,
                                    "event_log": "events.log"}
    client._ad = lambda job_id: ({"QDate": 0, "JobCurrentStartExecutingDate": started,
                                 "BasePackQueueTimeout": 10, "BasePackRunTimeout": 10}, False)
    cancelled = []
    client.cancel = lambda job_id: cancelled.append(job_id) or {"state": "removed", "cleanup_confirmed": True}
    result = client.run(JobSpec(executable=sys.executable, queue_timeout=10, run_timeout=10))
    assert result["timeout"] == expected
    assert result["cleanup_confirmed"]
    assert cancelled == ["123.0"]


def test_run_cancels_after_overall_observation_deadline(client, monkeypatch):
    ticks = iter([0, 100])
    monkeypatch.setattr(jobs_client.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(jobs_client.time, "time", lambda: 0)
    client.submit = lambda spec: {"job_id": "123.0"}
    client.status = lambda job_id: {"state": "queued", "terminal": False, "event_log": "events.log"}
    client._ad = lambda job_id: ({"QDate": 0, "BasePackQueueTimeout": 1, "BasePackRunTimeout": 1}, False)
    cancelled = []
    client.cancel = lambda job_id: cancelled.append(job_id) or {"state": "removed", "cleanup_confirmed": True}
    result = client.run(JobSpec(executable=sys.executable, queue_timeout=1, run_timeout=1))
    assert result["timeout"] == "overall"
    assert cancelled == ["123.0"]


def test_cancel_preserves_native_removal_error(client):
    client._ad = lambda job_id: ({}, False)
    client._call = lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, "native stdout", "native stderr")
    client.status = lambda job_id: {"state": "running", "terminal": False}
    client._confirm_cleanup = lambda *args: pytest.fail("failed native removal must not imply cleanup")
    result = client.cancel("123.0")
    assert not result["cleanup_confirmed"]
    assert result["cleanup_error"] == "native stdoutnative stderr"


def test_cancel_terminal_job_confirms_cleanup_without_removal(client):
    client._ad = lambda job_id: ({}, True)
    client._call = lambda *args, **kwargs: pytest.fail("terminal history must not issue removal")
    checked = []
    client._confirm_cleanup = lambda job_id, timeout, expected_pids: checked.append(job_id) or {"cleanup_confirmed": True}
    client.status = lambda job_id: {"state": "completed", "terminal": True}
    assert client.cancel("123.0")["cleanup_confirmed"]
    assert checked == ["123.0"]


@pytest.mark.parametrize("history,processes,confirmed", [
    (False, {}, False),
    (True, {21: 1}, False),
    (True, {}, True),
])
def test_cleanup_requires_native_history_and_known_processes_gone(client, monkeypatch, history, processes, confirmed):
    client._ad = lambda job_id: ({}, history)
    monkeypatch.setattr(jobs_client, "_process_parents", lambda: processes)
    result = client._confirm_cleanup("123.0", timeout=0, expected_pids={21})
    assert result["cleanup_confirmed"] is confirmed
    if confirmed:
        assert result["checked_pids"] == [21]
    else:
        assert "deadline" in result["cleanup_error"]


def test_cleanup_preserves_process_observation_error(client, monkeypatch):
    client._ad = lambda job_id: ({}, True)

    def fail():
        raise OSError("original process snapshot failure")

    monkeypatch.setattr(jobs_client, "_process_parents", fail)
    result = client._confirm_cleanup("123.0", timeout=0)
    assert result == {"cleanup_confirmed": False, "cleanup_error": "original process snapshot failure"}


@pytest.mark.parametrize("action,answer,code", [
    ("run", {"success": True, "cleanup_confirmed": True}, 0),
    ("run", {"success": False, "cleanup_confirmed": True}, 1),
    ("run", {"success": True, "cleanup_confirmed": False}, 1),
    ("wait", {"terminal": True, "success": True, "cleanup_confirmed": True}, 0),
    ("wait", {"terminal": True, "success": False, "cleanup_confirmed": True}, 0),
    ("cancel", {"cleanup_confirmed": True}, 0),
    ("cancel", {"cleanup_confirmed": False}, 1),
])
def test_cli_owns_success_and_cleanup_exit_status(monkeypatch, tmp_path, action, answer, code):
    class FakeClient:
        def __init__(self, config):
            pass

        def run(self, spec):
            return answer

        def wait(self, job_id, timeout):
            return answer

        def cancel(self, job_id):
            return answer

    monkeypatch.setattr(cli, "CondorClient", FakeClient)
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"executable": sys.executable}), encoding="utf-8")
    args = Namespace(jobs_action=action, spec=str(spec), job_id="123.0", timeout=0)
    result, exit_code = cli.dispatch(args, object())
    assert result is answer
    assert exit_code == code

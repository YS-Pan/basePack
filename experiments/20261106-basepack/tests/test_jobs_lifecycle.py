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


def test_wait_native_timeout_returns_latest_state_without_cancelling(client):
    states = iter([{"state": "queued", "terminal": False, "event_log": "events.log"},
                   {"job_id": "123.0", "state": "running", "terminal": False}])
    client.status = lambda job_id: next(states)
    calls = []
    def call(*args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 1, "Time expired.\n", "")
    client._call = call
    client.cancel = lambda *args: pytest.fail("wait must not cancel")
    result = client.wait("123.0", timeout=4)
    assert result["observation_expired"] and result["state"] == "running"
    assert calls[0][0][:2] == ("condor_wait", "-wait")
    assert calls[0][1]["timeout"] is None


@pytest.mark.parametrize("state", ["completed", "removed", "held"])
def test_wait_reports_native_outcome_after_timeout(client, state):
    states = iter([{"state": "queued", "terminal": False, "event_log": "events.log"},
                   {"state": state, "terminal": state != "held"}])
    client.status = lambda job_id: next(states)
    client._call = lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, "Time expired.\n", "")
    result = client.wait("123.0", timeout=4)
    assert result["state"] == state and "observation_expired" not in result


def test_wait_reports_terminal_after_native_success(client, monkeypatch):
    states = iter([{"state": "running", "terminal": False, "event_log": "events.log"},
                   {"state": "completed", "terminal": True, "success": True}])
    client.status = lambda job_id: next(states)
    client._call = lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "", "")
    monkeypatch.setattr(jobs_client.time, "sleep", lambda _: None)
    assert client.wait("123.0", timeout=4)["success"]


def test_wait_preserves_command_error_and_unknown_subprocess_timeout(client):
    client.status = lambda job_id: {"state": "queued", "terminal": False, "event_log": "missing"}
    client._call = lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, "", "Couldn't open log")
    with pytest.raises(RuntimeError, match="Couldn't open log"):
        client.wait("123.0", timeout=4)
    original = subprocess.TimeoutExpired("condor_wait", 4)
    def fail(*args, **kwargs):
        raise original
    client._call = fail
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        client.wait("123.0", timeout=4)
    assert caught.value is original


def test_run_returns_expired_observation_without_cancelling(client):
    client.submit = lambda spec: {"job_id": "123.0"}
    client.wait = lambda job_id, timeout: {"job_id": job_id, "state": "running", "observation_expired": True}
    client.cancel = lambda *args: pytest.fail("run must not cancel")
    assert client.run(JobSpec(executable=sys.executable))["observation_expired"]


def test_cancel_reports_request_separately_from_observed_state(client):
    states = iter([{"state": "running", "terminal": False}, {"state": "running", "terminal": False}])
    client.status = lambda job_id: next(states)
    calls = []
    client._call = lambda *args: calls.append(args)
    result = client.cancel("123.0")
    assert result == {"state": "running", "terminal": False, "cancellation_requested": True}
    assert calls == [("condor_rm", "123.0")]


def test_cancel_already_terminal_and_native_error(client):
    client.status = lambda job_id: {"state": "completed", "terminal": True}
    client._call = lambda *args: pytest.fail("terminal job must not issue removal")
    assert client.cancel("123.0")["cancellation_requested"] is False
    client.status = lambda job_id: {"state": "running", "terminal": False}
    def fail(*args):
        raise RuntimeError("native removal error")
    client._call = fail
    with pytest.raises(RuntimeError, match="native removal error"):
        client.cancel("123.0")


@pytest.mark.parametrize("native,expected", [
    ({"CompletionDate": 5, "JobCurrentStartExecutingDate": 8}, (-5, -2, -3)),
    ({"CompletionDate": 5}, (-5, -5, None)),
    ({}, (None, None, None)),
])
def test_status_keeps_raw_negative_durations_and_missing_times(client, monkeypatch, native, expected):
    client.encoding = "utf-8"
    client._ad = lambda job_id: ({"JobStatus": 3, "QDate": 10} | native, True)
    monkeypatch.setattr(jobs_client, "_terminal_time", lambda ad, encoding: ad.get("CompletionDate"))
    result = client.status("123.0")
    assert tuple(result[key] for key in ("elapsed_seconds", "queued_seconds", "running_seconds")) == expected


@pytest.mark.parametrize("code,reason,expected", [
    (46, "超过允许时长", "execution"),
    (47, "超过执行时长", "execution"),
    (3, "execution time exceeded in unrelated policy", None),
    (None, "PeriodicRemove expression evaluated true", None),
])
def test_removed_status_uses_structured_timeout_evidence(client, monkeypatch, code, reason, expected):
    client.encoding = "utf-8"
    client._ad = lambda job_id: ({"JobStatus": 3, "LastJobStatus": 5, "QDate": 10,
        "HoldReasonCode": code, "HoldReasonSubCode": 12, "RemoveReason": reason}, True)
    monkeypatch.setattr(jobs_client, "_terminal_time", lambda *args: None)
    result = client.status("123.0")
    assert result["reason"] == reason
    assert result["hold_reason_code"] == code and result["hold_reason_subcode"] == 12
    assert result["timeout"] == expected


@pytest.mark.parametrize("state", [1, 2, 3])
def test_past_timeout_hold_does_not_classify_a_later_job_state(client, monkeypatch, state):
    client.encoding = "utf-8"
    client._ad = lambda job_id: ({"JobStatus": state, "LastJobStatus": 2, "QDate": 10,
        "HoldReasonCode": 47}, state == 3)
    monkeypatch.setattr(jobs_client, "_terminal_time", lambda *args: None)
    assert client.status("123.0").get("timeout") is None


@pytest.mark.parametrize("action,answer,code", [
    ("run", {"success": True}, 0),
    ("run", {"success": False}, 1),
    ("run", {"observation_expired": True}, 1),
    ("wait", {"terminal": True, "success": False}, 0),
    ("cancel", {"cancellation_requested": True, "terminal": False}, 0),
])
def test_cli_exit_status(monkeypatch, tmp_path, action, answer, code):
    class FakeClient:
        def __init__(self, config): pass
        def run(self, spec): return answer
        def wait(self, job_id, timeout): return answer
        def cancel(self, job_id): return answer
    monkeypatch.setattr(cli, "CondorClient", FakeClient)
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"executable": sys.executable}), encoding="utf-8")
    args = Namespace(jobs_action=action, spec=str(spec), job_id="123.0", timeout=0)
    result, exit_code = cli.dispatch(args, object())
    assert result is answer and exit_code == code

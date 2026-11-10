from argparse import Namespace
import json
import subprocess
import sys

import psutil
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


@pytest.mark.parametrize("history,alive,confirmed", [
    (False, False, False),
    (True, True, False),
    (True, False, True),
])
def test_cleanup_requires_native_history_and_known_processes_gone(client, monkeypatch, history, alive, confirmed):
    client._ad = lambda job_id: ({}, history)
    monkeypatch.setattr(jobs_client.psutil, "pid_exists", lambda pid: alive)
    result = client._confirm_cleanup("123.0", timeout=0, expected_pids={21})
    assert result["cleanup_confirmed"] is confirmed
    if confirmed:
        assert result["checked_pids"] == [21]
    else:
        assert "deadline" in result["cleanup_error"]


def test_cleanup_preserves_process_observation_error(client, monkeypatch):
    client._ad = lambda job_id: ({}, True)

    def fail(pid):
        raise OSError("original process observation failure")

    monkeypatch.setattr(jobs_client.psutil, "pid_exists", fail)
    result = client._confirm_cleanup("123.0", timeout=0, expected_pids={21})
    assert result == {"cleanup_confirmed": False, "cleanup_error": "original process observation failure"}


@pytest.mark.parametrize("native", [{}, {"NumJobStarts": 1}, {"NumJobStarts": 0, "JobCurrentStartExecutingDate": 5}])
def test_cleanup_without_pids_preserves_missing_process_evidence(client, monkeypatch, native):
    client._ad = lambda job_id: (native, True)
    monkeypatch.setattr(jobs_client.psutil, "pid_exists", lambda pid: pytest.fail("no PIDs were observed"))
    result = client._confirm_cleanup("123.0", timeout=0)
    assert not result["cleanup_confirmed"]
    assert result["cleanup_scope"] == "condor_history_only"
    assert "checked_pids" not in result
    assert "No worker PIDs" in result["cleanup_error"]


def test_cleanup_never_started_uses_native_history_without_claiming_pid_checks(client, monkeypatch):
    client._ad = lambda job_id: ({"NumJobStarts": 0}, True)
    monkeypatch.setattr(jobs_client.psutil, "pid_exists", lambda pid: pytest.fail("never started"))
    result = client._confirm_cleanup("123.0", timeout=0)
    assert result == {"cleanup_confirmed": True, "cleanup_scope": "condor_history_never_started"}


def test_cleanup_can_observe_worker_receipt_published_after_cancel(client, monkeypatch):
    observations = iter([({}, False), ({}, True)])
    receipts = iter([set(), {21}])
    client._ad = lambda job_id: next(observations)
    monkeypatch.setattr(jobs_client, "_worker_pids", lambda ad: next(receipts))
    monkeypatch.setattr(jobs_client.psutil, "pid_exists", lambda pid: False)
    monkeypatch.setattr(jobs_client.time, "sleep", lambda _: None)
    result = client._confirm_cleanup("123.0")
    assert result["cleanup_confirmed"] and result["checked_pids"] == [21]


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


@pytest.mark.parametrize("code,reason,expected", [
    (47, "执行时间超过限制", "execution"),
    (3, "execution time mentioned by unrelated hold", None),
])
def test_run_preserves_held_reason_and_uses_code_for_timeout(client, code, reason, expected):
    client.encoding = "utf-8"
    client.submit = lambda spec: {"job_id": "123.0"}
    client._ad = lambda job_id: ({"JobStatus": 5, "QDate": 10, "HoldReason": reason,
        "HoldReasonCode": code, "HoldReasonSubCode": 12}, False)
    client.cancel = lambda job_id: {"state": "removed", "cleanup_confirmed": True}
    result = client.run(JobSpec(executable=sys.executable))
    assert result["original_state"] == "held" and result["reason"] == reason
    assert result["hold_reason_code"] == code and result["hold_reason_subcode"] == 12
    assert result.get("timeout") == expected


def test_completed_job_cleanup_is_independent_of_unrelated_process_metadata(client, monkeypatch):
    class UnrelatedProcess:
        pid = 999

        def ppid(self):
            raise OSError("unrelated process metadata is unavailable")

    client._ad = lambda job_id: ({}, True)
    monkeypatch.setattr(jobs_client.psutil, "process_iter", lambda: iter([UnrelatedProcess()]))
    monkeypatch.setattr(jobs_client.psutil, "pid_exists", lambda pid: False)

    result = client._confirm_cleanup("123.0", timeout=0, expected_pids={21})

    assert result["cleanup_confirmed"]
    assert result["checked_pids"] == [21]


def test_cancel_observes_only_its_known_process_family(client, monkeypatch):
    root = subprocess.Popen([sys.executable, "-u", "-c",
        "import subprocess,sys,time; "
        "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']); "
        "print(child.pid,flush=True); time.sleep(30)"], stdout=subprocess.PIPE, text=True)
    descendant = psutil.Process(int(root.stdout.readline()))
    owned_descendants = psutil.Process(root.pid).children(recursive=True)
    try:
        client._ad = lambda job_id: ({}, False)
        monkeypatch.setattr(jobs_client, "_worker_pids", lambda ad: {root.pid})
        client._call = lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "", "")
        client.status = lambda job_id: {"state": "removed", "terminal": True}
        checked = []
        client._confirm_cleanup = lambda job_id, timeout, pids: checked.append(pids) or {"cleanup_confirmed": True}

        assert client.cancel("123.0")["cleanup_confirmed"]
        # Windows venv launchers can add interpreter processes inside this family.
        assert {root.pid, descendant.pid} <= checked[0]
        assert psutil.Process().pid not in checked[0]
    finally:
        root.terminate()
        root.wait(timeout=5)
        for process in owned_descendants:
            try:
                process.kill()
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(owned_descendants, timeout=5)
        assert not alive
        root.stdout.close()


def test_cancel_still_removes_job_if_known_root_exits_before_observation(client, monkeypatch):
    client._ad = lambda job_id: ({}, False)
    monkeypatch.setattr(jobs_client, "_worker_pids", lambda ad: {21})

    def gone(pid):
        raise psutil.NoSuchProcess(pid)

    monkeypatch.setattr(jobs_client.psutil, "Process", gone)
    removed = []
    client._call = lambda *args, **kwargs: removed.append(args) or subprocess.CompletedProcess(args, 0, "", "")
    client._confirm_cleanup = lambda job_id, timeout, pids: {"cleanup_confirmed": True, "checked_pids": sorted(pids)}
    client.status = lambda job_id: {"state": "removed", "terminal": True}

    result = client.cancel("123.0")

    assert removed == [("condor_rm", "123.0")]
    assert result["cleanup_confirmed"] and result["checked_pids"] == [21]


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

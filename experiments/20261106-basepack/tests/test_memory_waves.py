import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import sys

import pytest

from basepack.memory import owner, waves
from basepack.memory.maintenance import MaintenanceStopped


def setup_wave(tmp_path, *, task_count=1, worker_count=1):
    control = tmp_path / "control"
    run = owner.acquire(tmp_path, "project", "parent", control)["owner"]["run_id"]
    receipt = tmp_path / "source.json"
    receipt.write_text(json.dumps({"owner_run_id": run, "layout": {"organization": "finite-wave-v1"},
                                   "workset": {"included": [f"source-{i}" for i in range(task_count)]}}), encoding="utf-8")
    tasks = [{"id": f"t{i}", "goal": f"goal {i}", "paths": [f"source-{i}"],
              "write_targets": [f"graph-{i}"], "outputs": ["draft"]} for i in range(task_count)]
    workers = [f"w{i}" for i in range(worker_count)]
    wave = waves.create(tmp_path, control, run, receipt, tasks, workers)["wave_id"]
    return control, run, wave, workers


def result_files(tmp_path):
    paths = [tmp_path / f"result-{i}.json" for i in range(3)]
    for index, path in enumerate(paths):
        path.write_text('{"sources": []}' if index == 0 else "{}", encoding="utf-8")
    return paths


def seal_wave(tmp_path, control, run, wave):
    reference = waves.initialization_receipt(tmp_path, control, run, wave)
    assert waves.initialization_receipt(tmp_path, control, run, wave) == reference
    return waves.seal(tmp_path, control, run, wave)


def test_startup_gate_and_unstarted_worker_are_explicit(tmp_path):
    control, run, wave, workers = setup_wave(tmp_path, worker_count=2)
    waves.started(tmp_path, control, run, wave, workers[0], "host-0")
    assert waves.claim(tmp_path, control, run, wave, workers[0])["startup_pending"]
    with pytest.raises(ValueError, match="registered worker"):
        waves.initialization_receipt(tmp_path, control, run, wave)
    with pytest.raises(ValueError, match="initialization receipt"):
        waves.seal(tmp_path, control, run, wave)
    waves.worker_failed(tmp_path, control, run, wave, workers[1], "host did not start")
    seal_wave(tmp_path, control, run, wave)
    draft, coverage, errors = result_files(tmp_path)
    task = waves.claim(tmp_path, control, run, wave, workers[0])["task"]
    waves.submit(tmp_path, control, run, wave, workers[0], task["id"],
                 drafts=[draft], coverage=coverage, errors=errors)
    retired = waves.claim(tmp_path, control, run, wave, workers[0])
    assert retired["retired"] and retired["notification"]["worker"] == workers[0]
    state = waves.inspect(tmp_path, control, run, wave)
    assert state["workers"][workers[1]]["error"] == "host did not start"


def test_zero_started_workers_produce_recovery_receipt_without_notifier(tmp_path):
    control, run, wave, workers = setup_wave(tmp_path)
    waves.worker_failed(tmp_path, control, run, wave, workers[0], "start failed")
    state = seal_wave(tmp_path, control, run, wave)
    assert state["receipt"] and state["notification"] is None
    assert state["tasks"][0]["status"] == "unclaimed"
    assert waves.finish(tmp_path, control, run, wave)["receipt"] == state["receipt"]
    assert waves.close(tmp_path, control, run, wave, no_publication=True)["closed"]


def test_last_host_failure_preserves_claim_and_recovery_receipt(tmp_path):
    control, run, wave, workers = setup_wave(tmp_path, worker_count=2)
    for worker in workers:
        waves.started(tmp_path, control, run, wave, worker, worker)
    seal_wave(tmp_path, control, run, wave)
    waves.claim(tmp_path, control, run, wave, workers[0])
    assert waves.claim(tmp_path, control, run, wave, workers[1])["notification"] is None
    waves.worker_failed(tmp_path, control, run, wave, workers[0], "worker lost")
    state = waves.inspect(tmp_path, control, run, wave)
    assert state["receipt"] and state["notification"] is None
    assert state["tasks"][0]["status"] == "claimed"


def test_two_windows_processes_claim_and_retire_once(tmp_path):
    control, run, wave, workers = setup_wave(tmp_path, task_count=18, worker_count=2)
    for worker in workers:
        waves.started(tmp_path, control, run, wave, worker, "host-" + worker)
    seal_wave(tmp_path, control, run, wave)
    result_files(tmp_path)
    script = r'''
import json, sys, time
from pathlib import Path
from basepack.memory import waves
root, control, run, wave, worker = sys.argv[1:]
root = Path(root)
claimed = []
while True:
    value = waves.claim(root, control, run, wave, worker)
    if value["retired"]:
        print(json.dumps({"claimed": claimed, "notification": value["notification"]}), flush=True)
        break
    task = value["task"]["id"]
    claimed.append(task)
    if len(claimed) == 1:
        (root / (worker + ".ready")).touch()
        deadline = time.monotonic() + 15
        while len(list(root.glob("*.ready"))) < 2:
            if time.monotonic() > deadline:
                raise TimeoutError("Second worker did not claim a task")
            time.sleep(0.01)
    waves.submit(root, control, run, wave, worker, task, drafts=[root / "result-0.json"],
                 coverage=root / "result-1.json", errors=root / "result-2.json")
'''
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    processes = [subprocess.Popen([sys.executable, "-X", "utf8", "-c", script, str(tmp_path), str(control),
                                   run, wave, worker], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True, encoding="utf-8", env=env) for worker in workers]
    rows = []
    for process in processes:
        out, err = process.communicate(timeout=30)
        assert process.returncode == 0, err
        rows.append(json.loads(out))
    claimed = [task for row in rows for task in row["claimed"]]
    assert len(claimed) == 18 and len(set(claimed)) == 18
    notices = [row["notification"] for row in rows if row["notification"]]
    assert len(notices) == 1 and notices[0]["status"] == "eligible"
    state = waves.inspect(tmp_path, control, run, wave)
    assert all(task["status"] == "submitted" for task in state["tasks"])
    assert Path(state["receipt"]["path"]).is_file()
    assert all(datetime.fromisoformat(state[key]).utcoffset() == timedelta(0)
               for key in ("created_at", "sealed_at", "execution_ended_at"))
    for task in state["tasks"]:
        assert datetime.fromisoformat(task["claimed_at"]) <= datetime.fromisoformat(task["submitted_at"])
    for worker in state["workers"].values():
        assert datetime.fromisoformat(worker["retired_at"]) <= datetime.fromisoformat(state["execution_ended_at"])
    receipt = json.loads(Path(state["receipt"]["path"]).read_text(encoding="utf-8"))
    assert receipt["execution_ended_at"] == state["execution_ended_at"]
    assert receipt["tasks"] == state["tasks"] and receipt["workers"] == state["workers"]


def test_failure_retains_claim_and_notification_tracks_host_result(tmp_path):
    control, run, wave, workers = setup_wave(tmp_path, task_count=2, worker_count=2)
    for worker in workers:
        waves.started(tmp_path, control, run, wave, worker, worker)
    seal_wave(tmp_path, control, run, wave)
    claimed = waves.claim(tmp_path, control, run, wave, workers[0])["task"]
    waves.worker_failed(tmp_path, control, run, wave, workers[0], "original host failure")
    draft, coverage, errors = result_files(tmp_path)
    task = waves.claim(tmp_path, control, run, wave, workers[1])["task"]
    waves.submit(tmp_path, control, run, wave, workers[1], task["id"], drafts=[draft],
                 coverage=coverage, errors=errors, failed=True)
    retired = waves.claim(tmp_path, control, run, wave, workers[1])
    assert retired["notification"]["worker"] == workers[1]
    snapshot = json.loads(Path(retired["receipt"]["path"]).read_text(encoding="utf-8"))
    assert [task["status"] for task in snapshot["tasks"]] == ["claimed", "failed"]
    assert snapshot["tasks"][0]["id"] == claimed["id"]
    assert snapshot["workers"][workers[0]]["error"] == "original host failure"
    assert datetime.fromisoformat(snapshot["workers"][workers[0]]["failed_at"]).utcoffset() == timedelta(0)
    waves.notification_pending(tmp_path, control, run, wave, workers[1])
    with pytest.raises(PermissionError):
        waves.notification_pending(tmp_path, control, run, wave, workers[1])
    waves.notification_result(tmp_path, control, run, wave, workers[1], accepted=False, result="host error")
    assert waves.inspect(tmp_path, control, run, wave)["notification"]["result"] == "host error"
    assert not waves.finish(tmp_path, control, run, wave)["already_finished"]
    assert waves.finish(tmp_path, control, run, wave)["already_finished"]
    assert waves.inspect(tmp_path, control, run, wave)["execution_ended_at"] == snapshot["execution_ended_at"]


def test_receipt_survives_state_write_interruption_without_new_times(tmp_path, monkeypatch):
    control, run, wave, workers = setup_wave(tmp_path)
    worker = workers[0]
    waves.started(tmp_path, control, run, wave, worker, "host")
    seal_wave(tmp_path, control, run, wave)
    task = waves.claim(tmp_path, control, run, wave, worker)["task"]
    _, coverage, errors = result_files(tmp_path)
    waves.submit(tmp_path, control, run, wave, worker, task["id"], drafts=[], coverage=coverage, errors=errors)
    original_write = waves._write

    def interrupted(*args):
        raise OSError("state write interrupted")

    monkeypatch.setattr(waves, "_write", interrupted)
    with pytest.raises(OSError, match="interrupted"):
        waves.claim(tmp_path, control, run, wave, worker)
    path = tmp_path / "maintenance" / f"wave-{wave}-receipt.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    monkeypatch.setattr(waves, "_write", original_write)
    result = waves.claim(tmp_path, control, run, wave, worker)
    state = waves.inspect(tmp_path, control, run, wave)
    assert result["receipt"]["path"] == str(path.resolve())
    assert state["execution_ended_at"] == receipt["execution_ended_at"]
    assert state["workers"][worker]["retired_at"] == receipt["workers"][worker]["retired_at"]


def test_stop_rejects_late_claim_callback_and_notification(tmp_path):
    control, run, wave, workers = setup_wave(tmp_path)
    waves.started(tmp_path, control, run, wave, workers[0], "host")
    seal_wave(tmp_path, control, run, wave)
    task = waves.claim(tmp_path, control, run, wave, workers[0])["task"]
    draft, coverage, errors = result_files(tmp_path)
    waves.submit(tmp_path, control, run, wave, workers[0], task["id"], drafts=[draft],
                 coverage=coverage, errors=errors)
    waves.claim(tmp_path, control, run, wave, workers[0])
    waves.notification_pending(tmp_path, control, run, wave, workers[0])
    owner.stop_owned(tmp_path, control)
    for operation in (lambda: waves.claim(tmp_path, control, run, wave, workers[0]),
                      lambda: waves.finish(tmp_path, control, run, wave),
                      lambda: waves.notification_result(tmp_path, control, run, wave, workers[0],
                                                        accepted=True, result="accepted")):
        with pytest.raises(MaintenanceStopped):
            operation()
    owner.release(tmp_path, control)
    with pytest.raises(PermissionError):
        waves.finish(tmp_path, control, run, wave)


def test_changed_fixed_submission_is_rejected(tmp_path):
    control, run, wave, workers = setup_wave(tmp_path)
    waves.started(tmp_path, control, run, wave, workers[0], "host")
    seal_wave(tmp_path, control, run, wave)
    task = waves.claim(tmp_path, control, run, wave, workers[0])["task"]
    draft, coverage, errors = result_files(tmp_path)
    waves.submit(tmp_path, control, run, wave, workers[0], task["id"], drafts=[draft],
                 coverage=coverage, errors=errors)
    waves.claim(tmp_path, control, run, wave, workers[0])
    draft.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="Fixed reference changed"):
        waves.finish(tmp_path, control, run, wave)


def test_pending_notification_is_not_overwritten_by_next_wave(tmp_path):
    control, run, wave, workers = setup_wave(tmp_path)
    waves.started(tmp_path, control, run, wave, workers[0], "host")
    seal_wave(tmp_path, control, run, wave)
    task = waves.claim(tmp_path, control, run, wave, workers[0])["task"]
    draft, coverage, errors = result_files(tmp_path)
    waves.submit(tmp_path, control, run, wave, workers[0], task["id"], drafts=[draft],
                 coverage=coverage, errors=errors)
    waves.claim(tmp_path, control, run, wave, workers[0])
    waves.notification_pending(tmp_path, control, run, wave, workers[0])
    waves.finish(tmp_path, control, run, wave)
    reference = {**waves.fixed_reference(draft), "assignment": task["id"]}
    frozen, result = tmp_path / "frozen.json", tmp_path / "publication.json"
    intent = waves.publication_intent(tmp_path, control, run, wave, drafts=[reference], frozen=frozen, result=result)
    assert intent["status"] == "intent"
    assert waves.finish(tmp_path, control, run, wave)["publication"] == intent
    assert waves.publication_intent(tmp_path, control, run, wave, drafts=[reference], frozen=frozen, result=result) == intent
    with pytest.raises(ValueError, match="cannot be changed"):
        waves.publication_intent(tmp_path, control, run, wave, drafts=[reference], frozen=frozen, result=tmp_path / "other")
    frozen.write_text(json.dumps({"batch_id": "test-batch"}), encoding="utf-8")
    frozen_ref = waves.fixed_reference(frozen)
    result.write_text(json.dumps({"batch_id": "test-batch", "frozen": frozen_ref["path"],
                                  "frozen_file_sha256": frozen_ref["file_sha256"]}), encoding="utf-8")
    committed = waves.publication_committed(tmp_path, control, run, wave)
    assert waves.publication_committed(tmp_path, control, run, wave) == committed
    with pytest.raises(RuntimeError, match="notification"):
        waves.close(tmp_path, control, run, wave)
    with pytest.raises(RuntimeError, match="notification"):
        waves.create(tmp_path, control, run, tmp_path / "source.json", [task], workers)
    waves.notification_result(tmp_path, control, run, wave, workers[0], accepted=True, result={"ok": True})
    closed = waves.close(tmp_path, control, run, wave)
    repeated = waves.finish(tmp_path, control, run, wave)
    assert repeated["already_finished"] and repeated["closed"]
    assert repeated["closure"] == closed["closure"] and repeated["publication"] == committed
    next_state = waves.create(tmp_path, control, run, tmp_path / "source.json", [task], workers)
    newer = next_state["wave_id"]
    assert newer != wave
    closure = json.loads(Path(next_state["history"][0]["path"]).read_text(encoding="utf-8"))
    assert closure["publication"]["status"] == "committed" and closure["unpublished"] == []
    with pytest.raises(PermissionError):
        waves.finish(tmp_path, control, run, wave)


def test_new_owner_archives_unfinished_wave_without_reusing_its_id(tmp_path):
    control, run, wave, workers = setup_wave(tmp_path)
    waves.started(tmp_path, control, run, wave, workers[0], "host")
    seal_wave(tmp_path, control, run, wave)
    waves.claim(tmp_path, control, run, wave, workers[0])
    owner.stop_owned(tmp_path, control)
    owner.release(tmp_path, control)
    new_control = tmp_path / "new-control"
    new_run = owner.acquire(tmp_path, "project", "new", new_control)["owner"]["run_id"]
    receipt = tmp_path / "new-source.json"
    receipt.write_text(json.dumps({"owner_run_id": new_run, "layout": {"organization": "finite-wave-v1"},
                                   "workset": {"included": ["source", "another"]}}), encoding="utf-8")
    tasks = [{"id": "new", "goal": "goal", "paths": ["source"], "write_targets": [], "outputs": ["draft"]}]
    with pytest.raises(ValueError, match="already been used"):
        waves.create(tmp_path, new_control, new_run, receipt, tasks, workers, wave_id=wave)
    state = waves.create(tmp_path, new_control, new_run, receipt, tasks, workers)
    recovery = json.loads(Path(state["history"][0]["path"]).read_text(encoding="utf-8"))
    assert recovery["run_id"] == run and recovery["tasks"][0]["status"] == "claimed"


def test_receipt_and_stage_are_fixed_before_creation(tmp_path):
    control = tmp_path / "control"
    run = owner.acquire(tmp_path, "project", "parent", control)["owner"]["run_id"]
    receipt = tmp_path / "source.json"
    receipt.write_text(json.dumps({"owner_run_id": run, "layout": {}}), encoding="utf-8")
    tasks = [{"id": "t", "goal": "goal", "paths": ["source"], "write_targets": [], "outputs": ["draft"]}]
    with pytest.raises(ValueError, match="Old maintenance organization"):
        waves.create(tmp_path, control, run, receipt, tasks, ["w"])
    receipt.write_text(json.dumps({"owner_run_id": run, "layout": {"organization": "finite-wave-v1"},
                                   "workset": {"included": ["source"]}}), encoding="utf-8")
    reference = waves.fixed_reference(receipt)
    stage = tmp_path / "stage.json"
    stage.write_text(json.dumps({"receipt": reference, "control": str(control.resolve()), "owner_run_id": run,
                                 "remaining": {"paths": ["source"]},
                                 "layout": {"organization": "finite-wave-v1"}}), encoding="utf-8")
    stage_ref = waves.fixed_reference(stage)
    with pytest.raises(ValueError, match="receipt changed"):
        waves.create(tmp_path, control, run, receipt, tasks, ["w"], receipt_sha256="0" * 64)
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        waves.create(tmp_path, control, run, receipt, tasks, ["w"], stage={**stage_ref, "file_sha256": "0" * 64})
    wrong = json.loads(stage.read_text(encoding="utf-8"))
    wrong["control"] = str(tmp_path / "wrong")
    stage.write_text(json.dumps(wrong), encoding="utf-8")
    with pytest.raises(PermissionError, match="Stage receipt"):
        waves.create(tmp_path, control, run, receipt, tasks, ["w"], stage=waves.fixed_reference(stage))
    stage.write_text(json.dumps({**wrong, "control": str(control.resolve())}), encoding="utf-8")
    with pytest.raises(PermissionError, match="current owner stage"):
        waves.create(tmp_path, control, run, receipt, tasks, ["w"], stage=waves.fixed_reference(stage))
    stage = tmp_path / "saved-stage.json"
    stage_package = {**wrong, "control": str(control.resolve()), "previous_stage": None, "index": 1}
    stage_ref = owner.save_stage(tmp_path, control, stage_package, stage)
    stage_ref = {key: stage_ref[key] for key in ("path", "file_sha256")}
    with pytest.raises(PermissionError, match="must be supplied"):
        waves.create(tmp_path, control, run, receipt, tasks, ["w"])
    with pytest.raises(ValueError, match="fixed wave scope"):
        waves.create(tmp_path, control, run, receipt, [{**tasks[0], "paths": ["another"]}], ["w"], stage=stage_ref)
    state = waves.create(tmp_path, control, run, receipt, tasks, ["w"],
                         receipt_sha256=reference["file_sha256"], stage=stage_ref)
    wave = state["wave_id"]
    waves.worker_failed(tmp_path, control, run, wave, "w", "startup failed")
    init = waves.initialization_receipt(tmp_path, control, run, wave)
    assert json.loads(Path(init["path"]).read_text(encoding="utf-8"))["stage"] == stage_ref
    receipt_ref = waves.seal(tmp_path, control, run, wave)["receipt"]
    assert json.loads(Path(receipt_ref["path"]).read_text(encoding="utf-8"))["stage"] == stage_ref
    stage.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="Fixed reference changed"):
        waves.finish(tmp_path, control, run, wave)


def test_definite_publication_failure_preserves_original_error_and_unpublished(tmp_path):
    control, run, wave, workers = setup_wave(tmp_path)
    worker = workers[0]
    waves.started(tmp_path, control, run, wave, worker, "host")
    seal_wave(tmp_path, control, run, wave)
    task = waves.claim(tmp_path, control, run, wave, worker)["task"]
    draft, coverage, errors = result_files(tmp_path)
    waves.submit(tmp_path, control, run, wave, worker, task["id"], drafts=[draft], coverage=coverage, errors=errors)
    waves.claim(tmp_path, control, run, wave, worker)
    waves.notification_pending(tmp_path, control, run, wave, worker)
    waves.notification_result(tmp_path, control, run, wave, worker, accepted=True, result="accepted")
    waves.finish(tmp_path, control, run, wave)
    reference = {**waves.fixed_reference(draft), "assignment": task["id"]}
    frozen, result = tmp_path / "frozen.json", tmp_path / "publication.json"
    waves.publication_intent(tmp_path, control, run, wave, drafts=[reference], frozen=frozen, result=result)
    with pytest.raises(ValueError, match="Confirm"):
        waves.publication_failed(tmp_path, control, run, wave, error="version conflict", publisher_ended=True, no_commit=False)
    marker = owner.begin_publication(tmp_path, control)
    with pytest.raises(RuntimeError, match="in flight"):
        waves.publication_failed(tmp_path, control, run, wave, error="version conflict", publisher_ended=True, no_commit=True)
    owner.finish_publication(tmp_path, control, marker)
    failed = waves.publication_failed(tmp_path, control, run, wave, error="version conflict", publisher_ended=True, no_commit=True)
    assert waves.publication_failed(tmp_path, control, run, wave, error="version conflict", publisher_ended=True, no_commit=True) == failed
    with pytest.raises(ValueError, match="cannot be changed"):
        waves.publication_failed(tmp_path, control, run, wave, error="different error", publisher_ended=True, no_commit=True)
    with pytest.raises(ValueError, match="definitively failed"):
        waves.publication_intent(tmp_path, control, run, wave, drafts=[reference], frozen=frozen, result=result)
    closure = waves.close(tmp_path, control, run, wave)
    assert closure["unpublished"] == [reference]
    record = json.loads(Path(closure["closure"]["path"]).read_text(encoding="utf-8"))
    assert record["publication"]["status"] == "failed" and record["publication"]["error"] == "version conflict"


def test_write_scope_includes_authorized_stable_sources_but_not_read_only_sources(tmp_path):
    control = tmp_path / "control"
    run = owner.acquire(tmp_path, "project", "parent", control)["owner"]["run_id"]
    receipt = tmp_path / "source.json"
    receipt.write_text(json.dumps({"owner_run_id": run, "layout": {"organization": "finite-wave-v1"},
                                   "semantic": [{"path": "src/A.md"}],
                                   "workset": {"included": ["src/A.md", "src/B.md"]}}), encoding="utf-8")
    base = {"goal": "goal", "write_targets": [], "outputs": ["draft"]}
    with pytest.raises(ValueError, match="fixed wave scope"):
        waves.create(tmp_path, control, run, receipt, [{**base, "id": "outside", "paths": ["src/C.md"]}], ["w"])
    with pytest.raises(ValueError, match="one task"):
        waves.create(tmp_path, control, run, receipt,
                     [{**base, "id": "a", "paths": ["src/A.md"]},
                      {**base, "id": "b", "paths": ["src\\A.md"]}], ["w"])
    state = waves.create(tmp_path, control, run, receipt,
                         [{**base, "id": "stable", "paths": ["src/B.md"], "read_paths": ["src/C.md"]},
                          {**base, "id": "feedback", "paths": [], "write_targets": ["feedback:1"]}], ["w"])
    assert state["tasks"][0]["paths"] == ["src/B.md"]
    assert state["tasks"][0]["read_paths"] == ["src/C.md"]
    assert state["tasks"][1]["paths"] == []
    waves.started(tmp_path, control, run, state["wave_id"], "w", "handle")
    seal_wave(tmp_path, control, run, state["wave_id"])
    task = waves.claim(tmp_path, control, run, state["wave_id"], "w")["task"]
    draft, coverage, errors = result_files(tmp_path)
    with pytest.raises(ValueError, match="changed after source ownership validation"):
        waves.submit(tmp_path, control, run, state["wave_id"], "w", task["id"], drafts=[draft],
                     draft_hashes=["0" * 64], coverage=coverage, errors=errors)
    draft.write_text(json.dumps({"sources": ["src/C.md"]}), encoding="utf-8")
    with pytest.raises(ValueError, match="outside its paths"):
        waves.submit(tmp_path, control, run, state["wave_id"], "w", task["id"], drafts=[draft],
                     coverage=coverage, errors=errors)
    draft.write_text(json.dumps({"sources": [], "members": [{"path": "src/C.md"}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="outside its paths"):
        waves.submit(tmp_path, control, run, state["wave_id"], "w", task["id"], drafts=[draft],
                     coverage=coverage, errors=errors)
    draft.write_text(json.dumps({"sources": [{"path": "src/B.md"}]}), encoding="utf-8")
    assert waves.submit(tmp_path, control, run, state["wave_id"], "w", task["id"], drafts=[draft],
                        coverage=coverage, errors=errors)["status"] == "submitted"
    assert (waves._path_key("src/A.md") == waves._path_key("src/a.md")) == (os.name == "nt")


@pytest.mark.parametrize("pending,accepted", [(False, False), (True, False), (True, True)])
def test_parent_recovers_notice_from_host_facts(tmp_path, pending, accepted):
    control, run, wave, workers = setup_wave(tmp_path)
    worker = workers[0]
    waves.started(tmp_path, control, run, wave, worker, "host")
    seal_wave(tmp_path, control, run, wave)
    task = waves.claim(tmp_path, control, run, wave, worker)["task"]
    _, coverage, errors = result_files(tmp_path)
    waves.submit(tmp_path, control, run, wave, worker, task["id"], drafts=[], coverage=coverage, errors=errors)
    waves.claim(tmp_path, control, run, wave, worker)
    if pending:
        waves.notification_pending(tmp_path, control, run, wave, worker)
    else:
        with pytest.raises(ValueError, match="unattempted"):
            waves.notification_recover(tmp_path, control, run, wave, accepted=True, evidence="host confirms",
                                       worker_ended=True, host_verified=True)
    with pytest.raises(ValueError, match="Confirm"):
        waves.notification_recover(tmp_path, control, run, wave, accepted=accepted, evidence="host confirms",
                                   worker_ended=True, host_verified=False)
    notice = waves.notification_recover(tmp_path, control, run, wave, accepted=accepted, evidence="host confirms",
                                       worker_ended=True, host_verified=True)
    assert notice["status"] == ("accepted" if accepted else "failed")
    assert notice["result"] == "host confirms" and notice["recovery"]["worker_ended"]
    waves.finish(tmp_path, control, run, wave)
    assert waves.close(tmp_path, control, run, wave, no_publication=True)["closed"]

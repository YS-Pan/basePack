from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock

import pytest

from basepack.memory import owner
from basepack.memory.maintenance import MaintenanceStopped


def test_concurrent_claims_keep_real_holder_and_preserve_control(tmp_path):
    def claim(i):
        return owner.acquire(tmp_path, "project", f"thread-{i}", tmp_path / f"control-{i}")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, range(2)))
    assert sum(result["acquired"] for result in results) == 1
    winner = next(result["owner"] for result in results if result["acquired"])
    public = {key: value for key, value in winner.items() if key != "control"}
    assert next(result["owner"] for result in results if not result["acquired"]) == public
    assert owner.status(tmp_path) == public
    assert Path(winner["control"]).exists()


def test_cancel_attempt_before_claim_does_not_create_control(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    memory_dir = Path("memory")
    attempt_id = "a" * 32
    control = owner.attempt_control(memory_dir, attempt_id)
    assert control == tmp_path / "memory" / "maintenance" / f"{attempt_id}.control"
    owner.check_attempt(memory_dir, attempt_id)
    assert not control.parent.exists()

    result = owner.cancel_attempt(memory_dir, attempt_id)
    assert result == {"stopped": True, "attempt_id": attempt_id, "owner": None}
    assert owner.cancel_attempt(memory_dir, attempt_id) == result
    with pytest.raises(MaintenanceStopped):
        owner.check_attempt(memory_dir, attempt_id)
    with pytest.raises(MaintenanceStopped):
        owner.acquire(memory_dir, "project", "parent", control, attempt_id=attempt_id)
    assert owner.status(memory_dir) is None
    assert not control.exists()


@pytest.mark.parametrize("attempt_id", ["../owner", "A" * 32, "a" * 31, "a" * 32 + "\n"])
def test_attempt_control_rejects_invalid_id(tmp_path, attempt_id):
    with pytest.raises(ValueError, match="32 lowercase hex"):
        owner.attempt_control(tmp_path, attempt_id)


def test_attempt_claim_rejects_wrong_control(tmp_path):
    with pytest.raises(ValueError, match="control must match"):
        owner.acquire(tmp_path, "project", "parent", tmp_path / "foreign", attempt_id="a" * 32)
    assert not (tmp_path / "maintenance").exists()


def test_cancel_attempt_after_claim_preserves_inflight_publication(tmp_path):
    attempt_id = "a" * 32
    control = owner.attempt_control(tmp_path, attempt_id)
    claimed = owner.acquire(tmp_path, "project", "parent", control, attempt_id=attempt_id)["owner"]
    assert claimed["run_id"] == attempt_id
    assert claimed["control"] == str(control)
    owner.check_attempt(tmp_path, attempt_id)
    publication = owner.begin_publication(tmp_path, control)

    result = owner.cancel_attempt(tmp_path, attempt_id)
    assert result["owner"] == {**claimed, "stopped": True, "publications": [publication]}
    assert owner.cancel_attempt(tmp_path, attempt_id) == result
    assert control.read_bytes() == b"S"
    with pytest.raises(MaintenanceStopped):
        owner.check_owned(tmp_path, control)
    with pytest.raises(RuntimeError, match="uncertain"):
        owner.release(tmp_path, control)
    owner.finish_publication(tmp_path, control, publication)
    owner.release(tmp_path, control)
    assert owner.cancel_attempt(tmp_path, attempt_id)["owner"] is None
    with pytest.raises(MaintenanceStopped):
        owner.check_attempt(tmp_path, attempt_id)


def test_attempt_cancellation_denies_admission_if_control_stop_fails(tmp_path, monkeypatch):
    from basepack.memory import waves

    attempt_id = "a" * 32
    control = owner.attempt_control(tmp_path, attempt_id)
    owner.acquire(tmp_path, "project", "parent", control, attempt_id=attempt_id)

    def fail_stop(_):
        raise TimeoutError("Control is busy")

    with monkeypatch.context() as patch:
        patch.setattr(owner, "stop", fail_stop)
        with pytest.raises(TimeoutError, match="Control is busy"):
            owner.cancel_attempt(tmp_path, attempt_id)
    assert control.read_bytes() == b""
    assert not owner.status(tmp_path)["stopped"]
    with pytest.raises(MaintenanceStopped):
        owner.check_attempt(tmp_path, attempt_id)
    with pytest.raises(MaintenanceStopped):
        owner.check_owned(tmp_path, control)
    with pytest.raises(MaintenanceStopped):
        owner.begin_publication(tmp_path, control)
    with pytest.raises(MaintenanceStopped):
        owner.save_stage(tmp_path, control, {"owner_run_id": attempt_id}, tmp_path / "stage.json")
    with pytest.raises(MaintenanceStopped):
        waves.inspect(tmp_path, control, attempt_id, "wave")
    assert owner.cancel_attempt(tmp_path, attempt_id)["owner"]["stopped"]
    owner.release(tmp_path, control)


def test_competing_attempts_cancel_only_the_requested_attempt(tmp_path):
    def claim(attempt_id):
        control = owner.attempt_control(tmp_path, attempt_id)
        return owner.acquire(tmp_path, "project", attempt_id, control, attempt_id=attempt_id)

    attempt_ids = ("a" * 32, "b" * 32)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = dict(zip(attempt_ids, pool.map(claim, attempt_ids)))
    assert sum(result["acquired"] for result in results.values()) == 1
    loser = next(attempt_id for attempt_id in attempt_ids if not results[attempt_id]["acquired"])
    live_owner = owner.status(tmp_path)
    assert results[loser]["owner"] == live_owner
    assert owner.cancel_attempt(tmp_path, loser)["owner"] is None
    with pytest.raises(MaintenanceStopped):
        claim(loser)
    assert owner.status(tmp_path) == live_owner
    assert not owner.attempt_control(tmp_path, loser).exists()
    owner.check_owned(tmp_path, owner.attempt_control(tmp_path, live_owner["run_id"]))


def test_cancel_attempt_does_not_stop_legacy_owner_using_same_path(tmp_path):
    attempt_id = "a" * 32
    control = owner.attempt_control(tmp_path, attempt_id)
    owner.acquire(tmp_path, "project", "legacy", control)
    assert owner.cancel_attempt(tmp_path, attempt_id)["owner"] is None
    assert not owner.status(tmp_path)["stopped"]
    owner.begin_publication(tmp_path, control)


def test_only_owner_stops_and_releases_after_publications_complete(tmp_path):
    control = tmp_path / "control"
    owner.acquire(tmp_path, "project", "thread", control)
    publication = owner.begin_publication(tmp_path, control)
    with pytest.raises(PermissionError):
        owner.stop_owned(tmp_path, tmp_path / "other")
    with pytest.raises(RuntimeError, match="Stop"):
        owner.release(tmp_path, control)
    owner.stop_owned(tmp_path, control)
    with pytest.raises(MaintenanceStopped):
        owner.begin_publication(tmp_path, control)
    with pytest.raises(RuntimeError, match="uncertain"):
        owner.release(tmp_path, control)
    owner.finish_publication(tmp_path, control, publication)
    owner.release(tmp_path, control)
    assert owner.status(tmp_path) is None
    with pytest.raises(FileExistsError):
        owner.acquire(tmp_path, "project", "new", control)


def test_uncertain_publication_requires_explicit_recovery(tmp_path):
    control = tmp_path / "control"
    record = owner.acquire(tmp_path, "project", "thread", control)["owner"]
    publication = owner.begin_publication(tmp_path, control)
    with pytest.raises(ValueError, match="Verify both"):
        owner.recover(tmp_path, record["run_id"], owner_ended=True, publication_resolved=False)
    with pytest.raises(ValueError, match="not the current owner"):
        owner.recover(tmp_path, "wrong", owner_ended=True, publication_resolved=True)
    assert owner.status(tmp_path)["publications"] == [publication]
    owner.recover(tmp_path, record["run_id"], owner_ended=True, publication_resolved=True)
    with pytest.raises(PermissionError):
        owner.begin_publication(tmp_path, control)
    assert owner.acquire(tmp_path, "project", "new", tmp_path / "new-control")["acquired"]
    with pytest.raises(PermissionError):
        owner.finish_publication(tmp_path, control, publication)


def test_two_processes_compete_for_project(tmp_path):
    import json
    import os
    import subprocess
    import sys

    script = """
import json, sys
from pathlib import Path
from basepack.memory.owner import acquire
root = Path(sys.argv[1])
i = sys.argv[2]
print(json.dumps(acquire(root, 'project', 'thread-' + i, root / ('control-' + i))), flush=True)
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    processes = [subprocess.Popen([sys.executable, "-c", script, str(tmp_path), str(i)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
                 for i in range(2)]
    results = []
    for process in processes:
        out, err = process.communicate(timeout=15)
        assert process.returncode == 0, err
        results.append(json.loads(out))
    assert sum(row["acquired"] for row in results) == 1
    winner = next(row["owner"] for row in results if row["acquired"])
    loser_view = next(row["owner"] for row in results if not row["acquired"])
    assert loser_view["holder"] == winner["holder"]
    assert "control" not in loser_view


def test_busy_cli_exits_before_store_or_preflight(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from basepack.memory.cli import dispatch

    owner.acquire(tmp_path, "project", "first", tmp_path / "first-control")
    config = SimpleNamespace(memory_dir=tmp_path, raw={"memory": {"project_id": "project"}})
    output = tmp_path / "busy.json"
    args = SimpleNamespace(memory_action="maintain", holder="second", control=tmp_path / "second-control",
                           output=output, attempt=None)
    result, code = dispatch(args, config)
    assert code == 0 and result == {"output": str(output)}
    import json
    report = json.loads(output.read_text(encoding="utf-8"))
    assert not report["acquired"] and report["owner"]["holder"] == "first"
    assert not (tmp_path / "second-control").exists()


def test_process_exit_after_publication_admission_keeps_lock(tmp_path):
    import os
    import subprocess
    import sys

    control = tmp_path / "control"
    record = owner.acquire(tmp_path, "project", "thread", control)["owner"]
    script = """
import os, sys
from basepack.memory.owner import begin_publication
begin_publication(sys.argv[1], sys.argv[2])
os._exit(7)
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    process = subprocess.run([sys.executable, "-c", script, str(tmp_path), str(control)], env=env, timeout=15)
    assert process.returncode == 7
    owner.stop_owned(tmp_path, control)
    with pytest.raises(RuntimeError, match="uncertain"):
        owner.release(tmp_path, control)
    assert len(owner.status(tmp_path)["publications"]) == 1
    assert not owner.acquire(tmp_path, "project", "other", tmp_path / "other")["acquired"]
    owner.recover(tmp_path, record["run_id"], owner_ended=True, publication_resolved=True)


def test_preflight_failure_releases_undispatched_owner(tmp_path):
    from types import SimpleNamespace
    from basepack.memory.cli import dispatch

    config = SimpleNamespace(memory_dir=tmp_path, raw={"memory": {"project_id": "project"}})
    args = SimpleNamespace(memory_action="maintain", holder="thread", control=tmp_path / "control", output=None,
                           mode="manual", available_subagents=None, attempt=None)
    with pytest.raises((AttributeError, KeyError)):
        dispatch(args, config)
    assert owner.status(tmp_path) is None
    assert (tmp_path / "control").read_bytes() == b"S"
    assert owner.acquire(tmp_path, "project", "other", tmp_path / "other")["acquired"]


def test_managed_preflight_can_resume_with_original_control_after_cold_start(tmp_path, monkeypatch):
    from contextlib import nullcontext
    from types import SimpleNamespace

    from basepack.memory import cli, store
    from basepack.runtime import activity
    from basepack.runtime.recovery import RuntimeStartRequired

    config = SimpleNamespace(memory_dir=tmp_path, raw={"memory": {"project_id": "project", "windows_task": True}})
    attempt = "a" * 32
    control = owner.attempt_control(tmp_path, attempt)
    args = SimpleNamespace(memory_action="maintain", holder="thread", control=control,
                           output=None, mode="automatic", available_subagents=None, attempt=attempt)
    demand = RuntimeStartRequired({"status": "runtime_start_required", "component": "memory", "error": "stopped"})
    memory = SimpleNamespace(verify_project=Mock(side_effect=[demand, None]))
    preflight = Mock(return_value={"acquired": True})
    monkeypatch.setattr(activity, "memory_operation", lambda config: nullcontext())
    monkeypatch.setattr(store, "Memory", lambda config: memory)
    monkeypatch.setattr(cli, "_maintain", preflight)

    with pytest.raises(RuntimeStartRequired) as caught:
        cli.dispatch(args, config)
    assert caught.value is demand
    assert owner.status(tmp_path) is None
    assert not control.exists()
    preflight.assert_not_called()

    result, exit_code = cli.dispatch(args, config)
    assert result == {"acquired": True} and exit_code == 0
    assert owner.status(tmp_path)["run_id"] == attempt
    assert preflight.call_args.kwargs["memory"] is memory


def test_failed_startup_keeps_uncertain_publication_and_other_owner(tmp_path):
    control = tmp_path / "control"
    claimed = owner.acquire(tmp_path, "project", "thread", control)["owner"]
    publication = owner.begin_publication(tmp_path, control)
    assert not owner.release_failed_startup(tmp_path, control, claimed["run_id"])["released"]
    assert owner.status(tmp_path)["publications"] == [publication]
    assert not owner.status(tmp_path)["stopped"]
    with pytest.raises(PermissionError):
        owner.release_failed_startup(tmp_path, tmp_path / "other", claimed["run_id"])
    with pytest.raises(PermissionError):
        owner.release_failed_startup(tmp_path, control, "wrong-run")
    assert owner.status(tmp_path)["publications"] == [publication]


def test_stop_and_release_cli_work_without_credentials_or_database(tmp_path):
    import json
    import os
    import subprocess
    import sys
    from basepack.project.config import load_project_config
    from basepack.project.init import init_project

    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine, max_concurrent_subagents=12, concurrency_source="test fixture"))
    assert not config.memory_password_file.exists()
    control = tmp_path / "control"
    owner.acquire(config.memory_dir, config.raw["memory"]["project_id"], "thread", control)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    prefix = [sys.executable, "-X", "utf8", "-m", "basepack", "--config", str(config.path), "memory"]
    for action, result in (("stop", "stopped"), ("release", "released")):
        process = subprocess.run([*prefix, action, "--control", str(control)], env=env,
                                 capture_output=True, text=True, encoding="utf-8", timeout=15)
        assert process.returncode == 0, process.stderr
        assert json.loads(process.stdout)[result]
        if action == "stop":
            assert owner.status(config.memory_dir)["stopped"]
    assert owner.status(config.memory_dir) is None
    assert not config.memory_password_file.exists()


def test_contended_owner_mutex_reports_existing_holder(tmp_path):
    import threading
    import time
    from basepack.memory.maintenance import _locked

    owner.acquire(tmp_path, "project", "first", tmp_path / "first")
    entered = threading.Event()

    def competing_claim():
        entered.set()
        return owner.acquire(tmp_path, "project", "second", tmp_path / "second")

    with ThreadPoolExecutor(max_workers=1) as pool:
        with _locked(tmp_path / "maintenance" / "owner.lock"):
            result = pool.submit(competing_claim)
            assert entered.wait(2)
            time.sleep(0.8)
        claim = result.result(timeout=5)
    assert not claim["acquired"] and claim["owner"]["holder"] == "first"


def test_windows_open_state_file_blocks_replace_and_preserves_journal(tmp_path):
    import os

    if os.name != "nt":
        pytest.skip("Windows file sharing behavior")
    control = tmp_path / "control"
    owner.acquire(tmp_path, "project", "thread", control)
    state = tmp_path / "maintenance" / "owner.json"
    with state.open("rb"):
        with pytest.raises(PermissionError) as error:
            owner.begin_publication(tmp_path, control, "publication")
        assert error.value.winerror == 5
    assert owner.status(tmp_path)["publications"] == []
    assert owner.begin_publication(tmp_path, control, "publication") == "publication"

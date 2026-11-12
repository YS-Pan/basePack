from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

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
    args = SimpleNamespace(memory_action="maintain", holder="second", control=tmp_path / "second-control", output=output)
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


def test_preflight_failure_retains_owner(tmp_path):
    from types import SimpleNamespace
    from basepack.memory.cli import dispatch

    config = SimpleNamespace(memory_dir=tmp_path, raw={"memory": {"project_id": "project"}})
    args = SimpleNamespace(memory_action="maintain", holder="thread", control=tmp_path / "control", output=None,
                           mode="manual", available_subagents=None)
    with pytest.raises((AttributeError, KeyError)):
        dispatch(args, config)
    assert owner.status(tmp_path)["holder"] == "thread"
    assert not owner.acquire(tmp_path, "project", "other", tmp_path / "other")["acquired"]


def test_stop_cli_loads_config_without_credentials_or_database(tmp_path):
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
    process = subprocess.run([sys.executable, "-X", "utf8", "-m", "basepack", "--config", str(config.path),
                              "memory", "stop", "--control", str(control)],
                             env=env, capture_output=True, text=True, encoding="utf-8", timeout=15)
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)["stopped"]
    assert owner.status(config.memory_dir)["stopped"]
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

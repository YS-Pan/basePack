import json
from pathlib import Path

import pytest

from basepack.memory import owner, waves
from basepack.memory.maintenance import MaintenanceStopped
from basepack.memory.prompts import maintenance_layout, render_prompt
from basepack.memory.stages import _read_reference, fixed_reference, load_stage, prepare_stage, stage_layout
from basepack.project.config import load_project_config
from basepack.project.init import init_project


@pytest.fixture
def stage_project(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine,
                                             max_concurrent_subagents=5, concurrency_source="test"))
    control = tmp_path / "control"
    claim = owner.acquire(config.memory_dir, config.raw["memory"]["project_id"], "parent", control)
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps({"owner_run_id": claim["owner"]["run_id"],
                                   "workset": {"included": ["a.md", "b.md", "c.md"]},
                                   "semantic": [{"path": path, "members": []} for path in ("a.md", "b.md", "c.md")],
                                   "pending_relations": [{"id": "semantic:r", "basis": []}],
                                   "feedback": [{"id": "feedback:f"}],
                                   "discovery": {"gaps": [{"path": "unknown.bin", "reason": "binary"}]},
                                   "layout": maintenance_layout(config, work_items=3, run_id=claim["owner"]["run_id"])}), encoding="utf-8")
    return config, receipt, control


def write_handoff(config, receipt, control, name, *, task=None, completed=("a.md",),
                  remaining=("b.md", "c.md"), close=True):
    """Save a synthetic host boundary after a real, local no-knowledge wave closes."""
    material = json.loads(receipt.read_text(encoding="utf-8"))
    run = material["owner_run_id"]
    stage = owner.status(config.memory_dir).get("stage")
    layout = _read_reference(stage)["layout"] if stage else material["layout"]
    coordinator = task or layout["teams"][0]["task_name"]
    worker = name + "-reader"
    source = next(iter(completed or remaining), "a.md")
    tasks = [{"id": "bounded-reading", "goal": "Resolve a bounded source without new knowledge",
              "paths": [source], "write_targets": [], "outputs": ["coverage"]}]
    state = waves.create(config.memory_dir, control, run, receipt, tasks, [worker],
                         coordinator="/root/" + coordinator, stage=stage)
    wave = state["wave_id"]
    common = (config.memory_dir, control, run, wave)
    waves.started(*common, worker, "host-" + worker)
    waves.initialization_receipt(*common)
    waves.seal(*common)
    waves.claim(*common, worker)
    coverage, errors = receipt.parent / (name + "-coverage.json"), receipt.parent / (name + "-errors.json")
    coverage.write_text('{"disposition":"no-knowledge"}', encoding="utf-8")
    errors.write_text('[]', encoding="utf-8")
    waves.submit(*common, worker, "bounded-reading", drafts=[], coverage=coverage, errors=errors)
    waves.claim(*common, worker)
    waves.notification_pending(*common, worker)
    waves.notification_result(*common, worker, accepted=True, result={"accepted": True})
    waves.finish(*common)
    state = waves.close(*common, no_publication=True) if close else waves.inspect(*common)
    executions = [_read_reference(_read_reference(ref)["receipt"]) for ref in state["history"]]
    executions.append(_read_reference(state["receipt"]))
    handles = {name: entry["handle"] for execution in executions
               for name, entry in execution["workers"].items() if entry["handle"]}
    workers = [{"task_name": coordinator, "handle": "host-" + coordinator, "status": "ended"},
               *[{"task_name": name, "handle": handle, "status": "ended"} for name, handle in handles.items()]]
    path = receipt.parent / name
    path.write_text(json.dumps({"wave_id": wave,
                                "completed": {"paths": list(completed), "relations": [], "feedback": []},
                                "remaining": {"paths": list(remaining), "relations": ["semantic:r"], "feedback": ["feedback:f"]},
                                "workers": workers, "completed_drafts": [], "publication_results": [],
                                "errors": [], "jobs": []}), encoding="utf-8")
    return path


def test_two_serial_stages_keep_original_lifecycle_and_unfinished_scope(stage_project, tmp_path):
    config, receipt, control = stage_project
    original = receipt.read_bytes()
    run_id = owner.status(config.memory_dir)["run_id"]
    first = prepare_stage(config, receipt, control, write_handoff(config, receipt, control, "first-handoff.json"),
                          tmp_path / "first-stage.json", workers_ended=True)
    assert first["worker"]["task_name"] == f"bp_mem_{run_id[:8]}_s1_coord_0"
    first_saved = load_stage(receipt, control, first["stage"]["path"])
    assert first_saved["layout"]["work_items"] == 2
    assert first_saved["layout"]["planned_subagents"] == 3
    assert first_saved["layout"]["teams"][0]["reader_task_names"] == [f"bp_mem_{run_id[:8]}_s1_read_0_{i}" for i in range(2)]
    assert first["worker"]["fork_turns"] == "none"
    assert "--stage" in first["worker"]["render_command"]
    assert first["stage"]["file_sha256"] in first["worker"]["render_command"]
    second = prepare_stage(config, receipt, control,
                           write_handoff(config, receipt, control, "second-handoff.json", task=first["worker"]["task_name"],
                                         completed=("b.md",), remaining=("c.md",)),
                           tmp_path / "second-stage.json", workers_ended=True, previous_stage=first["stage"]["path"])
    assert second["worker"]["task_name"] == f"bp_mem_{run_id[:8]}_s2_coord_0"
    assert second["remaining"] == {"paths": ["c.md"], "relations": ["semantic:r"], "feedback": ["feedback:f"]}
    assert owner.status(config.memory_dir)["run_id"] == run_id
    assert owner.status(config.memory_dir)["stage"] == second["stage"]
    assert not owner.status(config.memory_dir)["stopped"] and control.read_bytes() == b""
    assert receipt.read_bytes() == original
    stage = load_stage(receipt, control, second["stage"]["path"])
    assert stage["layout"]["work_items"] == 1
    assert stage["layout"]["planned_subagents"] == 2
    assert len(stage["layout"]["teams"][0]["reader_task_names"]) == 1
    assert stage["previous_stage"] == first["stage"]
    assert stage["receipt"] == fixed_reference(receipt)
    rendered = render_prompt(config, receipt, control, stage=second["stage"]["path"])
    assert rendered["task_name"] == second["worker"]["task_name"] and rendered["publisher"]
    assert rendered["stage_context"]["remaining"] == second["remaining"]
    # One parent stop capability still governs every saved stage and publication.
    owner.stop_owned(config.memory_dir, control)
    with pytest.raises(MaintenanceStopped):
        owner.begin_publication(config.memory_dir, control)
    owner.release(config.memory_dir, control)


def test_same_previous_stage_cannot_create_a_second_publisher(stage_project, tmp_path):
    config, receipt, control = stage_project
    handoff = write_handoff(config, receipt, control, "handoff.json")
    first = prepare_stage(config, receipt, control, handoff, tmp_path / "first.json", workers_ended=True)
    with pytest.raises(ValueError, match="not the current owner stage"):
        prepare_stage(config, receipt, control, handoff, tmp_path / "duplicate.json", workers_ended=True)
    assert owner.status(config.memory_dir)["stage"] == first["stage"]
    assert not (tmp_path / "duplicate.json").exists()


@pytest.mark.parametrize("state", ["inflight", "stopped", "other-owner"])
def test_stage_rejects_uncertain_publication_parent_stop_or_wrong_run(stage_project, tmp_path, state):
    config, receipt, control = stage_project
    handoff = write_handoff(config, receipt, control, "handoff.json")
    if state == "inflight":
        owner.begin_publication(config.memory_dir, control, "uncertain-batch")
        expected = RuntimeError
    elif state == "stopped":
        owner.stop_owned(config.memory_dir, control)
        expected = MaintenanceStopped
    else:
        owner.stop_owned(config.memory_dir, control)
        owner.release(config.memory_dir, control)
        control = tmp_path / "new-control"
        owner.acquire(config.memory_dir, config.raw["memory"]["project_id"], "new-parent", control)
        expected = PermissionError
    with pytest.raises(expected):
        prepare_stage(config, receipt, control, handoff, tmp_path / "stage.json", workers_ended=True)
    assert not (tmp_path / "stage.json").exists()


def test_stage_rejects_lost_work_and_changed_fixed_drafts(stage_project, tmp_path):
    config, receipt, control = stage_project
    handoff = write_handoff(config, receipt, control, "handoff.json", remaining=("b.md",))
    with pytest.raises(ValueError, match="exactly partition"):
        prepare_stage(config, receipt, control, handoff, tmp_path / "stage.json", workers_ended=True)
    handoff = write_handoff(config, receipt, control, "handoff.json")
    boundary = json.loads(handoff.read_text(encoding="utf-8"))
    draft = tmp_path / "draft.json"
    draft.write_text("{}", encoding="utf-8")
    boundary["completed_drafts"] = [{**fixed_reference(draft), "assignment": "a.md"}]
    handoff.write_text(json.dumps(boundary), encoding="utf-8")
    draft.write_text('{"changed":true}', encoding="utf-8")
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        prepare_stage(config, receipt, control, handoff, tmp_path / "stage.json", workers_ended=True)
    assert "stage" not in owner.status(config.memory_dir)


def test_stage_render_is_read_only_and_fixed_inputs_remain_verifiable(stage_project, tmp_path, monkeypatch):
    config, receipt, control = stage_project
    handoff = write_handoff(config, receipt, control, "handoff.json")
    result = prepare_stage(config, receipt, control, handoff, tmp_path / "stage.json", workers_ended=True)
    def forbidden(*args, **kwargs):
        pytest.fail("stage prompt consulted runtime ownership or capacity")
    monkeypatch.setattr(owner, "check_owned", forbidden)
    monkeypatch.setattr(type(config), "max_concurrent_subagents", property(forbidden))
    monkeypatch.setattr(type(config), "memory_password_file", property(forbidden))
    assert render_prompt(config, receipt, control, stage=result["stage"]["path"])["stage_context"]["index"] == 1
    handoff.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        render_prompt(config, receipt, control, stage=result["stage"]["path"])


def test_generated_stage_hash_rejects_changed_layout(stage_project, tmp_path):
    config, receipt, control = stage_project
    result = prepare_stage(config, receipt, control, write_handoff(config, receipt, control, "handoff.json"),
                           tmp_path / "stage.json", workers_ended=True)
    stage_path = Path(result["stage"]["path"])
    changed = json.loads(stage_path.read_text(encoding="utf-8"))
    changed["layout"]["teams"][0]["task_name"] = "changed-after-handoff"
    stage_path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        render_prompt(config, receipt, control, stage=stage_path, stage_sha256=result["stage"]["file_sha256"])


@pytest.mark.parametrize("kind", ["relations", "feedback"])
def test_stage_keeps_non_source_work_in_one_finite_wave_with_a_reader(stage_project, kind):
    config, receipt, control = stage_project
    handoff = write_handoff(config, receipt, control, "non-source.json", completed=("a.md", "b.md", "c.md"), remaining=())
    boundary = json.loads(handoff.read_text(encoding="utf-8"))
    completed_kind = "feedback" if kind == "relations" else "relations"
    boundary["completed"][completed_kind] = boundary["remaining"][completed_kind]
    boundary["remaining"][completed_kind] = []
    handoff.write_text(json.dumps(boundary), encoding="utf-8")
    result = prepare_stage(config, receipt, control, handoff, receipt.parent / "non-source-stage.json",
                           workers_ended=True)
    stage = load_stage(receipt, control, result["stage"]["path"])
    assert stage["remaining"]["paths"] == []
    assert len(stage["remaining"][kind]) == 1
    assert stage["layout"]["planned_subagents"] == 2
    assert len(stage["layout"]["teams"][0]["reader_task_names"]) == 1
    assert result["worker"]["publisher"]


@pytest.mark.parametrize("available", [0, 1, 2])
def test_stage_defers_without_reader_and_recovery_capacity_without_changing_saved_boundary(stage_project, available):
    config, receipt, control = stage_project
    original = receipt.read_bytes()
    first = prepare_stage(config, receipt, control, write_handoff(config, receipt, control, "first.json"),
                          receipt.parent / "first-stage.json", workers_ended=True)
    next_handoff = write_handoff(config, receipt, control, "next-handoff.json", task=first["worker"]["task_name"],
                                  completed=("b.md",), remaining=("c.md",))
    boundary = next_handoff.read_bytes()
    previous_stage = Path(first["stage"]["path"]).read_bytes()
    prior_owner = owner.status(config.memory_dir)
    target = receipt.parent / "next-stage.json"
    with pytest.raises(ValueError, match="reserved recovery seat"):
        prepare_stage(config, receipt, control, next_handoff, target, workers_ended=True,
                      previous_stage=first["stage"]["path"], available_subagents=available)
    assert not target.exists()
    assert owner.status(config.memory_dir) == prior_owner
    assert receipt.read_bytes() == original
    assert next_handoff.read_bytes() == boundary
    assert Path(first["stage"]["path"]).read_bytes() == previous_stage
    assert control.read_bytes() == b""
    resumed = prepare_stage(config, receipt, control, next_handoff, target, workers_ended=True,
                            previous_stage=first["stage"]["path"], available_subagents=3)
    stage = load_stage(receipt, control, resumed["stage"]["path"])
    assert stage["layout"]["planned_subagents"] == 2
    assert stage["layout"]["maintenance_budget"] == 2
    assert resumed["remaining"] == {"paths": ["c.md"], "relations": ["semantic:r"], "feedback": ["feedback:f"]}
    assert stage["previous_stage"] == first["stage"]
    assert stage["owner_run_id"] == owner.status(config.memory_dir)["run_id"]
    assert receipt.read_bytes() == original
    assert control.read_bytes() == b""


def test_stage_unknown_capacity_remains_a_ceiling_and_saved_identity_is_stable(stage_project):
    config, receipt, control = stage_project
    result = prepare_stage(config, receipt, control, write_handoff(config, receipt, control, "handoff.json"),
                           receipt.parent / "stage.json", workers_ended=True)
    stage = load_stage(receipt, control, result["stage"]["path"])
    assert stage["layout"]["available_subagents"] is None
    assert stage["layout"]["capacity_status"] == "organization_ceiling"
    assert stage["layout"]["planned_subagents"] == 3
    first = render_prompt(config, receipt, control, stage=result["stage"]["path"])
    again = render_prompt(config, receipt, control, stage=result["stage"]["path"])
    assert first["task_name"] == again["task_name"] == result["worker"]["task_name"]
    assert first["reader_task_names"] == again["reader_task_names"]
    assert stage["layout"]["organization"] == "finite-wave-v1"
    assert len(stage["layout"]["teams"]) == 1


def test_stage_caps_remaining_work_by_new_host_availability(stage_project):
    config, receipt, control = stage_project
    result = prepare_stage(config, receipt, control, write_handoff(config, receipt, control, "handoff.json"),
                           receipt.parent / "stage.json", workers_ended=True, available_subagents=3)
    stage = load_stage(receipt, control, result["stage"]["path"])
    assert stage["layout"]["work_items"] == 2
    assert stage["layout"]["planned_subagents"] == 2
    assert stage["layout"]["available_subagents"] == 3
    assert stage["layout"]["capacity_status"] == "verified_available"
    assert stage["remaining"]["paths"] == ["b.md", "c.md"]
    assert len(result["worker"]["reader_task_names"]) == 1


def test_stage_names_are_stable_per_stage_and_distinct_across_runs(stage_project):
    config, _, _ = stage_project
    first = maintenance_layout(config, work_items=2, run_id="12345678-first")
    saved = stage_layout(first, 1, "12345678-first")
    assert stage_layout(first, 1, "12345678-first") == saved
    second = stage_layout(first, 2, "12345678-first")
    other = stage_layout(first, 1, "abcdefgh-other")
    names = [{team["task_name"], *team["reader_task_names"]}
             for team in (saved["teams"][0], second["teams"][0], other["teams"][0])]
    assert names[0].isdisjoint(names[1]) and names[0].isdisjoint(names[2])
    assert first["teams"][0]["task_name"] == "bp_mem_12345678_coord_0"


@pytest.mark.parametrize("workers_ended,worker_status", [(False, "ended"), (True, "running")])
def test_stage_requires_actual_worker_end_confirmation(stage_project, workers_ended, worker_status):
    config, receipt, control = stage_project
    handoff = write_handoff(config, receipt, control, "handoff.json")
    boundary = json.loads(handoff.read_text(encoding="utf-8"))
    boundary["workers"][0]["status"] = worker_status
    handoff.write_text(json.dumps(boundary), encoding="utf-8")
    with pytest.raises(ValueError, match="ended"):
        prepare_stage(config, receipt, control, handoff, receipt.parent / "stage.json", workers_ended=workers_ended)
    assert "stage" not in owner.status(config.memory_dir)


def test_stage_rejects_execution_finished_before_wave_close(stage_project):
    config, receipt, control = stage_project
    handoff = write_handoff(config, receipt, control, "unclosed.json", close=False)
    before = owner.status(config.memory_dir)
    with pytest.raises(ValueError, match="Close the wave"):
        prepare_stage(config, receipt, control, handoff, receipt.parent / "stage.json", workers_ended=True)
    assert owner.status(config.memory_dir) == before
    assert not (receipt.parent / "stage.json").exists()


@pytest.mark.parametrize("wrong_handle", [False, True])
def test_stage_requires_started_reader_handles_from_every_wave(stage_project, wrong_handle):
    config, receipt, control = stage_project
    prior = write_handoff(config, receipt, control, "earlier.json")
    old_reader = json.loads(prior.read_text(encoding="utf-8"))["workers"][1]
    handoff = write_handoff(config, receipt, control, "handoff.json")
    boundary = json.loads(handoff.read_text(encoding="utf-8"))
    if wrong_handle:
        next(worker for worker in boundary["workers"] if worker["task_name"] == old_reader["task_name"])["handle"] = "different-host"
    else:
        boundary["workers"] = [worker for worker in boundary["workers"] if worker["task_name"] != old_reader["task_name"]]
    handoff.write_text(json.dumps(boundary), encoding="utf-8")
    with pytest.raises(ValueError, match="each started wave worker"):
        prepare_stage(config, receipt, control, handoff, receipt.parent / "stage.json", workers_ended=True)
    assert "stage" not in owner.status(config.memory_dir)
    assert not (receipt.parent / "stage.json").exists()

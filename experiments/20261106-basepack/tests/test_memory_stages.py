import json
from pathlib import Path

import pytest

from basepack.memory import owner
from basepack.memory.maintenance import MaintenanceStopped
from basepack.memory.prompts import maintenance_layout, pending_workers, render_prompt
from basepack.memory.stages import fixed_reference, load_stage, prepare_stage
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
                                   "semantic": [{"path": path, "members": []} for path in ("a.md", "b.md", "c.md")],
                                   "pending_relations": [{"id": "semantic:r", "basis": []}],
                                   "feedback": [{"id": "feedback:f"}],
                                   "discovery": {"gaps": [{"path": "unknown.bin", "reason": "binary"}]},
                                   "layout": maintenance_layout(config)}), encoding="utf-8")
    return config, receipt, control


def write_handoff(tmp_path, name, *, task="bp_mem_coord_0", completed=("a.md",), remaining=("b.md", "c.md")):
    path = tmp_path / name
    path.write_text(json.dumps({"completed": {"paths": list(completed), "relations": [], "feedback": []},
                                "remaining": {"paths": list(remaining), "relations": ["semantic:r"], "feedback": ["feedback:f"]},
                                "workers": [{"task_name": task, "handle": "host-handle-" + task, "status": "ended"}],
                                "completed_drafts": [], "publication_results": [], "errors": [], "jobs": []}), encoding="utf-8")
    return path


def test_two_serial_stages_keep_original_lifecycle_and_unfinished_scope(stage_project, tmp_path):
    config, receipt, control = stage_project
    original = receipt.read_bytes()
    run_id = owner.status(config.memory_dir)["run_id"]
    first = prepare_stage(config, receipt, control, write_handoff(tmp_path, "first-handoff.json"),
                          tmp_path / "first-stage.json", workers_ended=True)
    assert first["worker"]["task_name"] == f"bp_mem_{run_id[:8]}_s1_coord_0"
    assert first["worker"]["fork_turns"] == "none"
    assert "--stage" in first["worker"]["render_command"]
    assert first["stage"]["file_sha256"] in first["worker"]["render_command"]
    second = prepare_stage(config, receipt, control,
                           write_handoff(tmp_path, "second-handoff.json", task=first["worker"]["task_name"],
                                         completed=("b.md",), remaining=("c.md",)),
                           tmp_path / "second-stage.json", workers_ended=True, previous_stage=first["stage"]["path"])
    assert second["worker"]["task_name"] == f"bp_mem_{run_id[:8]}_s2_coord_0"
    assert second["remaining"] == {"paths": ["c.md"], "relations": ["semantic:r"], "feedback": ["feedback:f"]}
    assert owner.status(config.memory_dir)["run_id"] == run_id
    assert owner.status(config.memory_dir)["stage"] == second["stage"]
    assert not owner.status(config.memory_dir)["stopped"] and control.read_bytes() == b""
    assert receipt.read_bytes() == original
    stage = load_stage(receipt, control, second["stage"]["path"])
    assert stage["previous_stage"] == first["stage"]
    assert stage["receipt"] == fixed_reference(receipt)
    rendered = render_prompt(config, receipt, control, stage=second["stage"]["path"])
    assert rendered["task_name"] == second["worker"]["task_name"] and rendered["publisher"]
    assert rendered["stage_context"]["remaining"] == second["remaining"]
    with pytest.raises(ValueError, match="outside the saved layout"):
        pending_workers(stage["layout"], 1, [first["worker"]["task_name"]])
    # One parent stop capability still governs every saved stage and publication.
    owner.stop_owned(config.memory_dir, control)
    with pytest.raises(MaintenanceStopped):
        owner.begin_publication(config.memory_dir, control)
    owner.release(config.memory_dir, control)


def test_same_previous_stage_cannot_create_a_second_publisher(stage_project, tmp_path):
    config, receipt, control = stage_project
    handoff = write_handoff(tmp_path, "handoff.json")
    first = prepare_stage(config, receipt, control, handoff, tmp_path / "first.json", workers_ended=True)
    with pytest.raises(ValueError, match="not the current owner stage"):
        prepare_stage(config, receipt, control, handoff, tmp_path / "duplicate.json", workers_ended=True)
    assert owner.status(config.memory_dir)["stage"] == first["stage"]
    assert not (tmp_path / "duplicate.json").exists()


@pytest.mark.parametrize("state", ["inflight", "stopped", "other-owner"])
def test_stage_rejects_uncertain_publication_parent_stop_or_wrong_run(stage_project, tmp_path, state):
    config, receipt, control = stage_project
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
        prepare_stage(config, receipt, control, write_handoff(tmp_path, "handoff.json"),
                      tmp_path / "stage.json", workers_ended=True)
    assert not (tmp_path / "stage.json").exists()


def test_stage_rejects_lost_work_and_changed_fixed_drafts(stage_project, tmp_path):
    config, receipt, control = stage_project
    handoff = write_handoff(tmp_path, "handoff.json", remaining=("b.md",))
    with pytest.raises(ValueError, match="exactly partition"):
        prepare_stage(config, receipt, control, handoff, tmp_path / "stage.json", workers_ended=True)
    handoff = write_handoff(tmp_path, "handoff.json")
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
    handoff = write_handoff(tmp_path, "handoff.json")
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
    result = prepare_stage(config, receipt, control, write_handoff(tmp_path, "handoff.json"),
                           tmp_path / "stage.json", workers_ended=True)
    stage_path = Path(result["stage"]["path"])
    changed = json.loads(stage_path.read_text(encoding="utf-8"))
    changed["layout"]["teams"][0]["task_name"] = "changed-after-handoff"
    stage_path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        render_prompt(config, receipt, control, stage=stage_path, stage_sha256=result["stage"]["file_sha256"])

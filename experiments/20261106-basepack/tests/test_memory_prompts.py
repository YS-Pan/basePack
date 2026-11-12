import json
from copy import deepcopy
import os
from pathlib import Path
import shlex
import subprocess

import pytest

from basepack.memory.prompts import (maintenance_layout, memory_command, pending_workers,
                                     prompt_dispatch, render_prompt, retrieval_dispatch,
                                     render_retrieval_prompt)
from basepack.project.config import load_project_config
from basepack.project.init import init_project


@pytest.fixture
def prompt_project(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    return load_project_config(init_project(tmp_path / "中文 user's project", machine,
                                           max_concurrent_subagents=12,
                                           concurrency_source="test host excludes main; all descendants"))


def write_receipt(config, receipt, material, *, layout=None):
    material["layout"] = maintenance_layout(config) if layout is None else layout
    receipt.write_text(json.dumps(material), encoding="utf-8")


def test_dispatch_is_lazy_and_resolves_role_independently(prompt_project, tmp_path):
    receipt = tmp_path / "missing receipt.json"
    control = tmp_path / "missing dir" / "control"
    result = prompt_dispatch(prompt_project, receipt, control)
    assert result["role"] == "coordinator"
    assert result["tier"] == "tier2"
    assert result["model"] == prompt_project.raw["ai"]["tiers"]["tier2"]["model"]
    assert "--receipt" in result["render_command"]
    assert str(receipt) in result["render_command"]
    assert not receipt.exists() and not control.parent.exists()
    override = prompt_dispatch(prompt_project, receipt, control, role="reader", tier="tier4", paths=["one.md"])
    assert override["role"] == "reader" and override["tier"] == "tier4"
    assert "--paths" in override["render_command"] and "one.md" in override["render_command"]
    with pytest.raises(KeyError):
        prompt_dispatch(prompt_project, receipt, control, role="unexpected", tier="tier1")


@pytest.mark.parametrize("role, paths", [("reader", None), ("reader", []),
                                        ("coordinator", ["one.md"]),
                                        ("reader", ["../outside.md"]),
                                        ("reader", ["/absolute.md"])])
def test_dispatch_rejects_invalid_role_paths(prompt_project, tmp_path, role, paths):
    with pytest.raises(ValueError):
        prompt_dispatch(prompt_project, tmp_path / "receipt", tmp_path / "control", role=role, paths=paths)


def test_render_reads_only_receipt_and_templates(prompt_project, tmp_path, monkeypatch):
    from basepack.memory import store, maintenance

    def forbidden(*args, **kwargs):
        pytest.fail("prompt rendering must not access the memory store or control lock")

    monkeypatch.setattr(store, "Memory", forbidden)
    monkeypatch.setattr(maintenance, "check", forbidden)
    receipt = tmp_path / "receipt.json"
    write_receipt(prompt_project, receipt, {"semantic": [{"path": "one.md", "large": "secret-body",
                                                 "members": [{"id": "member:one", "reasons": ["changed"]}],
                                                 "uncovered_ranges": [{"start_line": 1, "end_line": 2,
                                                                       "text": "secret-body"}]}],
                                   "pending_relations": [{"id": "edge", "basis": [{"member": "member:one"}]},
                                                         {"id": "unknown", "basis": [{"member": "member:missing"}]}]})
    control = tmp_path / "new" / "control"
    coordinator = render_prompt(prompt_project, receipt, control)
    assert coordinator["role"] == "coordinator" and coordinator["tier"] == "tier2"
    assert "1 semantic sources, 2 pending relations and 0 reports" in coordinator["prompt"]
    assert "secret-body" not in coordinator["prompt"]
    assert "sole publisher" in coordinator["prompt"]
    assert "both relation endpoints" in coordinator["prompt"]
    assert "until every candidate" in coordinator["prompt"]
    reader_ai = prompt_project.resolve_ai(tier="tier1")
    assert reader_ai["model"] in coordinator["prompt"]
    assert reader_ai["reasoning_effort"] in coordinator["prompt"]
    assert "actual host spawn parameters" in coordinator["prompt"]
    assert "Execute the following command, parse its JSON output, and follow its prompt." in coordinator["prompt"]
    assert "do not launch an audit" in coordinator["prompt"].lower()
    assert "no-knowledge or duplicate disposition" in coordinator["prompt"]
    assert "<batch.json>" not in coordinator["prompt"]
    assert str(control) in coordinator["prompt"]
    assert not control.parent.exists() and not prompt_project.memory_dir.exists()
    reader = render_prompt(prompt_project, receipt, control, role="reader", paths=["one.md"])
    assert reader["tier"] == "tier1" and reader["role"] == "reader"
    assert 'one.md' in reader["prompt"]
    assert '"related_pending_relations": [{"id": "edge"' in reader["prompt"]
    assert '"unresolved_pending_relations_count": 1' in reader["prompt"]
    assert '"id": "unknown"' not in reader["prompt"]
    assert "secret-body" not in reader["prompt"]
    assert "<reading.json>" not in reader["prompt"]
    assert "<batch.json>" not in reader["prompt"]
    assert "open the original `image_path`" in reader["prompt"]
    batch = reader["prompt"].split("Batch artifact: ", 1)[1].splitlines()[0]
    assert str(prompt_project.root / "tmp" / "basepack-maintenance" / receipt.stem) in batch
    assert not Path(batch).parent.exists()
    again = render_prompt(prompt_project, receipt, control, role="reader", paths=["one.md"])
    assert batch != again["prompt"].split("Batch artifact: ", 1)[1].splitlines()[0]
    assert "do not apply" in reader["prompt"]
    assert "model" in reader and "reasoning_effort" in reader


@pytest.mark.skipif(os.name != "nt", reason="Windows path separators")
def test_reader_hints_match_windows_paths(prompt_project, tmp_path):
    receipt = tmp_path / "receipt.json"
    write_receipt(prompt_project, receipt, {"semantic": [{"path": "folder/one.md", "members": [
        {"id": "member:one", "reasons": ["changed"]}]}], "pending_relations": []})
    reader = render_prompt(prompt_project, receipt, tmp_path / "control", role="reader", paths=[r"folder\one.md"])
    assert '"sources": [{"path": "folder/one.md"' in reader["prompt"]


@pytest.mark.parametrize("current_capture", [False, True])
@pytest.mark.parametrize("project_id", ["owned-project", None])
def test_render_preserves_codex_provenance_pointers_without_opening_them(
        prompt_project, tmp_path, current_capture, project_id):
    codex = {"project_id": project_id, "capture_dir": str(tmp_path / "missing 中文 captures"),
             "attachment_dir": str(tmp_path / "missing image's directory")}
    if current_capture:
        codex["receipt"] = str(tmp_path / "missing capture receipt.json")
    receipt = tmp_path / "receipt.json"
    write_receipt(prompt_project, receipt, {"semantic": [{"path": "attachment.png", "members": []}],
                                   "pending_relations": [], "codex": codex})
    coordinator = render_prompt(prompt_project, receipt, tmp_path / "control")
    assert f"Codex provenance inputs: {json.dumps(codex, ensure_ascii=False)}" in coordinator["prompt"]
    reader = render_prompt(prompt_project, receipt, tmp_path / "control", role="reader", paths=["attachment.png"])
    hint_text = reader["prompt"].split("Bounded receipt hints: ", 1)[1].splitlines()[0]
    hints = json.loads(hint_text)
    assert hints["codex"] == codex
    assert hints["sources"] == [{"path": "attachment.png", "members": []}]
    for result in (coordinator, reader):
        assert "match both the handed-off `codex.project_id`" in result["prompt"]
        assert "An unavailable project ID leaves the origin unresolved." in result["prompt"]
    assert not prompt_project.memory_dir.exists()


def test_render_preserves_input_errors(prompt_project, tmp_path):
    receipt = tmp_path / "receipt.json"
    receipt.write_text("not JSON", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        render_prompt(prompt_project, receipt, tmp_path / "control")


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell parser")
def test_powershell_command_quotes_literal_arguments(prompt_project):
    command = memory_command(prompt_project, "prompt", "--paths", "a'b; $(danger).md")
    parser = """[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseInput([Console]::In.ReadToEnd(), [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw ($errors | Out-String) }
$ast.EndBlock.Statements[0].PipelineElements[0].CommandElements | ForEach-Object { $_.Value }
"""
    output = subprocess.check_output(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", parser],
                                     input=command, text=True, encoding="utf-8")
    assert output.splitlines() == [str(prompt_project.python), "-X", "utf8", "-m", "basepack", "--config",
                                   str(prompt_project.path), "memory", "prompt", "--paths", "a'b; $(danger).md"]


def test_posix_command_quotes_literal_arguments(prompt_project, monkeypatch):
    monkeypatch.setattr("basepack.memory.prompts.os.name", "posix")
    args = shlex.split(memory_command(prompt_project, "read", "a'b; $(danger)"))
    assert args == [str(prompt_project.python), "-X", "utf8", "-m", "basepack", "--config",
                    str(prompt_project.path), "memory", "read", "a'b; $(danger)"]


@pytest.mark.parametrize("mode", ["automatic", "manual"])
@pytest.mark.parametrize("budget", [0, 1, 2, 3, 4, 5, 6, 10, 12, 13, 20, 30, 49, 50, 51, 100])
def test_layout_boundaries_and_fixed_names(prompt_project, mode, budget):
    reserve = 1 if mode == "automatic" else 0
    prompt_project.raw["ai"]["max_concurrent_subagents"] = budget + reserve
    layout = maintenance_layout(prompt_project, mode, budget + reserve)
    if budget == 0:
        count, readers = 0, 0
    elif mode == "automatic":
        count, readers = 1, min(4, budget - 1) if budget >= 4 else 0
    elif budget < 5:
        count, readers = 1, 0
    else:
        count, readers = min(10, budget // 5), 4
    assert layout["maintenance_budget"] == budget
    assert len(layout["teams"]) == count
    assert layout["used_subagents"] == count * (1 + readers)
    assert layout["unused_subagents"] == budget - count * (1 + readers)
    for team, assigned in enumerate(layout["teams"]):
        assert assigned["task_name"] == f"bp_mem_coord_{team}"
        assert assigned["reader_task_names"] == [f"bp_mem_read_{team}{r}" for r in range(readers)]
        assert assigned["parent_task_name"] == ("bp_mem_coord_0" if team else None)
        assert assigned["publisher"] is (team == 0)
        assert assigned["coordinator_ai"] == prompt_project.resolve_ai(tier="tier2")
        assert assigned["reader_ai"] == prompt_project.resolve_ai(tier="tier1")
    assert not prompt_project.memory_dir.exists()


@pytest.mark.parametrize("configured,available,mode,budget,readers", [
    (4, 4, "automatic", 3, 0), (4, 4, "manual", 4, 0),
    (5, 5, "automatic", 4, 3), (5, 5, "manual", 5, 4),
    (12, 4, "automatic", 3, 0), (4, 12, "automatic", 3, 0),
    (12, 0, "manual", 0, 0), (0, 12, "automatic", 0, 0)])
def test_layout_caps_availability_before_reserve(prompt_project, configured, available, mode, budget, readers):
    prompt_project.raw["ai"]["max_concurrent_subagents"] = configured
    layout = maintenance_layout(prompt_project, mode, available)
    assert layout["maintenance_budget"] == budget
    assert sum(len(team["reader_task_names"]) for team in layout["teams"]) == readers
    assert layout["capacity_status"] == "verified_available"


def test_unknown_availability_is_a_ceiling_not_idle_capacity(prompt_project):
    layout = maintenance_layout(prompt_project, "automatic")
    assert layout["maintenance_budget"] == 11
    assert layout["available_subagents"] is None
    assert layout["capacity_status"] == "organization_ceiling"
    assert layout["concurrency_source"] == prompt_project.concurrency_source
    assert len(layout["teams"]) == 1


@pytest.mark.parametrize("available", [-1, True, 1.5, "2"])
def test_layout_rejects_invalid_external_capacity(prompt_project, available):
    with pytest.raises(ValueError, match="available_subagents"):
        maintenance_layout(prompt_project, available_subagents=available)


def test_pending_dispatch_shrinks_only_unstarted_without_charging_started_twice(prompt_project):
    layout = maintenance_layout(prompt_project)
    original = deepcopy(layout)
    started = ["bp_mem_coord_0", "bp_mem_read_00"]
    workers = pending_workers(layout, 3, started)
    assert [worker["task_name"] for worker in workers] == ["bp_mem_read_01", "bp_mem_read_02", "bp_mem_read_03"]
    assert all(worker["publisher"] is False for worker in workers)
    assert layout == original
    workers = pending_workers(layout, 6, [team["task_name"] for team in layout["teams"]])
    assert len(workers) == 6
    assert all(worker["role"] == "reader" for worker in workers)
    assert pending_workers(layout, 0, started) == []
    automatic = maintenance_layout(prompt_project, "automatic")
    assert len(pending_workers(automatic, 3, ["bp_mem_coord_0"])) == 2
    assert pending_workers(automatic, 1, ["bp_mem_coord_0"]) == []
    with pytest.raises(ValueError, match="outside the saved layout"):
        pending_workers(layout, 3, ["someone_elses_worker"])


def test_pending_manual_dispatch_leaves_new_partial_teams_unstarted(prompt_project):
    layout = maintenance_layout(prompt_project)
    team0 = ["bp_mem_coord_0", "bp_mem_read_00", "bp_mem_read_01", "bp_mem_read_02", "bp_mem_read_03"]
    for available in (0, 1, 2, 3, 4):
        assert pending_workers(layout, available, team0) == []
        assert pending_workers(layout, available) == []
    whole = pending_workers(layout, 5, team0)
    assert [worker["task_name"] for worker in whole] == [
        "bp_mem_coord_1", "bp_mem_read_10", "bp_mem_read_11", "bp_mem_read_12", "bp_mem_read_13"]
    partial = pending_workers(layout, 2, [*team0, "bp_mem_coord_1"])
    assert [worker["task_name"] for worker in partial] == ["bp_mem_read_10", "bp_mem_read_11"]
    assert all(not worker["publisher"] for worker in partial)
    assert len(pending_workers(maintenance_layout(prompt_project, "automatic"), 3)) == 2


def test_render_uses_saved_layout_models_names_and_permissions(prompt_project, tmp_path, monkeypatch):
    from basepack.memory import owner, store

    def forbidden(*args, **kwargs):
        pytest.fail("rendering must not read capacity, credentials or maintenance ownership")

    layout = maintenance_layout(prompt_project)
    receipt, control = tmp_path / "receipt.json", tmp_path / "missing" / "control"
    write_receipt(prompt_project, receipt, {"semantic": [], "pending_relations": []}, layout=layout)
    prompt_project.raw["ai"]["max_concurrent_subagents"] = 0
    prompt_project.raw["ai"]["tiers"]["tier2"]["model"] = "changed-after-start"
    monkeypatch.setattr(type(prompt_project), "max_concurrent_subagents", property(forbidden))
    monkeypatch.setattr(type(prompt_project), "memory_password_file", property(forbidden))
    monkeypatch.setattr(store, "Memory", forbidden)
    monkeypatch.setattr(owner, "acquire", forbidden)
    publisher = render_prompt(prompt_project, receipt, control)
    assert publisher["task_name"] == "bp_mem_coord_0" and publisher["publisher"]
    assert publisher["model"] == layout["teams"][0]["coordinator_ai"]["model"]
    assert "changed-after-start" not in publisher["prompt"]
    assert "--team" in publisher["render_command"]
    reading = render_prompt(prompt_project, receipt, control, team=1, paths=["one.md"])
    assert reading["task_name"] == "bp_mem_coord_1" and not reading["publisher"]
    assert reading["parent_task_name"] == "bp_mem_coord_0"
    assert "--team" in reading["render_command"]
    assert "do not apply, resolve feedback" in reading["prompt"]
    assert "'apply'" not in reading["prompt"]
    assert "bp_mem_read_10" in reading["prompt"] and "bp_mem_read_03" not in reading["prompt"].split("Fixed round layout:")[0]
    reader = render_prompt(prompt_project, receipt, control, role="reader", team=1, reader=3, paths=["one.md"])
    assert reader["task_name"] == "bp_mem_read_13" and not reader["publisher"]
    assert reader["parent_task_name"] == "bp_mem_coord_1"
    assert not control.parent.exists() and not prompt_project.memory_dir.exists()


def test_reading_coordinator_requires_explicit_bounded_paths(prompt_project, tmp_path):
    receipt, control = tmp_path / "receipt.json", tmp_path / "control"
    write_receipt(prompt_project, receipt, {"semantic": [
        {"path": "one.md", "members": []}, {"path": "other.md", "members": []}], "pending_relations": []})
    with pytest.raises(ValueError, match="requires at least one project-relative path"):
        render_prompt(prompt_project, receipt, control, team=1)
    with pytest.raises(ValueError, match="project-relative"):
        prompt_dispatch(prompt_project, receipt, control, team=1, paths=["../outside.md"])
    reading = render_prompt(prompt_project, receipt, control, team=1, paths=["one.md"])
    assert 'Assigned paths: ["one.md"]' in reading["prompt"]
    assert '"sources": [{"path": "one.md", "members": []}]' in reading["prompt"]
    assert "other.md" not in reading["prompt"]
    assert "--paths" in reading["render_command"]
    assert not reading["publisher"]
    publisher = render_prompt(prompt_project, receipt, control)
    assert "<project-relative-source>" in publisher["prompt"]


def test_saved_solo_and_zero_capacity_permissions(prompt_project, tmp_path):
    prompt_project.raw["ai"]["max_concurrent_subagents"] = 4
    receipt, control = tmp_path / "receipt.json", tmp_path / "control"
    write_receipt(prompt_project, receipt, {"semantic": [], "pending_relations": []})
    result = render_prompt(prompt_project, receipt, control)
    assert result["reader_task_names"] == []
    assert "personally perform the complete prepare, original reading, chunking, summaries, relations" in result["prompt"]
    assert "0 reader slots" in result["prompt"]
    with pytest.raises(IndexError):
        render_prompt(prompt_project, receipt, control, role="reader", paths=["one.md"])
    zero = maintenance_layout(prompt_project, available_subagents=0)
    assert zero["teams"] == []
    with pytest.raises(IndexError):
        prompt_dispatch(prompt_project, receipt, control, layout=zero)


def test_retrieval_dispatch_is_independent_and_lazy(prompt_project, tmp_path, monkeypatch):
    request = tmp_path / "missing request.json"
    result = retrieval_dispatch(prompt_project, request)
    assert result["task_name"] == "bp_mem_search_0"
    assert result["executor"] == "worker"
    assert result["tier"] == prompt_project.resolve_ai(purpose="retrieval")["tier"]
    assert result["capacity_status"] == "organization_ceiling"
    assert "--receipt" not in result["render_command"] and "--control" not in result["render_command"]
    other = retrieval_dispatch(prompt_project, request, slot=2, tier="tier4", available_subagents=1)
    assert other["task_name"] == "bp_mem_search_2" and other["tier"] == "tier4"
    assert not request.exists() and not prompt_project.memory_dir.exists()
    for slot in (-1, True, "1"):
        with pytest.raises(ValueError, match="slot"):
            retrieval_dispatch(prompt_project, request, slot=slot)


@pytest.mark.parametrize("available", [None, 0, 1])
def test_retrieval_render_has_complete_flow_without_store_or_ownership(prompt_project, tmp_path, monkeypatch, available):
    from basepack.memory import owner, store

    def forbidden(*args, **kwargs):
        pytest.fail("retrieval rendering must not use database, credentials or ownership")

    monkeypatch.setattr(store, "Memory", forbidden)
    monkeypatch.setattr(owner, "acquire", forbidden)
    monkeypatch.setattr(type(prompt_project), "memory_password_file", property(forbidden))
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"question": "Find C=4's rules", "scope": "docs", "content_budget": 600}), encoding="utf-8")
    result = render_retrieval_prompt(prompt_project, request, available_subagents=available)
    assert "search" in result["prompt"] and "read" in result["prompt"] and "rank" in result["prompt"]
    assert "common 0–100 relevance scale" in result["prompt"]
    assert "--budget" in result["prompt"] and "600" in result["prompt"]
    assert "--control" not in result["prompt"] and "--receipt" not in result["prompt"]
    if available == 0:
        assert result["executor"] == "main"
        assert result["task_name"] is None and result["tier"] is None
        assert result["model"] is None and result["reasoning_effort"] is None
        assert "main agent performing retrieval directly" in result["prompt"]
    else:
        assert result["executor"] == "worker" and result["task_name"] == "bp_mem_search_0"
    assert not prompt_project.memory_dir.exists()
    assert not (prompt_project.root / "tmp").exists()


@pytest.mark.parametrize("field,value", [("question", ""), ("scope", []), ("content_budget", 0),
                                          ("content_budget", -1), ("content_budget", True)])
def test_retrieval_request_boundary_errors_remain_visible(prompt_project, tmp_path, field, value):
    request = tmp_path / "request.json"
    material = {"question": "Question", "scope": "", "content_budget": 100}
    material[field] = value
    request.write_text(json.dumps(material), encoding="utf-8")
    with pytest.raises(ValueError, match=field):
        render_retrieval_prompt(prompt_project, request)

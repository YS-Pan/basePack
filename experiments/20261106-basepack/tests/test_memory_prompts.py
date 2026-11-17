import json
import os
from pathlib import Path
import shlex
import subprocess

import pytest

from basepack.memory.prompts import (maintenance_layout, memory_command,
                                     prompt_dispatch, render_prompt)
from basepack.memory import owner, waves
from basepack.memory.wave_cli import task_prompt, worker_prompt
from basepack.memory.retrieval import retrieval_dispatch, render_retrieval_prompt
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
    material.setdefault("owner_run_id", "prompt-test-run")
    material.setdefault("workset", {"included": [item["path"] for item in material["semantic"]]})
    material["layout"] = maintenance_layout(config) if layout is None else layout
    receipt.write_text(json.dumps(material), encoding="utf-8")


def render_claimed_task(config, receipt, control, paths):
    """Reach reader rendering through a registered, sealed and claimed local wave."""
    run = owner.acquire(config.memory_dir, config.raw["memory"]["project_id"], "test-parent", control)["owner"]["run_id"]
    material = json.loads(receipt.read_text(encoding="utf-8"))
    material["owner_run_id"] = run
    receipt.write_text(json.dumps(material), encoding="utf-8")
    task = {"id": "reading", "goal": "Read the bounded originals", "paths": paths,
            "write_targets": ["test-node"], "outputs": ["draft", "coverage"]}
    wave = waves.create(config.memory_dir, control, run, receipt, [task], ["reader"], coordinator="/root/coordinator")["wave_id"]
    waves.started(config.memory_dir, control, run, wave, "reader", "host-reader")
    waves.initialization_receipt(config.memory_dir, control, run, wave)
    waves.seal(config.memory_dir, control, run, wave)
    waves.claim(config.memory_dir, control, run, wave, "reader")
    return task_prompt(config, control, run, wave, "reader", "reading")


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
    override = prompt_dispatch(prompt_project, receipt, control, tier="tier4")
    assert override["role"] == "coordinator" and override["tier"] == "tier4"
    assert override["spawn_arguments"]["model"] == prompt_project.resolve_ai(tier="tier4")["model"]
    assert override["spawn_arguments"]["reasoning_effort"] == prompt_project.resolve_ai(tier="tier4")["reasoning_effort"]
    assert override["spawn_arguments"]["fork_turns"] == "none"
    with pytest.raises(ValueError, match="one coordinator"):
        prompt_dispatch(prompt_project, receipt, control, role="unexpected", tier="tier1")


@pytest.mark.parametrize("role, paths", [("reader", None), ("reader", []),
                                        ("coordinator", ["one.md"]),
                                        ("reader", ["../outside.md"]),
                                        ("reader", ["/absolute.md"])])
def test_dispatch_rejects_invalid_role_paths(prompt_project, tmp_path, role, paths):
    with pytest.raises(ValueError):
        prompt_dispatch(prompt_project, tmp_path / "receipt", tmp_path / "control", role=role, paths=paths)


def test_coordinator_is_lazy_and_claimed_task_contains_bounded_hints(prompt_project, tmp_path, monkeypatch):
    from basepack.memory import store, maintenance

    def forbidden(*args, **kwargs):
        pytest.fail("prompt rendering must not access the memory store or control lock")

    monkeypatch.setattr(store, "Memory", forbidden)
    monkeypatch.setattr(maintenance, "check", forbidden)
    monkeypatch.setattr(type(prompt_project), "memory_password_file", property(forbidden))
    receipt = tmp_path / "receipt.json"
    write_receipt(prompt_project, receipt, {"semantic": [{"path": "one.md", "large": "secret-body",
                                                 "members": [{"id": "member:one", "reasons": ["changed"],
                                                              "source_version": "fixed-v19", "locator": {"page": 3}}],
                                                 "uncovered_ranges": [{"start_line": 1, "end_line": 2,
                                                                       "text": "secret-body"}]}],
                                   "pending_relations": [{"id": "edge", "basis": [{"member": "member:one"}]},
                                                         {"id": "unknown", "basis": [{"member": "member:missing"}]}]})
    control = tmp_path / "new" / "control"
    coordinator = render_prompt(prompt_project, receipt, control)
    assert coordinator["role"] == "coordinator" and coordinator["tier"] == "tier2"
    assert "1 semantic sources, 2 pending relations, 0 reports" in coordinator["prompt"]
    assert "secret-body" not in coordinator["prompt"]
    assert "single maintenance wave coordinator and publisher" in coordinator["prompt"]
    assert "finite wave" in coordinator["prompt"]
    assert "`spawn_arguments` object" in coordinator["prompt"]
    assert "--readers" in coordinator["prompt"] and "<reader-count>" in coordinator["prompt"]
    assert "verifies this exact coordinator turn ended and is idle" in coordinator["prompt"]
    assert "do not wait, poll, dispatch more readers" in coordinator["prompt"]
    assert "no routine independent re-reading or semantic audit" in coordinator["prompt"]
    assert "<batch.json>" not in coordinator["prompt"]
    assert str(control) in coordinator["prompt"]
    assert not control.parent.exists() and not prompt_project.memory_dir.exists()
    monkeypatch.setattr(type(prompt_project), "max_concurrent_subagents", property(forbidden))
    reader = render_claimed_task(prompt_project, receipt, control, ["one.md"])
    assert 'one.md' in reader["prompt"]
    assert '"related_pending_relations": [{"id": "edge"' in reader["prompt"]
    assert '"unresolved_pending_relations_count": 1' in reader["prompt"]
    assert '"id": "unknown"' not in reader["prompt"]
    assert "secret-body" not in reader["prompt"]
    assert '"source_version": "fixed-v19"' in reader["prompt"]
    assert '"locator": {"page": 3}' in reader["prompt"]
    assert "private flags" in reader["prompt"]
    assert "exact source versions, locators, privacy" in reader["prompt"]
    assert "<reading.json>" not in reader["prompt"]
    assert "<batch.json>" not in reader["prompt"]
    assert "open and inspect the original `image_path`" in reader["prompt"]
    assert str(prompt_project.root / "tmp" / "basepack-waves") in reader["work"]
    assert not Path(reader["work"]).exists()
    assert "do not publish" in reader["prompt"]
    assert "represented, no-knowledge/duplicate, deferred refinement, or unresolved" in reader["prompt"]
    assert ("A full-file summary spans line 1 through the current EOF, including framing; a partial summary must state its `coverage_gaps`." in reader["prompt"]
            and "For a text read with an explicit `--source-version`, supply the saved `--start-line` and `--end-line`." in reader["prompt"])
    wave_id = Path(reader["work"]).parent.name
    run = owner.status(prompt_project.memory_dir)["run_id"]
    assert "Keep all submitted files' bytes fixed; a repair uses a new path and hash." in worker_prompt(
        prompt_project, control, run, wave_id, "reader")["prompt"]
    wave_path = prompt_project.memory_dir / "maintenance" / "wave.json"
    before = wave_path.read_bytes(), receipt.read_bytes()
    assert task_prompt(prompt_project, control, run, wave_id, "reader", "reading") == reader
    assert (wave_path.read_bytes(), receipt.read_bytes()) == before


@pytest.mark.skipif(os.name != "nt", reason="Windows path separators")
def test_reader_hints_match_windows_paths(prompt_project, tmp_path):
    receipt = tmp_path / "receipt.json"
    write_receipt(prompt_project, receipt, {"semantic": [{"path": "folder/one.md", "members": [
        {"id": "member:one", "reasons": ["changed"]}]}], "pending_relations": []})
    reader = render_claimed_task(prompt_project, receipt, tmp_path / "control", [r"folder\one.md"])
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
    reader = render_claimed_task(prompt_project, receipt, tmp_path / "control", ["attachment.png"])
    hint_text = reader["prompt"].split("Receipt hints: ", 1)[1].splitlines()[0]
    hints = json.loads(hint_text)
    assert hints["codex"] == codex
    assert hints["sources"] == [{"path": "attachment.png", "members": []}]
    assert "verify both project ID and `managed_attachment` against the assigned image" in coordinator["prompt"]
    assert "An unavailable project ID leaves origin unresolved." in coordinator["prompt"]
    assert "match the project ID and managed attachment against the capture receipt or retained framing" in reader["prompt"]
    assert "leave an unavailable origin unresolved" in reader["prompt"]
    assert not Path(codex["capture_dir"]).exists()
    assert not Path(codex["attachment_dir"]).exists()


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
@pytest.mark.parametrize("budget", [0, 1, 4, 5, 6, 12, 50])
@pytest.mark.parametrize("work_items", [0, 1, 3, 6, 50])
def test_layout_sizes_roster_from_work_with_capacity_as_ceiling(prompt_project, mode, budget, work_items):
    reserve = 1
    prompt_project.raw["ai"]["max_concurrent_subagents"] = budget + reserve
    layout = maintenance_layout(prompt_project, mode, budget + reserve, work_items=work_items,
                                run_id="12345678-full-run-id")
    assert layout["maintenance_budget"] == budget
    assert layout["work_items"] == work_items
    assert "used_subagents" not in layout
    planned = layout["planned_subagents"]
    readers = min(work_items, max(0, budget - 1))
    assert planned == (readers + 1 if readers else 0)
    assert layout["organization"] == "finite-wave-v1"
    assert layout["unused_subagents"] == budget - planned
    assert sum(1 + len(team["reader_task_names"]) for team in layout["teams"]) == planned
    assert bool(layout["teams"]) is bool(readers)
    assert len(layout["teams"]) <= 1
    names = []
    for team, assigned in enumerate(layout["teams"]):
        assert assigned["task_name"] == f"bp_mem_12345678_coord_{team}"
        assert len(assigned["reader_task_names"]) == readers
        assert assigned["reader_task_names"] == [f"bp_mem_12345678_read_{team}_{r}"
                                                  for r in range(len(assigned["reader_task_names"]))]
        names.extend([assigned["task_name"], *assigned["reader_task_names"]])
        assert assigned["parent_task_name"] == (layout["teams"][0]["task_name"] if team else None)
        assert assigned["publisher"] is (team == 0)
        assert assigned["coordinator_ai"] == prompt_project.resolve_ai(tier="tier2")
        assert assigned["reader_ai"] == prompt_project.resolve_ai(tier="tier1")
    assert len(names) == len(set(names))
    assert not prompt_project.memory_dir.exists()


@pytest.mark.parametrize("configured,available,mode,budget,readers", [
    (4, 4, "automatic", 3, 2), (4, 4, "manual", 3, 2),
    (5, 5, "automatic", 4, 3), (5, 5, "manual", 4, 3),
    (12, 4, "automatic", 3, 2), (4, 12, "automatic", 3, 2),
    (12, 0, "manual", 0, 0), (0, 12, "automatic", 0, 0)])
def test_layout_caps_availability_before_reserve(prompt_project, configured, available, mode, budget, readers):
    prompt_project.raw["ai"]["max_concurrent_subagents"] = configured
    layout = maintenance_layout(prompt_project, mode, available)
    assert layout["maintenance_budget"] == budget
    assert sum(len(team["reader_task_names"]) for team in layout["teams"]) == readers
    assert layout["capacity_status"] == "verified_available"


def test_unknown_availability_is_a_ceiling_not_idle_capacity(prompt_project):
    layout = maintenance_layout(prompt_project, "automatic", work_items=1)
    assert layout["maintenance_budget"] == 11
    assert layout["available_subagents"] is None
    assert layout["capacity_status"] == "organization_ceiling"
    assert layout["concurrency_source"] == prompt_project.concurrency_source
    assert len(layout["teams"]) == 1
    assert layout["planned_subagents"] == 2
    assert layout["unused_subagents"] == 9


def test_layout_run_identity_is_stable_when_saved_and_distinct_for_new_runs(prompt_project, tmp_path):
    layout = maintenance_layout(prompt_project, work_items=2, run_id="abcdefgh-first")
    assert maintenance_layout(prompt_project, work_items=2, run_id="abcdefgh-first") == layout
    other = maintenance_layout(prompt_project, work_items=2, run_id="ijklmnop-second")
    assert other["teams"][0]["task_name"] != layout["teams"][0]["task_name"]
    receipt, control = tmp_path / "receipt.json", tmp_path / "control"
    write_receipt(prompt_project, receipt, {"semantic": [], "pending_relations": []}, layout=layout)
    first = render_prompt(prompt_project, receipt, control)
    again = render_prompt(prompt_project, receipt, control)
    assert first["task_name"] == again["task_name"] == layout["teams"][0]["task_name"]
    assert first["reader_task_names"] == again["reader_task_names"] == layout["teams"][0]["reader_task_names"]
    assert maintenance_layout(prompt_project)["run_id"] != maintenance_layout(prompt_project)["run_id"]


@pytest.mark.parametrize("available", [-1, True, 1.5, "2"])
def test_layout_rejects_invalid_external_capacity(prompt_project, available):
    with pytest.raises(ValueError, match="available_subagents"):
        maintenance_layout(prompt_project, available_subagents=available)


@pytest.mark.parametrize("work_items", [-1, True, 1.5, "2"])
def test_layout_rejects_invalid_work_count(prompt_project, work_items):
    with pytest.raises(ValueError, match="work_items"):
        maintenance_layout(prompt_project, work_items=work_items)


@pytest.mark.parametrize("legacy_layout", [{}, {"organization": "teams-v0", "teams": []}])
def test_legacy_receipt_is_rejected_without_capacity_or_store_fallback(prompt_project, tmp_path, monkeypatch, legacy_layout):
    from basepack.memory import store

    receipt, control = tmp_path / "receipt.json", tmp_path / "control"
    write_receipt(prompt_project, receipt, {"semantic": [], "pending_relations": []}, layout=legacy_layout)
    monkeypatch.setattr(store, "Memory", lambda *a: pytest.fail("legacy rejection opened store"))
    monkeypatch.setattr(type(prompt_project), "max_concurrent_subagents",
                        property(lambda *a: pytest.fail("legacy receipt replanned from current capacity")))
    with pytest.raises(ValueError, match="Legacy maintenance receipt"):
        render_prompt(prompt_project, receipt, control)
    with pytest.raises(ValueError, match="Legacy maintenance receipt"):
        prompt_dispatch(prompt_project, receipt, control, layout=legacy_layout)
    assert not prompt_project.memory_dir.exists() and not control.exists()


@pytest.mark.parametrize("options", [{"role": "reader", "paths": ["one.md"]},
                                     {"team": 1}, {"reader": 1}, {"paths": ["one.md"]}])
def test_old_per_group_dispatch_has_an_explicit_wave_error(prompt_project, tmp_path, options):
    with pytest.raises(ValueError, match="readers are registered by wave create"):
        prompt_dispatch(prompt_project, tmp_path / "receipt", tmp_path / "control", **options)
    assert not prompt_project.memory_dir.exists()


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
    assert publisher["task_name"] == layout["teams"][0]["task_name"] and publisher["publisher"]
    assert publisher["model"] == layout["teams"][0]["coordinator_ai"]["model"]
    assert "changed-after-start" not in publisher["prompt"]
    assert "--team" in publisher["render_command"]
    assert publisher["spawn_arguments"]["model"] == layout["teams"][0]["coordinator_ai"]["model"]
    assert publisher["spawn_arguments"]["reasoning_effort"] == layout["teams"][0]["coordinator_ai"]["reasoning_effort"]
    assert publisher["spawn_arguments"]["task_name"] == publisher["task_name"]
    with pytest.raises(ValueError, match="one coordinator"):
        render_prompt(prompt_project, receipt, control, team=1, paths=["one.md"])
    with pytest.raises(ValueError, match="wave create"):
        render_prompt(prompt_project, receipt, control, role="reader", paths=["one.md"])
    assert not control.parent.exists() and not prompt_project.memory_dir.exists()


@pytest.mark.parametrize("available", [0, 1, 2])
def test_insufficient_capacity_never_creates_a_readerless_coordinator(prompt_project, tmp_path, available):
    receipt, control = tmp_path / "receipt.json", tmp_path / "control"
    layout = maintenance_layout(prompt_project, available_subagents=available, work_items=1)
    assert layout["teams"] == [] and layout["planned_subagents"] == 0
    write_receipt(prompt_project, receipt, {"semantic": [], "pending_relations": []}, layout=layout)
    with pytest.raises(IndexError):
        prompt_dispatch(prompt_project, receipt, control, layout=layout)
    assert not prompt_project.memory_dir.exists()


def test_one_work_item_has_one_reader_and_a_reserved_coordinator_seat(prompt_project, tmp_path):
    receipt, control = tmp_path / "receipt.json", tmp_path / "control"
    layout = maintenance_layout(prompt_project, available_subagents=3, work_items=1)
    write_receipt(prompt_project, receipt, {"semantic": [], "pending_relations": []}, layout=layout)
    result = render_prompt(prompt_project, receipt, control)
    assert len(result["reader_task_names"]) == 1
    assert layout["reserve"] == 1 and layout["planned_subagents"] == 2
    assert "reserved recovery seat" in result["prompt"]
    assert "same coordinator" in result["prompt"]
    assert "original parent" in result["prompt"]
    assert not prompt_project.memory_dir.exists()


def test_retrieval_dispatch_is_independent_and_lazy(prompt_project, tmp_path, monkeypatch):
    request = tmp_path / "missing request.json"
    result = retrieval_dispatch(prompt_project, request)
    assert result["task_name"].startswith("bp_mem_search_") and result["task_name"].endswith("_0")
    assert result["executor"] == "worker"
    assert result["tier"] == prompt_project.resolve_ai(purpose="retrieval")["tier"]
    assert result["capacity_status"] == "organization_ceiling"
    assert "--receipt" not in result["render_command"] and "--control" not in result["render_command"]
    other = retrieval_dispatch(prompt_project, request, slot=2, tier="tier4", available_subagents=1)
    assert other["task_name"].startswith("bp_mem_search_") and other["task_name"].endswith("_2") and other["tier"] == "tier4"
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
        assert result["executor"] == "worker" and result["task_name"].startswith("bp_mem_search_") and result["task_name"].endswith("_0")
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


@pytest.mark.parametrize("scope", ["", "devDoc/", "资料/中文 project/"])
def test_scope_is_a_literal_path_prefix_not_the_business_question(prompt_project, tmp_path, scope):
    request = tmp_path / "中文 request.json"
    request.write_text(json.dumps({"question": "现在的科学目标是什么？", "scope": scope, "content_budget": 200}), encoding="utf-8")
    first = render_retrieval_prompt(prompt_project, request)
    second = render_retrieval_prompt(prompt_project, request)
    assert first["scope"] == scope
    assert first["delivery_id"] == second["delivery_id"] and first["work"] == second["work"]
    assert f"Actual path-prefix filter: {json.dumps(scope, ensure_ascii=False)}" in first["prompt"]
    if scope:
        assert ("'--scope' '" + scope + "'" in first["search_command"] if os.name == "nt"
                else "--scope" in first["search_command"])
    else:
        assert "--scope" not in first["search_command"]
    assert "--knowledge-revision" in first["prompt"] and "endpoint_versions" in first["prompt"]
    assert "host file-writing tool" in first["prompt"] and "incomplete stage" in first["prompt"]
    assert not first["started"] and first["status"] == "prepared"


@pytest.mark.parametrize("scope", ["../outside", "docs/../../outside", "/absolute", "C:/absolute", "C:relative", "\\\\server\\share"])
def test_retrieval_scope_rejects_non_project_paths(prompt_project, tmp_path, scope):
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"question": "Question", "scope": scope}), encoding="utf-8")
    with pytest.raises(ValueError, match="scope.*project-relative"):
        render_retrieval_prompt(prompt_project, request)


def test_retrieval_request_defaults_and_backslash_prefix(prompt_project, tmp_path):
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"question": "Question", "scope": "中文 project\\资料\\"}), encoding="utf-8")
    result = render_retrieval_prompt(prompt_project, request)
    assert result["scope"] == "中文 project/资料/"
    assert "6000" in result["prompt"]


def test_retrieval_request_directory_reports_the_file_contract(prompt_project, tmp_path):
    with pytest.raises(ValueError, match="JSON file, got a directory"):
        render_retrieval_prompt(prompt_project, tmp_path)


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell native argument passing")
@pytest.mark.parametrize("scope", ["", "资料/中文 project/"])
def test_rendered_search_native_arguments_keep_default_and_unicode_scope(prompt_project, tmp_path, scope):
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"question": "为何改变目标？", "scope": scope}), encoding="utf-8")
    command = render_retrieval_prompt(prompt_project, request)["search_command"]
    probe = tmp_path / "argv probe.py"
    probe.write_text("import json, sys\nprint(json.dumps(sys.argv[1:], ensure_ascii=False))\n", encoding="utf-8")
    command = command.replace("'-m' 'basepack'", "'" + str(probe).replace("'", "''") + "'", 1)
    output = subprocess.check_output(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                                      "[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)\n" + command],
                                     text=True, encoding="utf-8")
    actual = json.loads(output)
    expected = ["--config", str(prompt_project.path), "memory", "search", "--text", "<terms>"]
    if scope:
        expected += ["--scope", scope]
    assert actual == expected

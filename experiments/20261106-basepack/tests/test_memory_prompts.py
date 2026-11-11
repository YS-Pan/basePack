import json
import os
from pathlib import Path
import shlex
import subprocess

import pytest

from basepack.memory.prompts import memory_command, prompt_dispatch, render_prompt
from basepack.project.config import load_project_config
from basepack.project.init import init_project


@pytest.fixture
def prompt_project(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    return load_project_config(init_project(tmp_path / "中文 user's project", machine))


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
    receipt.write_text(json.dumps({"semantic": [{"path": "one.md", "large": "secret-body",
                                                 "members": [{"id": "member:one", "reasons": ["changed"]}],
                                                 "uncovered_ranges": [{"start_line": 1, "end_line": 2,
                                                                       "text": "secret-body"}]}],
                                   "pending_relations": [{"id": "edge", "basis": [{"member": "member:one"}]},
                                                         {"id": "unknown", "basis": [{"member": "member:missing"}]}]}), encoding="utf-8")
    control = tmp_path / "new" / "control"
    coordinator = render_prompt(prompt_project, receipt, control)
    assert coordinator["role"] == "coordinator" and coordinator["tier"] == "tier2"
    assert "1 semantic sources and 2 pending relations" in coordinator["prompt"]
    assert "secret-body" not in coordinator["prompt"]
    assert "sole publisher" in coordinator["prompt"]
    assert "both relation endpoints" in coordinator["prompt"]
    assert "until every candidate" in coordinator["prompt"]
    reader_ai = prompt_project.resolve_ai(tier="tier1")
    assert reader_ai["model"] in coordinator["prompt"]
    assert reader_ai["reasoning_effort"] in coordinator["prompt"]
    assert "actual host spawn parameters" in coordinator["prompt"]
    assert "Execute the following command, parse its JSON output, and follow its prompt." in coordinator["prompt"]
    assert "published content and saved original evidence" in coordinator["prompt"]
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
    assert str(prompt_project.memory_dir / "maintenance" / "work" / receipt.stem) in batch
    assert not Path(batch).parent.exists()
    again = render_prompt(prompt_project, receipt, control, role="reader", paths=["one.md"])
    assert batch != again["prompt"].split("Batch artifact: ", 1)[1].splitlines()[0]
    assert "do not apply" in reader["prompt"]
    assert "model" in reader and "reasoning_effort" in reader


@pytest.mark.skipif(os.name != "nt", reason="Windows path separators")
def test_reader_hints_match_windows_paths(prompt_project, tmp_path):
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps({"semantic": [{"path": "folder/one.md", "members": [
        {"id": "member:one", "reasons": ["changed"]}]}], "pending_relations": []}), encoding="utf-8")
    reader = render_prompt(prompt_project, receipt, tmp_path / "control", role="reader", paths=[r"folder\one.md"])
    assert '"sources": [{"path": "folder/one.md"' in reader["prompt"]


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

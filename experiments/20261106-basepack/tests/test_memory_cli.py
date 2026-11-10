import argparse
from pathlib import Path
import subprocess

import pytest

from basepack.memory.cli import _activate, dispatch, register_commands
from basepack.project.config import load_project_config
from basepack.project.init import init_project


def test_memory_activation_preserves_business_text_and_updates_one_local_entry(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    project = tmp_path / "中文 project"
    config = load_project_config(init_project(project, machine))
    instructions = project / ".basepack/instructions.md"
    original = instructions.read_text(encoding="utf-8")
    _activate(config)
    instructions.write_text(instructions.read_text(encoding="utf-8") + "\n业务尾注：需保留。\n", encoding="utf-8")
    _activate(config)
    updated = instructions.read_text(encoding="utf-8")
    assert updated.startswith(original.rstrip())
    assert updated.endswith("\n业务尾注：需保留。\n")
    assert updated.count("<!-- basepack-memory:start -->") == 1
    assert f"$basepackConfig = '{config.path}'" in updated
    assert "--config $basepackConfig memory brief" in updated
    assert "[记忆流程](<" in updated
    assert "memory.search_mode" in updated
    assert "`hybrid --literal`" in updated
    assert "`vector --literal` 明确拒绝" in updated
    assert f"{config.memory_dir.as_posix()}/serve.ps1" in updated
    assert "logs/surreal.stderr.log" in updated


@pytest.mark.parametrize("markers", ["<!-- basepack-memory:start -->", "<!-- basepack-memory:end -->",
                                    "<!-- basepack-memory:end -->\n<!-- basepack-memory:start -->",
                                    "<!-- basepack-memory:start -->\n<!-- basepack-memory:start -->\n<!-- basepack-memory:end -->",
                                    "<!-- basepack-memory:start -->\n<!-- basepack-memory:end -->\n<!-- basepack-memory:end -->"])
def test_broken_generated_boundary_fails_before_overwriting_instructions(tmp_path, markers):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    project = tmp_path / "project"
    config = load_project_config(init_project(project, machine))
    instructions = project / ".basepack/instructions.md"
    text = "用户正文\n" + markers + "\n用户仍需的尾注\n"
    instructions.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        _activate(config)
    assert instructions.read_text(encoding="utf-8") == text


def _search_args(*options):
    parser = argparse.ArgumentParser()
    register_commands(parser.add_subparsers(dest="command"))
    return parser.parse_args(["memory", "search", "--text", "项目数据库", *options])


@pytest.mark.parametrize("configured, explicit, expected", [
    ("hybrid", None, "hybrid"), ("vector", None, "vector"),
    ("hybrid", "vector", "vector"), ("vector", "hybrid", "hybrid"),
    ("text", "vector", "vector"), (None, "hybrid", "hybrid"), ("typo", "hybrid", "hybrid"),
])
def test_search_uses_project_mode_and_explicit_override(tmp_path, monkeypatch, configured, explicit, expected):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine))
    if configured is None:
        del config.raw["memory"]["search_mode"]
    else:
        config.raw["memory"]["search_mode"] = configured

    class Search:
        def __init__(self, config):
            pass

        def hybrid_search(self, *args, **kwargs):
            return "hybrid"

        def vector_search(self, *args, **kwargs):
            return "vector"

    monkeypatch.setattr("basepack.memory.store.Memory", Search)
    options = ["--mode", explicit] if explicit else []
    assert dispatch(_search_args(*options), config) == (expected, 0)


@pytest.mark.parametrize("configured, error", [(None, KeyError), ("typo", ValueError), ("text", ValueError)])
def test_default_search_requires_a_valid_explicit_project_setting(tmp_path, configured, error):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine))
    if configured is None:
        del config.raw["memory"]["search_mode"]
    else:
        config.raw["memory"]["search_mode"] = configured
    with pytest.raises(error, match="search_mode"):
        dispatch(_search_args(), config)


def test_text_search_mode_is_not_a_cli_option():
    with pytest.raises(SystemExit) as error:
        _search_args("--mode", "text")
    assert error.value.code == 2


@pytest.mark.parametrize("explicit", [False, True])
def test_vector_search_rejects_literal_before_retrieving(tmp_path, monkeypatch, explicit):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine))
    monkeypatch.setattr("basepack.memory.store.Memory.vector_search",
                        lambda *args, **kwargs: pytest.fail("vector search accepted --literal"))
    options = ["--mode", "vector"] if explicit else []
    with pytest.raises(ValueError, match="--literal requires --mode hybrid"):
        dispatch(_search_args("--literal", *options), config)


def test_hybrid_search_passes_literal_to_lexical_retrieval(tmp_path, monkeypatch):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine))
    config.raw["memory"]["search_mode"] = "hybrid"
    calls = []

    def hybrid(self, text, **kwargs):
        calls.append((text, kwargs))
        return "matches"

    monkeypatch.setattr("basepack.memory.store.Memory.hybrid_search", hybrid)
    assert dispatch(_search_args("--literal"), config) == ("matches", 0)
    assert calls == [("项目数据库", {"scope": "", "limit": 12, "timeout": 600,
                                  "literal": True})]


def _activation_bootstrap(config):
    text = (config.root / ".basepack/instructions.md").read_text(encoding="utf-8")
    section = text.split("<!-- basepack-memory:start -->", 1)[1].split("<!-- basepack-memory:end -->", 1)[0]
    command = section.split("```powershell\n", 1)[1].split("\n```", 1)[0]
    return command.split("& $basepackPython -X utf8 -m basepack --config $basepackConfig memory brief", 1)[0]


def test_generated_bootstrap_loads_config_in_fresh_shell_from_other_cwd(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    project = tmp_path / "中文 user's project-🚀"
    config = load_project_config(init_project(project, machine, ".basepack/deep/config.toml"))
    _activate(config)
    bootstrap = _activation_bootstrap(config)
    assert "password" not in bootstrap.lower()
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                             bootstrap + "Write-Output $basepackConfig"],
                            cwd=tmp_path.parent, capture_output=True, text=True, encoding="utf-8", timeout=20)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(config.path)


def test_maintain_defaults_to_project_scope_and_passes_control(tmp_path, monkeypatch):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine))
    config.raw["memory"]["source_scope"] = ["docs"]
    calls = []
    monkeypatch.setattr("basepack.memory.store.Memory.maintain",
                        lambda self, scope, **kwargs: calls.append((scope, kwargs)) or {"needs_semantic": 0})
    parser = argparse.ArgumentParser()
    register_commands(parser.add_subparsers(dest="command"))
    args = parser.parse_args(["memory", "maintain", "--control", "task.control"])
    result, status = dispatch(args, config)
    assert status == 0 and result["needs_semantic"] == 0
    assert result["codex"]["status"] == "binding_unavailable"
    assert calls == [(["docs"], {"control": "task.control", "timeout": 600})]


def test_codex_registry_is_used_for_maintenance_scope(tmp_path, monkeypatch):
    import json
    from basepack.memory.cli import _collect_codex
    from basepack.memory import codex, codex_binding
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine))
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"project_id": "host-project", "registry_complete": True,
                                    "other_project_roots": []}), encoding="utf-8")
    source = config.memory_dir / "codex" / "thread.txt"
    class Client:
        def __init__(self, executable): pass
        def close(self): pass
    monkeypatch.setattr(codex, "AppServer", Client)
    monkeypatch.setattr(codex, "list_threads", lambda client, control: [{"id": "thread"}])
    monkeypatch.setattr(codex_binding, "discover_binding", lambda *args: {"gaps": []})
    monkeypatch.setattr(codex_binding, "classify_threads", lambda *args: {
        "matched": [{"id": "thread"}],
        "excluded": [{"thread": {"id": "other", "preview": "other project private text"}, "reason": "outside"}],
        "unresolved": [], "gaps": []})
    seen = []
    def collect(*args, **kwargs):
        seen.append(kwargs['project_binding'])
        return {"paths": [str(source)], "gaps": [], "threads": []}
    monkeypatch.setattr(codex, "collect_codex", collect)
    result = _collect_codex(config, registry, control="task.control")
    assert result["paths"] == [".basepack/memory/codex/thread.txt"]
    assert result["discovered"] == 1
    assert seen == [{"gaps": []}]
    assert Path(result["receipt"]).is_file()
    assert "other project private text" not in Path(result["receipt"]).read_text(encoding="utf-8")

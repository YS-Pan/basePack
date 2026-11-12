import argparse
import json
from pathlib import Path
import subprocess

import pytest

from basepack.memory.cli import _activate, dispatch, register_commands
from basepack.project.config import load_project_config
from basepack.project.init import init_project


def _provision_password(config):
    config.memory_password_file.parent.mkdir(parents=True, exist_ok=True)
    config.memory_password_file.write_text("memory-cli-test-credential", encoding="utf-8")


def test_memory_activation_preserves_business_text_and_updates_one_local_entry(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    project = tmp_path / "中文 project"
    config = load_project_config(init_project(project, machine, max_concurrent_subagents=12, concurrency_source="test fixture"))
    instructions = project / ".basepack/instructions.md"
    original = instructions.read_text(encoding="utf-8").split("<!-- basepack-memory:start -->", 1)[0]
    _activate(config)
    instructions.write_text(instructions.read_text(encoding="utf-8") + "\n业务尾注：需保留。\n", encoding="utf-8")
    _activate(config)
    updated = instructions.read_text(encoding="utf-8")
    assert updated.startswith(original)
    assert updated.endswith("\n业务尾注：需保留。\n")
    assert updated.count("<!-- basepack-memory:start -->") == 1
    assert f"$basepackConfig = '{config.path}'" in updated
    assert "--config $basepackConfig memory brief" in updated
    assert "[检索流程](<" in updated
    assert "memory.search_mode" in updated
    assert "`hybrid --literal`" in updated
    assert "`vector --literal` 明确拒绝" in updated
    assert f"{config.memory_dir.as_posix()}/serve.ps1" in updated
    assert "logs/surreal.stderr.log" in updated
    startup = updated.split("<!-- basepack-memory:start -->", 1)[1].split("## 自动维护", 1)[0]
    bootstrap = startup.split("```powershell\n", 1)[1].split("\n```", 1)[0]
    assert "memory brief" not in bootstrap
    assert startup.count("--config $basepackConfig memory brief") == 1
    assert "新进程只重新初始化" in startup


@pytest.mark.parametrize("markers", ["<!-- basepack-memory:start -->", "<!-- basepack-memory:end -->",
                                    "<!-- basepack-memory:end -->\n<!-- basepack-memory:start -->",
                                    "<!-- basepack-memory:start -->\n<!-- basepack-memory:start -->\n<!-- basepack-memory:end -->",
                                    "<!-- basepack-memory:start -->\n<!-- basepack-memory:end -->\n<!-- basepack-memory:end -->"])
def test_broken_generated_boundary_fails_before_overwriting_instructions(tmp_path, markers):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    project = tmp_path / "project"
    config = load_project_config(init_project(project, machine, max_concurrent_subagents=12, concurrency_source="test fixture"))
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
    config = load_project_config(init_project(tmp_path / "project", machine, max_concurrent_subagents=12, concurrency_source="test fixture"))
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
    config = load_project_config(init_project(tmp_path / "project", machine, max_concurrent_subagents=12, concurrency_source="test fixture"))
    _provision_password(config)
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
    config = load_project_config(init_project(tmp_path / "project", machine, max_concurrent_subagents=12, concurrency_source="test fixture"))
    _provision_password(config)
    monkeypatch.setattr("basepack.memory.store.Memory.vector_search",
                        lambda *args, **kwargs: pytest.fail("vector search accepted --literal"))
    options = ["--mode", "vector"] if explicit else []
    with pytest.raises(ValueError, match="--literal requires --mode hybrid"):
        dispatch(_search_args("--literal", *options), config)


def test_hybrid_search_passes_literal_to_lexical_retrieval(tmp_path, monkeypatch):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine, max_concurrent_subagents=12, concurrency_source="test fixture"))
    _provision_password(config)
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
    config = load_project_config(init_project(project, machine, ".basepack/deep/config.toml", max_concurrent_subagents=12, concurrency_source="test fixture"))
    _activate(config)
    bootstrap = _activation_bootstrap(config)
    assert "password" not in bootstrap.lower()
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                             bootstrap + "\nWrite-Output $basepackConfig"],
                            cwd=tmp_path.parent, capture_output=True, text=True, encoding="utf-8", timeout=20)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(config.path)


def test_maintain_defaults_to_project_scope_and_passes_control(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("basepack.memory.discovery._git_repository", lambda root: False)
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine, max_concurrent_subagents=12, concurrency_source="test fixture"))
    _provision_password(config)
    config.raw["memory"]["source_scope"] = ["docs"]
    (config.root / "docs").mkdir()
    (config.root / "docs/new.md").write_text("New source", encoding="utf-8")
    calls = []
    receipt = config.memory_dir / "maintenance/receipt.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text('{"semantic": [], "pending_relations": []}', encoding="utf-8")
    monkeypatch.setattr("basepack.memory.store.Memory.maintain",
                        lambda self, scope, **kwargs: calls.append((scope, kwargs)) or
                        {"needs_semantic": 0, "receipt": str(receipt)})
    parser = argparse.ArgumentParser()
    register_commands(parser.add_subparsers(dest="command"))
    args = parser.parse_args(["memory", "maintain", "--holder", "thread", "--control", "task.control"])
    result, status = dispatch(args, config)
    assert status == 0 and result["needs_semantic"] == 0
    assert result["codex"]["status"] == "binding_unavailable"
    control = str(Path("task.control").resolve())
    assert calls == [(["docs/new.md"], {"control": control, "timeout": 600})]
    assert result["control"] == control
    assert result["discovery"] == {"mode": "configured", "sources": 1, "gaps": []}
    assert "worker" not in result


def _memory_args(*options):
    parser = argparse.ArgumentParser()
    register_commands(parser.add_subparsers(dest="command"))
    return parser.parse_args(["memory", *options])


def test_retrieve_has_useful_defaults_stable_reuse_and_no_implied_host_execution(tmp_path, monkeypatch):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "中文 project", machine,
                                              max_concurrent_subagents=12, concurrency_source="test fixture"))
    monkeypatch.setattr("basepack.memory.store.Memory", lambda *a: pytest.fail("retrieve opened the store"))
    empty, status = dispatch(_memory_args("retrieve"), config)
    assert status == 0 and empty["status"] == "needs_input" and empty["required_input"] == "question"
    assert not (config.root / "tmp").exists()
    result, status = dispatch(_memory_args("retrieve", "--question", "过去要求为何改变？"), config)
    assert status == 0 and result["status"] == "prepared" and not result["started"]
    assert result["scope"] == "" and result["content_budget"] == 6000
    request = json.loads(Path(result["request"]).read_text(encoding="utf-8"))
    assert request["question"] == "过去要求为何改变？" and request["scope"] == ""
    assert request["delivery_id"] == result["delivery_id"]
    assert result["executor"] == "worker" and result["tier"] == config.resolve_ai(purpose="retrieval")["tier"]
    assert not Path(result["delivery_receipt"]).exists()
    again, _ = dispatch(_memory_args("retrieve", "--request", result["request"], "--available-subagents", "0"), config)
    assert again["delivery_id"] == result["delivery_id"] and again["delivery_receipt"] == result["delivery_receipt"]
    assert again["executor"] == "main" and again["model"] is None and not again["started"]
    assert not config.memory_dir.exists()


def test_observed_version_cli_and_final_delivery_pass_exact_identity(tmp_path, monkeypatch):
    from types import SimpleNamespace

    calls = []
    memory = SimpleNamespace(**{name: (lambda *args, _name=name, **kwargs:
                                      calls.append((_name, args, kwargs)) or {"ok": True})
                               for name in ("knowledge", "history", "read", "neighbors", "access_hints", "record_delivery")})
    monkeypatch.setattr("basepack.memory.store.Memory", lambda config: memory)
    actions = [("knowledge", "member:m", "--knowledge-revision", "old"), ("history", "member:m"),
               ("read", "member:m", "--knowledge-revision", "old"),
               ("neighbors", "node:n", "--knowledge-revision", "node-old", "--include-stale")]
    for options in actions:
        assert dispatch(_memory_args(*options), None) == ({"ok": True}, 0)
    manifest = [{"id": "member:m", "knowledge_revision": "old"}]
    receipt = tmp_path / "delivered 中文.json"
    receipt.write_text(json.dumps({"delivery_id": "stable-id", "items": manifest, "context": {"task": "检索"}}), encoding="utf-8")
    dispatch(_memory_args("delivery", "--input", str(receipt)), None)
    hints = tmp_path / "hints.json"
    hints.write_text(json.dumps(manifest), encoding="utf-8")
    dispatch(_memory_args("access-hints", "--input", str(hints)), None)
    assert calls == [("knowledge", ("member:m",), {"knowledge_revision": "old"}),
                     ("history", ("member:m",), {}),
                     ("read", ("member:m",), {"knowledge_revision": "old", "source_version": None,
                                               "start_line": None, "end_line": None, "locator": None}),
                     ("neighbors", ("node:n",), {"knowledge_revision": "node-old", "include_stale": True}),
                     ("record_delivery", ("stable-id", manifest), {"context": {"task": "检索"}}),
                     ("access_hints", (manifest,), {})]


def test_rank_directory_input_reports_the_file_contract(tmp_path):
    with pytest.raises(ValueError, match="JSON file, got a directory"):
        dispatch(_memory_args("rank", "--input", str(tmp_path)), None)


@pytest.mark.parametrize("mode,available,expected_teams,expected_name", [
    ("automatic", 0, 0, None), ("automatic", 4, 1, "bp_mem_coord_0"),
    ("automatic", 12, 1, "bp_mem_coord_0"), ("manual", 12, 2, "bp_mem_coord_0"),
])
def test_maintain_saves_layout_and_respects_zero_capacity(tmp_path, monkeypatch, mode, available,
                                                       expected_teams, expected_name):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine,
                                              max_concurrent_subagents=12, concurrency_source="test fixture"))
    _provision_password(config)
    receipt = config.memory_dir / "maintenance/receipt.json"
    receipt.parent.mkdir()
    receipt.write_text('{"semantic": [], "pending_relations": []}', encoding="utf-8")
    monkeypatch.setattr("basepack.memory.cli._collect_codex", lambda *a, **kw:
                        {"project_id": None, "paths": [], "status": "binding_unavailable"})
    monkeypatch.setattr("basepack.memory.discovery.discover_sources", lambda *a:
                        {"mode": "configured", "paths": [], "gaps": []})
    monkeypatch.setattr("basepack.memory.store.Memory.maintain", lambda *a, **kw:
                        {"needs_semantic": True, "receipt": str(receipt)})
    result, status = dispatch(_memory_args("maintain", "--holder", "thread", "--control",
                                          str(receipt.with_suffix(".control")), "--mode", mode,
                                          "--available-subagents", str(available)), config)
    assert status == 0
    saved = json.loads(receipt.read_text(encoding="utf-8"))["layout"]
    assert saved == result["layout"]
    assert saved["capacity_status"] == "verified_available"
    assert len(saved["teams"]) == expected_teams
    if expected_name:
        assert result["worker"]["task_name"] == expected_name
        assert f"'--team' '0'" in result["worker"]["render_command"]
    else:
        assert "worker" not in result
        assert result["needs_semantic"] and result["dispatch_blocked"]


@pytest.mark.parametrize("available,executor", [(0, "main"), (1, "worker")])
def test_independent_retrieval_cli_and_pending_layout_never_open_store(tmp_path, monkeypatch,
                                                                    available, executor):
    from basepack.memory.prompts import maintenance_layout
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine,
                                              max_concurrent_subagents=12, concurrency_source="test fixture"))
    request = tmp_path / "question.json"
    request.write_text(json.dumps({"question": "如何维护并发上限？", "scope": "docs", "content_budget": 3000}),
                       encoding="utf-8")
    monkeypatch.setattr("basepack.memory.store.Memory", lambda *a:
                        pytest.fail("independent dispatch opened the store"))
    for action in ("retrieval-dispatch", "retrieval-prompt"):
        result, status = dispatch(_memory_args(action, "--request", str(request), "--slot", "1",
                                              "--available-subagents", str(available)), config)
        assert status == 0 and result["executor"] == executor
        assert result["task_name"] == ("bp_mem_search_1" if available else None)
        if action == "retrieval-prompt":
            assert result["prompt"]
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps({"layout": maintenance_layout(config, mode="manual")}), encoding="utf-8")
    pending, status = dispatch(_memory_args("pending-dispatch", "--receipt", str(receipt),
                                           "--available-subagents", "2", "--started-task-names",
                                           "bp_mem_coord_0"), config)
    assert status == 0
    assert [w["task_name"] for w in pending["workers"]] == ["bp_mem_read_00", "bp_mem_read_01"]
    assert not config.memory_dir.exists()
    assert not config.memory_password_file.exists()


def test_prompt_cli_never_constructs_memory_or_creates_state(tmp_path, monkeypatch):
    import json

    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine, max_concurrent_subagents=12, concurrency_source="test fixture"))
    receipt = tmp_path / "receipt.json"
    from basepack.memory.prompts import maintenance_layout
    receipt.write_text(json.dumps({"semantic": [], "pending_relations": [],
                                   "layout": maintenance_layout(config)}), encoding="utf-8")
    control = config.memory_dir / "new control" / "task.control"
    monkeypatch.setattr("basepack.memory.store.Memory",
                        lambda *args: pytest.fail("rendering opened the memory store"))
    result, status = dispatch(_memory_args("prompt", "--receipt", str(receipt),
                                          "--control", str(control)), config)
    assert status == 0 and result["tier"] == "tier2"
    assert result["role"] == "coordinator" and result["prompt"]
    assert not config.memory_dir.exists()
    assert not config.memory_password_file.exists()
    with pytest.raises(SystemExit):
        _memory_args("prompt", "--receipt", str(receipt), "--control", str(control),
                     "--output", str(config.memory_dir / "prompt.json"))
    assert not config.memory_dir.exists()


def test_maintain_discovers_git_project_and_emits_complete_worker_command(tmp_path, monkeypatch):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine, max_concurrent_subagents=12, concurrency_source="test fixture"))
    _provision_password(config)
    subprocess.run(["git", "init", "-q"], cwd=config.root, check=True)
    (config.root / "outside-current-task.md").write_text("Project wide", encoding="utf-8")
    (config.root / "unsupported.bin").write_bytes(b"binary\0content")
    calls = []
    receipt = str(config.memory_dir / "maintenance/receipt.json")
    Path(receipt).parent.mkdir(parents=True, exist_ok=True)
    Path(receipt).write_text('{"semantic": [], "pending_relations": []}', encoding="utf-8")
    monkeypatch.setattr("basepack.memory.store.Memory.maintain", lambda self, scope, **kwargs:
                        calls.append((scope, kwargs)) or {"needs_semantic": True, "receipt": receipt})
    result, status = dispatch(_memory_args("maintain", "--holder", "thread", "--control", str(config.memory_dir / "maintenance" / "task.control")), config)
    assert status == 0
    assert "outside-current-task.md" in calls[0][0]
    assert all(not path.startswith(".basepack/") for path in calls[0][0])
    assert result["discovery"]["mode"] == "git"
    assert result["discovery"]["gaps"] == [{"path": "unsupported.bin", "reason": "binary"}]
    assert result["worker"]["role"] == "coordinator"
    assert result["worker"]["tier"] == "tier2"
    assert result["worker"]["model"] == config.resolve_ai(tier="tier2")["model"]
    assert result["worker"]["reasoning_effort"] == config.resolve_ai(tier="tier2")["reasoning_effort"]
    assert "prompt" not in result["worker"]
    control = Path(result["control"])
    assert control.is_absolute() and control.parent == config.memory_dir / "maintenance"
    assert str(control) in result["worker"]["render_command"]
    assert receipt in result["worker"]["render_command"]
    assert calls[0][1] == {"control": str(control), "timeout": 600}
    material = json.loads(Path(receipt).read_text(encoding="utf-8"))
    assert material["codex"] == {"project_id": result["codex"]["project_id"],
                                  "capture_dir": str(config.memory_dir / "codex"),
                                  "attachment_dir": str(config.memory_dir / "codex-attachments")}
    assert material["layout"] == result["layout"]
    assert result["worker"]["task_name"] == "bp_mem_coord_0"
    assert len(material["layout"]["teams"]) == 2
    assert material["layout"]["unused_subagents"] == 2


def test_maintain_receipt_keeps_current_and_retained_codex_provenance(tmp_path, monkeypatch):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine, max_concurrent_subagents=12, concurrency_source="test fixture"))
    _provision_password(config)
    receipt = config.memory_dir / "maintenance" / "semantic.json"
    receipt.parent.mkdir()
    receipt.write_text('{"semantic": [], "pending_relations": []}', encoding="utf-8")
    capture_receipt = receipt.with_name('capture.json')
    monkeypatch.setattr("basepack.memory.cli._collect_codex", lambda *args, **kwargs:
                        {"project_id": "owned", "status": "captured", "paths": [],
                         "receipt": str(capture_receipt)})
    monkeypatch.setattr("basepack.memory.discovery.retained_codex_paths", lambda *args:
                        {"paths": [".basepack/memory/codex-attachments/retained.png"], "gaps": []})
    monkeypatch.setattr("basepack.memory.store.Memory.maintain", lambda *args, **kwargs:
                        {"needs_semantic": True, "receipt": str(receipt)})
    result, status = dispatch(_memory_args("maintain", "--holder", "thread", "--control", str(config.memory_dir / "maintenance" / "task.control"), "--scope", "no-new-discovery"), config)
    assert status == 0
    material = json.loads(receipt.read_text(encoding="utf-8"))
    assert material["codex"] == {"project_id": "owned", "receipt": str(capture_receipt),
                                  "capture_dir": str(config.memory_dir / "codex"),
                                  "attachment_dir": str(config.memory_dir / "codex-attachments")}
    from basepack.memory.prompts import render_prompt
    rendered = render_prompt(config, result["receipt"], result["control"], role="reader",
                             paths=[".basepack/memory/codex-attachments/retained.png"])
    hints = json.loads(rendered["prompt"].split('Bounded receipt hints: ', 1)[1].splitlines()[0])
    assert hints['codex'] == material['codex']


def test_maintain_keeps_owned_retained_captures_when_collection_is_unavailable(tmp_path, monkeypatch):
    import json

    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine, max_concurrent_subagents=12, concurrency_source="test fixture"))
    _provision_password(config)
    config.raw["memory"]["codex"]["project_id"] = "owned-project"
    capture = config.memory_dir / "codex" / "old-thread.txt"
    capture.parent.mkdir()
    body = "已保留且未登记的旧聊天。".encode("utf-8")
    header = {"project_id": "owned-project", "thread_id": "old-thread", "byte_length": len(body),
              "managed_attachment": "codex-attachments/old.png"}
    capture.write_bytes(json.dumps(header).encode() + b"\n" + body + b"\n")
    attachment = config.memory_dir / "codex-attachments" / "old.png"
    attachment.parent.mkdir()
    attachment.write_bytes(b"image")
    calls = []
    receipt = config.memory_dir / "maintenance/receipt.json"
    receipt.parent.mkdir()
    receipt.write_text('{"semantic": [], "pending_relations": []}', encoding="utf-8")
    monkeypatch.setattr("basepack.memory.store.Memory.maintain", lambda self, scope, **kwargs:
                        calls.append(scope) or {"needs_semantic": False, "receipt": str(receipt)})
    result, _ = dispatch(_memory_args("maintain", "--holder", "thread", "--control", str(config.memory_dir / "maintenance" / "task.control"), "--scope", "no-new-discovery"), config)
    assert result["codex"]["status"] == "binding_unavailable"
    assert result["codex"]["retained_sources"] == 2
    assert result["codex"]["retained_gaps"] == []
    assert calls == [[".basepack/memory/codex-attachments/old.png", ".basepack/memory/codex/old-thread.txt"]]


def test_codex_registry_is_used_for_maintenance_scope(tmp_path, monkeypatch):
    import json
    from basepack.memory.cli import _collect_codex
    from basepack.memory import codex, codex_binding
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine, max_concurrent_subagents=12, concurrency_source="test fixture"))
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

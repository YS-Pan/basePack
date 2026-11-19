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
                        {"needs_semantic": False, "semantic_sources": 0, "pending_relations": 0,
                         "feedback": 0, "receipt": str(receipt)})
    parser = argparse.ArgumentParser()
    register_commands(parser.add_subparsers(dest="command"))
    args = parser.parse_args(["memory", "maintain", "--holder", "thread", "--control", "task.control"])
    result, status = dispatch(args, config)
    assert status == 0 and result["needs_semantic"] == 0
    assert result["codex"]["status"] == "not_configured"
    control = str(Path("task.control").resolve())
    assert calls == [(["docs/new.md"], {"control": control, "timeout": 600, "include_registered": True})]
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
    assert result["executor"] == "worker" and result["level"] == config.resolve_ai(purpose="retrieval")["level"]
    assert not Path(result["delivery_receipt"]).exists()
    with pytest.raises(ValueError, match="positive integer"):
        dispatch(_memory_args("retrieve", "--question", "Question", "--available-subagents", "0", "--level", "0"), config)
    again, _ = dispatch(_memory_args("retrieve", "--request", result["request"], "--available-subagents", "0",
                                    "--level", "4"), config)
    assert again["delivery_id"] == result["delivery_id"] and again["delivery_receipt"] == result["delivery_receipt"]
    assert again["executor"] == "main" and again["level"] is None and again["model"] is None and not again["started"]
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


@pytest.mark.parametrize("mode,available,counts,planned", [
    ("automatic", 0, (8, 0, 0), 0), ("automatic", 4, (2, 0, 0), 3),
    ("automatic", 12, (8, 0, 0), 9), ("manual", 12, (6, 0, 0), 7),
    ("manual", 12, (0, 0, 0), 0), ("manual", 12, (0, 3, 0), 4),
    ("manual", 12, (0, 0, 2), 3),
])
def test_maintain_saves_layout_for_actual_work_and_capacity(tmp_path, monkeypatch, mode, available,
                                                         counts, planned):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine,
                                              max_concurrent_subagents=12, concurrency_source="test fixture"))
    _provision_password(config)
    receipt = config.memory_dir / "maintenance/receipt.json"
    receipt.parent.mkdir()
    receipt.write_text('{"semantic": [], "pending_relations": []}', encoding="utf-8")
    monkeypatch.setattr("basepack.memory.discovery.discover_sources", lambda *a:
                        {"mode": "configured", "paths": [], "gaps": []})
    monkeypatch.setattr("basepack.memory.store.Memory.maintain", lambda *a, **kw:
                        {"needs_semantic": bool(max(counts)), "semantic_sources": counts[0],
                         "pending_relations": counts[1], "feedback": counts[2], "receipt": str(receipt)})
    result, status = dispatch(_memory_args("maintain", "--holder", "thread", "--control",
                                          str(receipt.with_suffix(".control")), "--mode", mode,
                                          "--available-subagents", str(available)), config)
    assert status == 0
    saved = json.loads(receipt.read_text(encoding="utf-8"))["layout"]
    assert saved == result["layout"]
    assert saved["organization"] == "finite-wave-v1"
    assert len(saved["teams"]) <= 1
    assert saved["reserve"] == 1
    assert saved["capacity_status"] == "verified_available"
    assert saved["work_items"] == max(counts)
    assert saved["planned_subagents"] == planned
    assert saved["run_id"] == result["owner"]["run_id"]
    if planned:
        assert result["worker"]["task_name"] == f"bp_mem_{saved['run_id'][:8]}_coord_0"
        assert "'--team' '0'" in result["worker"]["render_command"]
    else:
        assert "worker" not in result
        assert saved["teams"] == []
        assert bool(result.get("dispatch_blocked")) is bool(max(counts))


@pytest.mark.parametrize("available,executor", [(0, "main"), (1, "worker")])
def test_independent_retrieval_cli_and_removed_pending_dispatch_never_open_store(tmp_path, monkeypatch,
                                                                    available, executor):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine,
                                              max_concurrent_subagents=12, concurrency_source="test fixture"))
    request = tmp_path / "question.json"
    config.raw["ai"]["levels"]["5"] = {"model": "project-model", "reasoning_effort": "high"}
    request.write_text(json.dumps({"question": "如何维护并发上限？", "scope": "docs", "content_budget": 3000}),
                       encoding="utf-8")
    monkeypatch.setattr("basepack.memory.store.Memory", lambda *a:
                        pytest.fail("independent dispatch opened the store"))
    for action in ("retrieval-dispatch", "retrieval-prompt"):
        result, status = dispatch(_memory_args(action, "--request", str(request), "--slot", "1",
                                              "--available-subagents", str(available), "--level", "5"), config)
        assert status == 0 and result["executor"] == executor
        if available:
            assert result["task_name"].startswith("bp_mem_search_") and result["task_name"].endswith("_1")
            assert result["level"] == 5 and result["model"] == "project-model"
        else:
            assert result["task_name"] is None and result["level"] is None
        if action == "retrieval-prompt":
            assert result["prompt"]
    with pytest.raises(SystemExit):
        _memory_args("pending-dispatch", "--receipt", str(tmp_path / "receipt.json"),
                     "--available-subagents", "2")
    assert not config.memory_dir.exists()
    assert not config.memory_password_file.exists()


def test_wave_create_requires_an_explicit_reader_pool_size():
    options = ("wave", "create", "--receipt", "receipt.json", "--control", "control",
               "--run-id", "run", "--tasks", "tasks.json", "--coordinator", "/root/coordinator")
    with pytest.raises(SystemExit):
        _memory_args(*options)
    args = _memory_args(*options, "--readers", "1")
    assert args.readers == 1 and args.wave_action == "create"


def test_prompt_cli_never_constructs_memory_or_creates_state(tmp_path, monkeypatch):
    import json

    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine, max_concurrent_subagents=12, concurrency_source="test fixture"))
    receipt = tmp_path / "receipt.json"
    from basepack.memory.prompts import maintenance_layout
    receipt.write_text(json.dumps({"owner_run_id": "test-run", "semantic": [], "pending_relations": [],
                                   "layout": maintenance_layout(config)}), encoding="utf-8")
    control = config.memory_dir / "new control" / "task.control"
    monkeypatch.setattr("basepack.memory.store.Memory",
                        lambda *args: pytest.fail("rendering opened the memory store"))
    result, status = dispatch(_memory_args("prompt", "--receipt", str(receipt),
                                          "--control", str(control)), config)
    assert status == 0 and result["level"] == 2
    assert result["role"] == "coordinator" and result["prompt"]
    override, status = dispatch(_memory_args("prompt", "--receipt", str(receipt), "--control", str(control),
                                             "--level", "4"), config)
    assert status == 0 and override["level"] == 4
    assert not config.memory_dir.exists()
    assert not config.memory_password_file.exists()
    with pytest.raises(SystemExit):
        _memory_args("prompt", "--receipt", str(receipt), "--control", str(control),
                     "--output", str(config.memory_dir / "prompt.json"))
    assert not config.memory_dir.exists()


def _maintenance_setup(tmp_path, monkeypatch, *, semantic=1, relations=0, feedback=0, registered=()):
    from types import SimpleNamespace

    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine,
                                             max_concurrent_subagents=12, concurrency_source="test fixture"))
    receipt = config.memory_dir / "maintenance" / "receipt.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text(json.dumps({"semantic": [{"path": f"source-{i}.md", "members": []}
                                               for i in range(semantic)],
                                   "pending_relations": [{"id": f"relation:{i}", "basis": []}
                                                         for i in range(relations)],
                                   "feedback": [{"id": f"feedback:{i}"} for i in range(feedback)]}), encoding="utf-8")
    calls = []
    def maintain(scope, **kwargs):
        calls.append((scope, kwargs))
        return {"needs_semantic": bool(semantic or relations or feedback), "semantic_sources": semantic,
                "pending_relations": relations, "feedback": feedback, "receipt": str(receipt)}
    monkeypatch.setattr("basepack.memory.store.Memory", lambda config: SimpleNamespace(
        maintain=maintain, sources=lambda: [{"path": path} for path in registered]))
    return config, receipt, calls


def _collection_receipt(config, paths):
    from hashlib import sha256

    config.raw["memory"]["codex"]["project_id"] = "owned-project"
    snapshots = []
    for relative in paths:
        target = config.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"captured original")
        snapshots.append({"path": relative, "sha256": sha256(target.read_bytes()).hexdigest()})
    receipt = config.memory_dir / "maintenance" / "collection.json"
    receipt.write_text(json.dumps({"status": "captured", "root": str(config.root),
                                   "project_id": "owned-project", "paths": paths,
                                   "snapshots": snapshots, "receipt": str(receipt)}), encoding="utf-8")
    return receipt


def _retained_capture(config):
    config.raw["memory"]["codex"]["project_id"] = "owned-project"
    capture = config.memory_dir / "codex" / "old.txt"
    capture.parent.mkdir(parents=True)
    capture.write_bytes(json.dumps({"project_id": "owned-project", "thread_id": "old", "byte_length": 3,
                                    "managed_attachment": "codex-attachments/old.png"}).encode() + b"\nold\n")
    attachment = config.memory_dir / "codex-attachments" / "old.png"
    attachment.parent.mkdir()
    attachment.write_bytes(b"retained image")
    return [attachment.relative_to(config.root).as_posix(), capture.relative_to(config.root).as_posix()]


@pytest.mark.parametrize("mode", ["automatic", "manual"])
def test_delegated_start_captures_and_runs_preflight_as_the_same_coordinator(tmp_path, monkeypatch, mode):
    from basepack.memory import owner

    config, _, calls = _maintenance_setup(tmp_path, monkeypatch)
    config.raw["memory"]["codex"]["project_id"] = "owned-project"
    monkeypatch.setattr("basepack.memory.discovery.discover_sources", lambda *a: {"mode": "configured", "paths": [], "gaps": []})
    launch, code = dispatch(_memory_args("maintain-start", "--mode", mode, "--holder", "parent",
                                         "--available-subagents", "3"), config)
    assert code == 0 and launch["status"] == "prepared" and owner.status(config.memory_dir) is None
    attempt, control = launch["attempt_id"], launch["control"]
    assert not Path(control).exists()
    assignment = launch["spawn_arguments"]
    assert "collect-prompt" in assignment["message"] and "render_command" in assignment["message"]
    prompt, _ = dispatch(_memory_args("collect-prompt", "--attempt", attempt), config)
    assert 'sandbox_permissions="require_escalated"' in prompt["prompt"]
    assert all(part in prompt["command"] for part in (attempt, prompt["registry"], prompt["receipt"]))
    assert not Path(prompt["registry"]).exists() and not Path(prompt["receipt"]).exists()
    assert prompt["receipt"] in assignment["message"]
    assert "'--retained'" not in assignment["message"]

    captured = ".basepack/memory/codex/new-chat.txt"
    receipt = _collection_receipt(config, [captured])
    material = json.loads(receipt.read_text(encoding="utf-8"))
    receipt = Path(prompt["receipt"])
    material["receipt"] = str(receipt)
    receipt.write_text(json.dumps(material), encoding="utf-8")
    result, code = dispatch(_memory_args("maintain", "--attempt", attempt, "--holder", "parent",
                                          "--control", control, "--mode", mode, "--available-subagents", "3",
                                          "--collection", str(receipt)), config)
    assert code == 0 and result["owner"]["holder"] == "parent" and result["owner"]["run_id"] == attempt
    assert result["worker"]["task_name"] == assignment["task_name"]
    assert len(result["layout"]["teams"][0]["reader_task_names"]) == 1
    assert calls[0][0] == [captured]
    assert calls[0][1]["expected_snapshots"] == {captured: material["snapshots"][0]["sha256"]}
    stop, _ = dispatch(_memory_args("stop", "--attempt", attempt), config)
    assert stop["owner"]["stopped"] is True
    dispatch(_memory_args("release", "--control", control), config)
    assert owner.status(config.memory_dir) is None


def test_delegated_start_has_no_assignment_when_busy_or_capacity_unavailable(tmp_path, monkeypatch):
    from basepack.memory import owner

    config, _, _ = _maintenance_setup(tmp_path, monkeypatch)
    args = _memory_args("maintain-start", "--holder", "parent", "--available-subagents", "2")
    launch, _ = dispatch(args, config)
    assert launch["status"] == "capacity_unavailable" and "spawn_arguments" not in launch
    owner.acquire(config.memory_dir, config.raw["memory"]["project_id"], "other", tmp_path / "other.control")
    launch, _ = dispatch(args, config)
    assert launch["status"] == "busy" and launch["owner"]["holder"] == "other"
    assert "spawn_arguments" not in launch


def test_retained_fallback_is_explicit_in_the_clean_coordinator_prompt(tmp_path, monkeypatch):
    config, _, _ = _maintenance_setup(tmp_path, monkeypatch)
    config.raw["memory"]["codex"]["project_id"] = "owned-project"
    fallback, _ = dispatch(_memory_args("maintain-start", "--holder", "parent", "--allow-retained"), config)
    retained, _ = dispatch(_memory_args("maintain-start", "--holder", "parent", "--retained"), config)
    fallback_prompt = fallback["spawn_arguments"]["message"]
    retained_prompt = retained["spawn_arguments"]["message"]
    assert "collect-prompt" in fallback_prompt and "the parent has authorized retained originals" in fallback_prompt
    assert "collect-prompt" not in retained_prompt and "--retained" in retained_prompt


def test_parent_can_stop_delegated_start_before_collection_or_owner(tmp_path, monkeypatch):
    from basepack.memory import owner
    from basepack.memory.maintenance import MaintenanceStopped

    config, _, _ = _maintenance_setup(tmp_path, monkeypatch)
    monkeypatch.setattr("basepack.memory.codex.AppServer", lambda *a: pytest.fail("cancelled attempt opened Codex"))
    config.raw["memory"]["codex"] = {"project_id": "owned-project", "registry_complete": True,
                                      "other_project_roots": []}
    launch, _ = dispatch(_memory_args("maintain-start", "--holder", "parent"), config)
    attempt, control = launch["attempt_id"], launch["control"]
    stopped, _ = dispatch(_memory_args("stop", "--attempt", attempt), config)
    assert stopped["stopped"] and stopped["owner"] is None
    with pytest.raises(MaintenanceStopped):
        dispatch(_memory_args("collect", "--attempt", attempt), config)
    with pytest.raises(MaintenanceStopped):
        dispatch(_memory_args("maintain", "--attempt", attempt, "--holder", "parent",
                              "--control", control, "--retained"), config)
    assert owner.status(config.memory_dir) is None and not Path(control).exists()


def test_maintain_discovers_git_project_and_emits_complete_worker_command(tmp_path, monkeypatch):
    config, receipt, calls = _maintenance_setup(tmp_path, monkeypatch)
    subprocess.run(["git", "init", "-q"], cwd=config.root, check=True)
    (config.root / "outside-current-task.md").write_text("Project wide", encoding="utf-8")
    (config.root / "unsupported.bin").write_bytes(b"binary\0content")
    result, status = dispatch(_memory_args("maintain", "--holder", "thread", "--control",
                                          str(config.memory_dir / "maintenance" / "task.control")), config)
    assert status == 0
    assert "outside-current-task.md" in calls[0][0]
    assert all(not path.startswith(".basepack/") for path in calls[0][0])
    assert result["discovery"]["mode"] == "git"
    assert result["discovery"]["gaps"] == [{"path": "unsupported.bin", "reason": "binary"}]
    worker = result["worker"]
    assert worker["role"] == "coordinator" and worker["level"] == 2
    assert worker["model"] == config.resolve_ai(level=2)["model"]
    assert worker["reasoning_effort"] == config.resolve_ai(level=2)["reasoning_effort"]
    assert "prompt" not in worker
    control = Path(result["control"])
    assert control.is_absolute() and control.parent == config.memory_dir / "maintenance"
    assert str(control) in worker["render_command"] and str(receipt) in worker["render_command"]
    assert calls[0][1] == {"control": str(control), "timeout": 600, "include_registered": True}
    material = json.loads(receipt.read_text(encoding="utf-8"))
    assert material["layout"] == result["layout"]
    assert worker["task_name"] == f"bp_mem_{result['owner']['run_id'][:8]}_coord_0"
    assert material["layout"]["planned_subagents"] == 2
    assert material["layout"]["unused_subagents"] == 9


def test_maintain_consumes_verified_collection_and_hands_off_provenance(tmp_path, monkeypatch):
    config, receipt, calls = _maintenance_setup(tmp_path, monkeypatch, semantic=2)
    captured = ".basepack/memory/codex-attachments/captured.png"
    collection = _collection_receipt(config, [captured])
    monkeypatch.setattr("basepack.memory.collection.collect", lambda *a, **kw: pytest.fail("maintain collected implicitly"))
    monkeypatch.setattr("basepack.memory.discovery.discover_sources", lambda *a: {"mode": "configured", "paths": [], "gaps": []})
    result, status = dispatch(_memory_args("maintain", "--holder", "thread", "--control", str(tmp_path / "control"),
                                          "--collection", str(collection)), config)
    assert status == 0 and calls[0][0] == [captured]
    material = json.loads(receipt.read_text(encoding="utf-8"))
    assert material["codex"] == {**result["codex"], "capture_dir": str(config.memory_dir / "codex"),
                                  "attachment_dir": str(config.memory_dir / "codex-attachments")}
    assert result["codex"]["status"] == "captured" and result["codex"]["receipt"] == str(collection)
    assert material["owner_run_id"] == result["owner"]["run_id"]
    # Provenance stays in the coordinator plan; reader prompts now come from a claimed wave task.
    from basepack.memory.prompts import render_prompt
    rendered = render_prompt(config, result["receipt"], result["control"])
    assert f"Codex provenance inputs: {json.dumps(material['codex'], ensure_ascii=False)}" in rendered["prompt"]
    with pytest.raises(SystemExit):
        _memory_args("prompt", "--receipt", str(receipt), "--control", str(tmp_path / "control"),
                     "--role", "reader", "--paths", captured)


def test_maintain_retained_is_explicit_and_freshness_remains_unknown(tmp_path, monkeypatch):
    config, _, calls = _maintenance_setup(tmp_path, monkeypatch, semantic=0)
    retained = _retained_capture(config)
    monkeypatch.setattr("basepack.memory.collection.collect", lambda *a, **kw: pytest.fail("retained invoked collector"))
    monkeypatch.setattr("basepack.memory.discovery.discover_sources", lambda *a: {"mode": "configured", "paths": [], "gaps": []})
    result, status = dispatch(_memory_args("maintain", "--holder", "thread", "--control", str(tmp_path / "control"),
                                          "--retained"), config)
    assert status == 0 and calls[0][0] == retained
    assert result["codex"]["status"] == "retained" and result["codex"]["freshness"] == "unknown"
    assert calls[0][1]["include_registered"] is True


def test_explicit_scope_excludes_unrelated_captures_and_registered_pending(tmp_path, monkeypatch):
    config, _, calls = _maintenance_setup(tmp_path, monkeypatch, registered=("docs/deleted.md", "docs2/unrelated.md"))
    _retained_capture(config)
    (config.root / "docs").mkdir()
    (config.root / "docs/current.md").write_text("Current source", encoding="utf-8")
    result, status = dispatch(_memory_args("maintain", "--holder", "thread", "--control", str(tmp_path / "control"),
                                          "--retained", "--scope", "docs"), config)
    assert status == 0
    assert calls[0][0] == ["docs/current.md", "docs/deleted.md"]
    assert calls[0][1]["include_registered"] is False
    assert result["discovery"]["mode"] == "explicit" and result["discovery"]["sources"] == 2


def test_explicit_scope_can_select_retained_chat_directory(tmp_path, monkeypatch):
    config, _, calls = _maintenance_setup(tmp_path, monkeypatch)
    retained = _retained_capture(config)
    result, status = dispatch(_memory_args("maintain", "--holder", "thread", "--control", str(tmp_path / "control"),
                                          "--retained", "--scope", ".basepack/memory/codex"), config)
    assert status == 0 and calls[0][0] == [retained[1]]
    assert calls[0][1]["include_registered"] is False


def test_bound_project_requires_collection_selection_and_releases_failed_startup(tmp_path, monkeypatch):
    from basepack.memory import owner

    config, _, _ = _maintenance_setup(tmp_path, monkeypatch)
    config.raw["memory"]["codex"]["project_id"] = "owned-project"
    monkeypatch.setattr("basepack.memory.store.Memory", lambda config: pytest.fail("selection error opened store"))
    control = tmp_path / "control"
    with pytest.raises(ValueError, match="--collection.*--retained"):
        dispatch(_memory_args("maintain", "--holder", "thread", "--control", str(control)), config)
    assert owner.status(config.memory_dir) is None
    assert control.read_bytes() == b"S"


def test_maintenance_collection_choices_are_exclusive_and_skip_flag_is_removed():
    for options in (("--collection", "receipt.json", "--retained"), ("--skip-codex-collection",)):
        with pytest.raises(SystemExit):
            _memory_args("maintain", "--holder", "thread", "--control", "control", *options)


def test_collect_cli_is_independent_of_store_and_maintenance_owner(tmp_path, monkeypatch):
    from basepack.memory import owner

    config, _, _ = _maintenance_setup(tmp_path, monkeypatch)
    monkeypatch.setattr("basepack.memory.store.Memory", lambda config: pytest.fail("collect opened store"))
    monkeypatch.setattr(owner, "acquire", lambda *a, **kw: pytest.fail("collect acquired maintenance owner"))
    calls = []
    output = config.memory_dir / "maintenance" / "collection.json"
    result = {"status": "captured", "receipt": str(output), "paths": []}
    monkeypatch.setattr("basepack.memory.collection.collect", lambda *a, **kw: calls.append((a, kw)) or result)
    assert dispatch(_memory_args("collect", "--codex-registry", "registry.json", "--output", str(output)), config) == (
        {"status": "captured", "output": str(output)}, 0)
    assert calls == [((config, "registry.json"), {"output": str(output)})]
    assert owner.status(config.memory_dir) is None


def test_collection_failure_preserves_original_error_without_owner_cleanup(tmp_path, monkeypatch):
    from basepack.memory import owner

    config, _, _ = _maintenance_setup(tmp_path, monkeypatch)
    error = RuntimeError("collector SQLite error 14")
    def failed(*args, **kwargs):
        raise error
    monkeypatch.setattr("basepack.memory.collection.collect", failed)
    with pytest.raises(RuntimeError) as failure:
        dispatch(_memory_args("collect"), config)
    assert failure.value is error and owner.status(config.memory_dir) is None


def test_startup_cleanup_failure_keeps_both_errors(tmp_path, monkeypatch):
    from basepack.memory import owner

    config, _, _ = _maintenance_setup(tmp_path, monkeypatch)
    original, cleanup = RuntimeError("selected receipt failed"), OSError("owner state is unavailable")
    def fail_original(*args, **kwargs):
        raise original
    def fail_cleanup(*args, **kwargs):
        raise cleanup
    monkeypatch.setattr("basepack.memory.collection.load_collection", fail_original)
    monkeypatch.setattr(owner, "release_failed_startup", fail_cleanup)
    with pytest.raises(ExceptionGroup) as failure:
        dispatch(_memory_args("maintain", "--holder", "thread", "--control", str(tmp_path / "control"),
                              "--collection", "receipt.json"), config)
    assert failure.value.exceptions == (original, cleanup)
    assert owner.status(config.memory_dir)["holder"] == "thread"

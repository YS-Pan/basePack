from concurrent.futures import ThreadPoolExecutor

import pytest

from basepack.memory import feedback
from basepack.memory.draft import freeze
from test_memory_store import memory as store_memory


@pytest.fixture
def memory(store_memory, tmp_path):
    memory = store_memory
    (memory.config.root / "sample.md").write_text("old\n", encoding="utf-8")
    prepared = memory.prepare(["sample.md"])
    batch = freeze([{"sources": [{"path": "sample.md", "revision": prepared["sources"][0]["revision"]}],
                     "expected": prepared["expected"], "members": [
                         {"kind": "chunk", "path": "sample.md", "start_line": 1, "end_line": 1}]}])
    memory.apply(batch)
    memory.test_member = memory.knowledge(batch["members"][0]["id"])
    from basepack.memory.owner import acquire
    memory.test_control = str(tmp_path / "feedback.control")
    acquire(memory.config.memory_dir, memory.connection["project_id"], "test", memory.test_control)
    return memory


def test_concurrent_reports_and_version_checked_resolution(memory):
    target = memory.test_member["id"]
    old_revision = memory.test_member["knowledge_revision"]
    def submit(i):
        return feedback.report(memory, kind="knowledge", issue=f"issue {i}", target=target,
                               observed_revision=old_revision, reporter=f"worker {i}")
    with ThreadPoolExecutor(max_workers=4) as pool:
        reports = list(pool.map(submit, range(4)))
    miss = feedback.report(memory, kind="retrieval", issue="missing result", query="database", source="guide.md")
    assert len({row["id"] for row in reports}) == 4
    assert len(feedback.pending(memory)) == 5
    (memory.config.root / "sample.md").write_text("new\n", encoding="utf-8")
    prepared = memory.prepare(["sample.md"])
    memory.apply(freeze([{"sources": [{"path": "sample.md", "revision": prepared["sources"][0]["revision"]}],
                          "expected": prepared["expected"], "members": [
                              {"id": target, "kind": "chunk", "path": "sample.md", "start_line": 1, "end_line": 1}]}]), control=memory.test_control)
    new_revision = memory.knowledge(target)["knowledge_revision"]
    with pytest.raises(RuntimeError, match="revision changed"):
        feedback.resolve(memory, reports[0]["id"], outcome="fixed", result="corrected", control=memory.test_control, expected_revision=old_revision)
    assert len(feedback.pending(memory)) == 5
    fixed = feedback.resolve(memory, reports[0]["id"], outcome="fixed", result="corrected", control=memory.test_control, expected_revision=new_revision)
    assert fixed["observed_revision"] == old_revision and fixed["resolved_revision"] == new_revision
    with pytest.raises(RuntimeError, match="no longer pending"):
        feedback.resolve(memory, reports[0]["id"], outcome="fixed", result="again", control=memory.test_control, expected_revision=new_revision)
    feedback.resolve(memory, miss["id"], outcome="invalid", result="already returned", control=memory.test_control)
    assert len(feedback.pending(memory)) == 3
    assert len(feedback.list_reports(memory, all_reports=True)) == 5


def test_feedback_input_contract(memory):
    with pytest.raises(ValueError, match="together"):
        feedback.report(memory, kind="knowledge", issue="issue", target=memory.test_member["id"])
    with pytest.raises(ValueError, match="query or source"):
        feedback.report(memory, kind="retrieval", issue="miss")
    row = feedback.report(memory, kind="knowledge", issue="issue", target=memory.test_member["id"], observed_revision=memory.test_member["knowledge_revision"])
    with pytest.raises(ValueError, match="current expected revision"):
        feedback.resolve(memory, row["id"], outcome="invalid", result="reason", control=memory.test_control)
    with pytest.raises(ValueError, match="does not exist"):
        feedback.resolve(memory, "feedback:missing", outcome="invalid", result="reason", control=memory.test_control)


def test_resolution_requires_maintenance_owner(memory, tmp_path):
    row = feedback.report(memory, kind="retrieval", issue="missing", query="example")
    with pytest.raises(PermissionError, match="owner|control"):
        feedback.resolve(memory, row["id"], outcome="invalid", result="reason",
                         control=str(tmp_path / "other.control"))
    assert [item["id"] for item in feedback.pending(memory)] == [row["id"]]


def test_resolution_returns_transaction_result_without_post_commit_read(memory, monkeypatch):
    row = feedback.report(memory, kind="retrieval", issue="missing", query="example")
    execute = memory._execute
    statements = []

    def record(sql, **kwargs):
        statements.append(sql)
        return execute(sql, **kwargs)

    monkeypatch.setattr(memory, "_execute", record)
    result = feedback.resolve(memory, row["id"], outcome="invalid", result="already returned",
                              control=memory.test_control)
    assert result["id"] == row["id"] and result["status"] == "resolved"
    business = [sql for sql in statements if not sql.startswith('IF meta:project.project_id')]
    assert len(business) == 2 and business[0].startswith("SELECT") and business[1].startswith("BEGIN")


@pytest.mark.parametrize("error_type", [ConnectionError, RuntimeError])
def test_ambiguous_resolution_retains_publication(memory, monkeypatch, error_type):
    from basepack.memory.owner import status
    row = feedback.report(memory, kind="retrieval", issue="missing", query="example")
    execute = memory._execute

    def disconnect(sql, **kwargs):
        if sql.startswith("BEGIN"):
            raise error_type("commit outcome unknown")
        return execute(sql, **kwargs)

    monkeypatch.setattr(memory, "_execute", disconnect)
    with pytest.raises(error_type, match="unknown"):
        feedback.resolve(memory, row["id"], outcome="invalid", result="reason", control=memory.test_control)
    assert len(status(memory.config.memory_dir)["publications"]) == 1


def test_feedback_cli_dispatch(monkeypatch):
    import argparse
    from basepack.memory.cli import dispatch, register_commands
    parser = argparse.ArgumentParser()
    register_commands(parser.add_subparsers(dest="command"))
    sentinel = object()
    monkeypatch.setattr("basepack.memory.store.Memory", lambda config: sentinel)
    calls = []
    monkeypatch.setattr(feedback, "report", lambda memory, **kw: calls.append((memory, kw)) or {"ok": True})
    args = parser.parse_args(["memory", "feedback-report", "--kind", "retrieval", "--issue", "miss",
                              "--query", "example"])
    assert dispatch(args, None) == ({"ok": True}, 0)
    assert calls[0][0] is sentinel and calls[0][1]["query"] == "example"
    with pytest.raises(SystemExit):
        parser.parse_args(["memory", "feedback-resolve", "feedback:1", "--outcome", "fixed", "--result", "done"])


def test_native_export_restores_pending_and_old_seven_table_backup(memory, tmp_path):
    import os
    from copy import deepcopy
    from pathlib import Path
    import subprocess

    executable = os.environ.get("BASEPACK_SURREAL_TEST_EXECUTABLE")
    if not executable:
        pytest.skip("requires SurrealDB CLI for native export and import")
    env = os.environ.copy()
    env["SURREAL_USER"] = "root"
    env["SURREAL_PASS"] = Path(os.environ["BASEPACK_MEMORY_TEST_PASSWORD_FILE"]).read_text(encoding="utf-8-sig")
    endpoint = os.environ["BASEPACK_MEMORY_TEST_ENDPOINT"]
    def run(action, database, path, *options):
        subprocess.run([executable, action, "--endpoint", endpoint, "--namespace", memory.connection["namespace"],
                        "--database", database, *options, str(path)], check=True, env=env, capture_output=True)
    feedback.report(memory, kind="retrieval", issue="missing", query="example")
    full = tmp_path / "full.surql"
    old = tmp_path / "old.surql"
    run("export", memory.connection["database"], full)
    run("export", memory.connection["database"], old, "--tables-exclude", "feedback")
    for database, path, expected in [("feedback_full_restore", full, 1), ("feedback_old_restore", old, 0)]:
        database += "_" + memory.connection["database"]
        restored_config = deepcopy(memory.config)
        restored_config.raw["memory"]["database"] = database
        from basepack.memory.store import Memory
        restored = Memory(restored_config)
        restored._execute(f"DEFINE DATABASE IF NOT EXISTS {database};", check_project=False)
        run("import", database, path)
        restored.install_schema()
        assert len(feedback.pending(restored)) == expected

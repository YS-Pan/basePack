from test_memory_store import batch_for, memory


def test_task_start_detects_scoped_addition_without_claiming_it_understood(memory):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    memory.connection["source_scope"] = ["guide.md", "incoming"]
    incoming = memory.config.root / "incoming"
    incoming.mkdir()
    (incoming / "new.md").write_text("新增例外需要实际阅读。\n", encoding="utf-8")
    brief = memory.brief(limit=0)
    assert brief["changes"][0]["path"] == "incoming/new.md"
    assert brief["changes"][0]["kind"] == "added"
    assert brief["source_count"] == 1
    assert memory.search("新增例外") == []
    assert len(brief["mandatory"]) == 1


def test_task_start_checks_registered_originals_outside_new_discovery_scope(memory):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    memory.connection["source_scope"] = ["incoming"]
    source = memory.config.root / "guide.md"
    source.write_bytes(source.read_bytes() + "\n新增例外。\n".encode("utf-8"))
    assert memory.brief()["changes"][0]["path"] == "guide.md"


def test_task_start_marks_old_facts_and_does_not_duplicate_invalidation_history(memory):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    source = memory.config.root / "guide.md"
    source.write_bytes(source.read_bytes() + "\n新增关键例外。\n".encode("utf-8"))
    first = memory.brief(limit=0)
    assert first["mandatory"][0]["stale"] is True
    assert "member:guide" in {row["id"] for row in first["pending"]}
    count = len(memory._rows("change"))
    second = memory.brief(limit=0)
    assert second["change_count"] == 1
    assert len(memory._rows("change")) == count
    assert "member:guide" not in {row["id"] for row in memory.search("项目", literal=True)}


def test_unchanged_start_reads_metadata_without_loading_all_member_bodies(memory, monkeypatch):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    original_rows = memory._rows

    def rows(table):
        assert table != "member", "unchanged startup must not fetch all accepted bodies"
        return original_rows(table)

    monkeypatch.setattr(memory, "_rows", rows)
    assert memory.brief(limit=0)["changes"] == []


def test_unmatched_task_still_receives_short_project_map_without_opaque_versions(memory):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    result = memory.brief("完全未出现在原文的任务词")
    assert result["clues"]
    assert all(row["clue_role"] == "map" for row in result["clues"])
    assert "basis" not in result["mandatory"][0]
    assert "knowledge_revision" not in result["mandatory"][0]
    candidates = memory.search("数据库")
    assert candidates
    assert all("basis" not in row and "knowledge_revision" not in row for row in candidates)


def test_node_merge_and_deleted_support_preserve_remaining_evidence(memory):
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    batch["nodes"].append({"id": "alias", "kind": "decision", "text": "采用本地数据库", "evidence": ["storage"]})
    batch["edges"].append({"id": "preserve", "in": "node:alias", "out": "member:retention",
                           "kind": "depends", "text": "资料需保留", "evidence": ["retention"]})
    memory.apply(batch)
    expected = memory.prepare(["guide.md"])["expected"]
    memory.apply({"sources": [], "expected": expected, "delete_nodes": ["alias"],
                  "edges": [{"id": "preserve", "in": "node:local", "out": "member:retention",
                             "kind": "depends", "text": "资料需保留", "evidence": ["retention"]}]})
    assert {edge["id"] for edge in memory.neighbors("node:local")["edges"]} == {"semantic:requires", "semantic:preserve"}
    assert memory.neighbors("node:alias")["record"]["retired"] is True
    assert any(row.get("previous") and row["previous"].get("in") == "node:alias"
               for row in memory._rows("change") if row.get("target") == "semantic:preserve")

    (memory.config.root / "backup.md").write_bytes("本地数据库隔离项目。\n".encode("utf-8"))
    prepared = memory.prepare(["guide.md", "backup.md"])
    backup = next(row for row in prepared["sources"] if row["path"] == "backup.md")
    members = [
        {"id": "backup", "kind": "file", "path": "backup.md", "parent": None,
         "start_line": 1, "end_line": 1, "title": "另一依据", "text": "本地数据库隔离项目。", "evidence": ["backup_leaf"]},
        {"id": "backup_leaf", "kind": "chunk", "path": "backup.md", "parent": "backup",
         "start_line": 1, "end_line": 1, "title": "隔离要求", "text": "本地数据库隔离项目。\n"},
    ]
    edge = {"id": "requires", "in": "node:local", "out": "member:storage", "kind": "depends",
            "text": "本地数据库隔离项目", "evidence": ["storage", "backup_leaf"]}
    memory.apply({"sources": [{"path": "backup.md", "revision": backup["revision"]}],
                  "expected": prepared["expected"], "members": members, "edges": [edge]})
    (memory.config.root / "backup.md").unlink()
    assert "semantic:requires" in {row["id"] for row in memory.brief()["pending"]}
    prepared = memory.prepare(["guide.md", "backup.md"])
    edge["evidence"] = ["storage"]
    memory.apply({"sources": [{"path": "backup.md", "revision": backup["revision"], "deleted": True}],
                  "expected": prepared["expected"], "edges": [edge]})
    assert memory.brief()["pending_count"] == 0
    assert len(memory._rows("source_version")) == 2
    assert any(row.get("text") == "本地数据库隔离项目。\n" for row in memory._rows("source_version"))
    assert len(memory.neighbors("node:local")["edges"]) == 2
    assert next(row for row in memory._rows("member") if row["id"] == "member:backup_leaf")["retired"] is True
    assert memory.changes(["backup.md"]) == []


def test_chunk_boundaries_take_exact_crlf_original_without_repeating_raw_text(memory):
    source = memory.config.root / "windows.md"
    source.write_bytes("# 标题\r\n条件与例外必须保留。\r\n".encode("utf-8"))
    prepared = memory.prepare(["windows.md"])
    memory.apply({"sources": [{"path": "windows.md", "revision": prepared["sources"][0]["revision"]}],
                  "expected": prepared["expected"], "members": [
                      {"id": "windows", "kind": "file", "path": "windows.md", "parent": None,
                       "start_line": 1, "end_line": 2, "title": "标题", "text": "条件与例外须保留。", "evidence": ["windows_body"]},
                      {"id": "windows_body", "kind": "chunk", "path": "windows.md", "parent": "windows",
                       "start_line": 2, "end_line": 2, "title": "条件"}]})
    assert memory.read("windows_body")["original"]["text"] == "条件与例外必须保留。\r\n"


def test_accepted_source_deletion_removes_retired_startup_obligations(memory):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    prepared = memory.prepare(["guide.md"])
    (memory.config.root / "guide.md").unlink()
    memory.apply({"sources": [{"path": "guide.md", "revision": prepared["sources"][0]["revision"], "deleted": True}],
                  "expected": prepared["expected"], "delete_nodes": ["local"], "delete_edges": ["requires"]})
    brief = memory.brief()
    assert brief["mandatory"] == []
    assert brief["mandatory_pending_count"] == 0
    assert brief["pending_count"] == 0
    assert brief["coverage_gaps_count"] == 0

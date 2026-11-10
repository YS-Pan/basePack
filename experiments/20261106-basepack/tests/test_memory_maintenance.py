import pytest

from test_memory_store import batch_for, memory


def test_task_start_detects_scoped_addition_without_claiming_it_understood(memory):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    memory.connection["source_scope"] = ["guide.md", "incoming"]
    incoming = memory.config.root / "incoming"
    incoming.mkdir()
    (incoming / "new.md").write_text("新增例外需要实际阅读。\n", encoding="utf-8")
    brief = memory.brief(limit=0)
    assert brief["changes"] == []
    assert memory.changes(["incoming"])[0]["path"] == "incoming/new.md"
    assert memory.changes(["incoming"])[0]["kind"] == "added"
    assert brief["source_count"] == 1
    assert memory.search("新增例外") == []
    assert len(brief["mandatory"]) == 1


def test_task_start_checks_registered_originals_outside_new_discovery_scope(memory):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    memory.connection["source_scope"] = ["incoming"]
    source = memory.config.root / "guide.md"
    source.write_bytes(source.read_bytes() + "\n新增例外。\n".encode("utf-8"))
    assert memory.brief()["changes"] == []
    assert memory.changes(["guide.md"])[0]["path"] == "guide.md"


def test_change_detection_keeps_published_knowledge(memory):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    source = memory.config.root / "guide.md"
    source.write_bytes(source.read_bytes() + "\n新增关键例外。\n".encode("utf-8"))
    count = len(memory._rows("change"))
    assert memory.changes(["guide.md"])[0]["kind"] == "modified"
    assert memory.brief(limit=0)["mandatory"][0]["stale"] is False
    assert "member:guide" in {row["id"] for row in memory.search("项目", literal=True)}
    assert len(memory._rows("change")) == count


def test_unchanged_start_reads_metadata_without_loading_all_member_bodies(memory, monkeypatch):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    original_rows = memory._rows

    def rows(table):
        assert table != "member", "unchanged startup must not fetch all accepted bodies"
        return original_rows(table)

    monkeypatch.setattr(memory, "_rows", rows)
    assert memory.brief(limit=0)["changes"] == []


def test_startup_receives_short_project_map_without_opaque_versions(memory):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    result = memory.brief()
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
    assert "semantic:requires" not in {row["id"] for row in memory.brief()["pending"]}
    assert memory.changes(["backup.md"])[0]["kind"] == "deleted"
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


def test_retired_chunk_does_not_invalidate_reaccepted_ancestors(memory):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    updated = batch_for(memory, "# 数据库\n数据库离线运行并隔离项目。\n\n# 保留\n资料必须保留。\n")
    updated["members"][2]["id"] = "current_storage"
    for item in updated["members"] + updated["nodes"] + updated["edges"]:
        item["evidence"] = ["current_storage" if value == "storage" else value for value in item.get("evidence", [])]
    updated["edges"][0]["out"] = "member:current_storage"
    updated["delete_members"] = ["storage"]
    memory.apply(updated)
    prepared = memory.prepare(["guide.md"])
    before = {row["id"]: row for row in prepared["sources"][0]["members"]}
    assert before["member:storage"]["retired"] is True
    assert prepared["expected"]["member:storage"] == before["member:storage"]["knowledge_revision"]
    assert memory.brief(limit=0)["pending_count"] == 0
    relation = {"id": "current_support", "in": "member:current_storage", "out": "member:retention",
                "kind": "supports", "text": "当前条件共同约束存储", "evidence": ["current_storage", "retention"]}
    result = memory.apply({"sources": updated["sources"], "expected": prepared["expected"], "edges": [relation]})
    assert result["invalidated"] == []
    assert memory.brief(limit=0)["pending_count"] == 0
    assert memory.read("current_storage")["original"]["text"] == "数据库离线运行并隔离项目。\n"
    assert {row["id"] for row in memory.neighbors("current_storage")["edges"]} == {
        "semantic:requires", "semantic:current_support"}
    after = {row["id"]: row for row in memory._rows("member")}
    for member_id in ("member:guide", "member:storage_section", "member:storage"):
        assert after[member_id] == before[member_id]
    assert memory.apply({"sources": updated["sources"]})["invalidated"] == []


@pytest.mark.parametrize("retired", [False, True])
def test_only_active_summary_dependencies_propagate_changes(memory, retired):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    updated = batch_for(memory, "# 数据库\n数据库离线运行并隔离项目。\n\n# 保留\n资料必须保留。\n")
    guide, storage = updated["members"][0], updated["members"][2]
    guide.update(start_line=4, end_line=5, text="资料必须保留。", evidence=["retention"],
                 coverage_gaps=["数据库章节独立维护"])
    memory.apply({"sources": updated["sources"], "expected": updated["expected"],
                  "members": [guide, storage], "delete_members": ["storage_section"] if retired else []})
    prepared = memory.prepare(["guide.md"])
    section = next(row for row in prepared["sources"][0]["members"] if row["id"] == "member:storage_section")
    assert section["stale"] is retired
    assert section["retired"] is retired
    storage["title"] = "离线隔离条件"
    result = memory.apply({"sources": updated["sources"], "expected": prepared["expected"], "members": [storage]})
    assert result["invalidated"] == []
    assert memory.read("guide")["member"]["stale"] is False
    # Existing node retains its old versioned evidence, even if the new member changes.
    assert memory.neighbors("node:local")["record"]["stale"] is False


def test_retired_unchanged_history_keeps_source_version_and_can_be_explicitly_revived(memory):
    original = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    memory.apply(original)
    prepared = memory.prepare(["guide.md"])
    memory.apply({"sources": [], "expected": prepared["expected"], "delete_members": ["storage", "storage_section"],
                  "delete_nodes": ["local"], "delete_edges": ["requires"]})
    retired = {row["id"]: row for row in memory._rows("member") if row["retired"]}
    updated = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料与旧依据必须保留。\n")
    updated["members"][0]["evidence"] = ["retention"]
    memory.apply({"sources": updated["sources"], "expected": updated["expected"],
                  "members": [updated["members"][0], updated["members"][3]]})
    after = {row["id"]: row for row in memory._rows("member") if row["retired"]}
    assert after == retired
    snapshot = memory._execute(f"SELECT * FROM ONLY {after['member:storage']['source_version']};")[0]
    assert snapshot["text"] == "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"
    prepared = memory.prepare(["guide.md"])
    revival = {"sources": updated["sources"], "members": [{**original["members"][2], "parent": None}]}
    with pytest.raises(RuntimeError, match="requires expected revision"):
        memory.apply(revival)
    memory.apply({"sources": [], "expected": prepared["expected"], "delete_members": ["storage"]})
    with pytest.raises(RuntimeError, match="Knowledge revision changed"):
        memory.apply({**revival, "expected": prepared["expected"]})
    memory.apply({**revival, "expected": memory.prepare(["guide.md"])["expected"],
                  "corrections": [{"id": "revive_storage", "target": "member:storage", "reason": "重新接受当前原文"}]})
    current = memory.read("storage")["member"]
    assert current["retired"] is False
    assert current["source_revision"] == updated["sources"][0]["revision"]
    previous = memory._execute("SELECT * FROM ONLY change:revive_storage;")[0]["previous"]
    assert previous["retired"] is True
    assert previous["source_version"] == retired["member:storage"]["source_version"]

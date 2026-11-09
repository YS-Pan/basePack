"""Opt-in integration checks against an actual local SurrealDB server.

The namespace/database are disposable. Start a native server, then set
BASEPACK_MEMORY_TEST_ENDPOINT and BASEPACK_MEMORY_TEST_PASSWORD to run.
"""

from copy import deepcopy
import os
from pathlib import Path
import sys

import pytest

from basepack.memory.store import Memory
from basepack.project.config import MachineConfig, ProjectConfig


@pytest.fixture
def memory(tmp_path):
    if "BASEPACK_MEMORY_TEST_ENDPOINT" not in os.environ:
        pytest.skip("requires an actual disposable SurrealDB server")
    config = ProjectConfig(tmp_path / "project.toml", Path(sys.executable), tmp_path,
                           {"memory": {"data_dir": ".basepack/memory", "project_id": "product_test",
                                       "endpoint": os.environ["BASEPACK_MEMORY_TEST_ENDPOINT"],
                                       "namespace": "memsys", "database": "product_tests",
                                       "username": "root", "password_env": "BASEPACK_MEMORY_TEST_PASSWORD"}},
                           MachineConfig(tmp_path / "machine.toml", {}))
    memory = Memory(config)
    memory.install_schema()
    memory._execute("DELETE semantic; DELETE node; DELETE member; DELETE source_version; DELETE source; DELETE change;")
    return memory


def batch_for(memory, text):
    (memory.config.root / "guide.md").write_bytes(text.encode("utf-8"))
    prepared = memory.prepare(["guide.md"])
    source = prepared["sources"][0]
    lines = text.splitlines(keepends=True)
    return {"sources": [{"path": "guide.md", "revision": source["revision"]}], "expected": prepared["expected"], "members": [
        {"id": "guide", "kind": "file", "path": "guide.md", "parent": None,
         "start_line": 1, "end_line": 5, "title": "项目说明", "text": "项目必须采用本地数据库并保留资料。",
         "evidence": ["storage", "retention"], "mandatory": True},
        {"id": "storage_section", "kind": "section", "path": "guide.md", "parent": "guide",
         "start_line": 1, "end_line": 3, "title": "数据库", "text": "本地数据库支持项目隔离。", "evidence": ["storage"]},
        {"id": "storage", "kind": "chunk", "path": "guide.md", "parent": "storage_section",
         "start_line": 2, "end_line": 2, "title": "数据库约束", "text": lines[1]},
        {"id": "retention", "kind": "chunk", "path": "guide.md", "parent": "guide",
         "start_line": 5, "end_line": 5, "title": "资料保留", "text": lines[4]},
    ], "nodes": [{"id": "local", "kind": "decision", "text": "采用本地数据库", "evidence": ["storage"]}],
            "edges": [{"id": "requires", "in": "node:local", "out": "member:storage", "kind": "depends",
                       "text": "决定依赖项目隔离", "evidence": ["storage"]}]}


def test_real_multilevel_roundtrip_local_edit_and_correction(memory):
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    memory.apply(batch)
    hits = memory.search("数据库")
    assert {row["kind"] for row in hits} == {"file", "section", "chunk"}
    assert memory.search("项目说明")[0]["id"] == "member:guide"
    assert memory.search("本地数据库隔离项目", literal=True)[0]["id"] == "member:storage"
    assert memory.read("storage")["original"]["text"] == "本地数据库隔离项目。\n"
    assert memory.neighbors("storage")["parent"]["id"] == "member:storage_section"
    assert memory.neighbors("node:local")["edges"][0]["id"] == "semantic:requires"
    assert memory.brief("资料", limit=0)["mandatory"][0]["id"] == "member:guide"
    old = {row["id"]: row for row in memory._rows("member")}
    updated = batch_for(memory, "# 数据库\n数据库离线运行并隔离项目。\n\n# 保留\n资料必须保留。\n")
    assert memory.changes(["guide.md"])[0]["kind"] == "modified"
    assert memory.search("数据库") == []
    assert memory.search("资料")[0]["id"] == "member:retention"
    with pytest.raises(ValueError, match="revision mismatch"):
        memory.read("storage")
    prepared = memory.prepare(["guide.md"])
    assert "本地数据库隔离项目" in prepared["sources"][0]["previous"]["numbered_text"]
    updated["members"] = [row for row in updated["members"] if row["id"] != "retention"]
    updated["members"][0]["text"] = "项目数据库离线运行，资料必须保留。"
    updated["members"][1]["text"] = "数据库必须离线运行并隔离项目。"
    updated["edges"][0]["text"] = "本地决定依赖离线隔离"
    updated["corrections"] = [{"id": "fix", "target": "member:storage", "reason": "原文增加离线条件",
                               "previous": "untrusted fabricated history"}]
    memory.apply(updated)
    assert memory.read("storage")["original"]["text"] == "数据库离线运行并隔离项目。\n"
    after = {row["id"]: row for row in memory._rows("member")}
    assert after["member:retention"]["input_revision"] == old["member:retention"]["input_revision"]
    assert after["member:retention"]["source_revision"] != old["member:retention"]["source_revision"]
    assert after["member:retention"]["stale"] is False
    assert all(row["stale"] is False for row in memory.search("离线"))
    correction = memory._execute("SELECT * FROM ONLY change:fix;")[0]
    assert correction["previous"]["text"] == old["member:storage"]["text"]
    assert len(memory._rows("source_version")) == 2
    # Adding a second native edge leaves the first intact.
    memory.apply({"sources": [], "edges": [{"id": "also", "in": "member:storage", "out": "member:retention",
                  "kind": "supports", "text": "隔离与保留共同约束存储", "evidence": ["storage", "retention"]}]})
    assert {edge["id"] for edge in memory._rows("semantic")} == {"semantic:requires", "semantic:also"}
    assert memory.changes(["guide.md"], deep=True) == []


def test_real_bad_batch_rolls_back_and_project_binding_rejects(memory):
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    forged = deepcopy(batch)
    forged["members"][2]["text"] = "agent rewrote original"
    with pytest.raises(ValueError, match="differs"):
        memory.apply(forged)
    assert memory._rows("source") == []
    broken = deepcopy(batch)
    broken["edges"][0]["out"] = "member:missing"
    with pytest.raises(RuntimeError):
        memory.apply(broken)
    assert memory._rows("source") == []
    memory.apply(batch)
    wrong = deepcopy(memory.config.raw)
    wrong["memory"]["project_id"] = "another_project"
    config = ProjectConfig(memory.config.path, memory.config.python, memory.config.root, wrong, memory.config.machine)
    with pytest.raises(RuntimeError, match="another project"):
        Memory(config).search("数据库")
    with pytest.raises(RuntimeError, match="another project"):
        Memory(config).install_schema()


def test_real_stale_evidence_and_deleted_original(memory):
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    memory.apply(batch)
    (memory.config.root / "guide.md").write_bytes("# 数据库\n修改了数据库条件。\n\n# 保留\n资料必须保留。\n".encode("utf-8"))
    with pytest.raises(ValueError, match="revision mismatch"):
        memory.apply({"sources": [], "edges": batch["edges"]})
    memory.changes(["guide.md"])
    assert memory._rows("node")[0]["stale"] is True
    assert memory._rows("semantic")[0]["stale"] is True
    (memory.config.root / "guide.md").unlink()
    assert memory.changes(["guide.md"])[0]["kind"] == "deleted"
    assert memory.search("资料") == []
    brief = memory.brief(limit=0)
    assert brief["mandatory"][0]["stale"] is True
    assert {row["id"] for row in brief["pending"]} == {
        "member:guide", "member:storage_section", "member:storage", "member:retention"}
    # Missing originals stay a visible failure; retained history is not passed
    # off as the current business file.
    with pytest.raises(FileNotFoundError):
        memory.read("storage")
    assert len(memory._rows("source_version")) == 1
    prepared = memory.prepare(["guide.md"])["sources"][0]
    assert prepared["deleted"] is True
    assert "本地数据库隔离项目" in prepared["previous"]["numbered_text"]
    memory.apply({"sources": [{"path": "guide.md", "revision": batch["sources"][0]["revision"], "deleted": True}]})
    assert memory.changes(["guide.md"]) == []
    assert memory._rows("source")[0]["deleted"] is True


def test_real_appended_exception_invalidates_complete_summaries(memory):
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    batch["members"].append({"id": "retention_section", "kind": "section", "path": "guide.md",
                             "parent": "guide", "start_line": 4, "end_line": 5,
                             "title": "保留政策", "text": "资料必须保留，没有例外。", "evidence": ["retention"]})
    memory.apply(batch)
    path = memory.config.root / "guide.md"
    path.write_bytes(path.read_bytes() + "但临时缓存允许删除。\n".encode("utf-8"))
    memory.changes(["guide.md"])
    rows = {row["id"]: row for row in memory._rows("member")}
    assert rows["member:guide"]["stale"] is True
    assert rows["member:retention_section"]["stale"] is True
    assert rows["member:storage"]["stale"] is False
    assert rows["member:retention"]["stale"] is False
    prepared = memory.prepare(["guide.md"])["sources"][0]
    memory.apply({"sources": [{"path": "guide.md", "revision": prepared["revision"]}]})
    rows = {row["id"]: row for row in memory._rows("member")}
    assert rows["member:guide"]["stale"] is True
    assert rows["member:retention_section"]["stale"] is True
    assert rows["member:retention"]["stale"] is False
    assert "member:retention_section" not in {row["id"] for row in memory.search("保留")}


def test_real_node_correction_invalidates_relations_and_stale_draft_rejected(memory):
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    memory.apply(batch)
    draft_a = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    draft_b = deepcopy(draft_a)
    independent_member = deepcopy(draft_a)
    draft_a["members"] = draft_a["members"][:1]
    draft_a["members"][0]["text"] = "人工更正：项目须保留资料并采用隔离数据库。"
    draft_a["nodes"][0]["text"] = "人工更正：隔离属于必须条件"
    draft_a["edges"] = []
    memory.apply(draft_a)
    assert memory._rows("semantic")[0]["stale"] is True
    independent_member["members"] = independent_member["members"][2:3]
    independent_member["nodes"] = []
    independent_member["edges"] = []
    memory.apply(independent_member)
    with pytest.raises(RuntimeError, match="Knowledge revision changed"):
        memory.apply(draft_b)
    assert memory.read("guide")["member"]["text"].startswith("人工更正")
    assert memory._rows("node")[0]["text"].startswith("人工更正")
    # A separately prepared, independent new relation remains authorized by
    # source evidence; it does not require a global knowledge epoch.
    memory.apply({"sources": [], "edges": [{"id": "independent", "in": "member:storage", "out": "member:retention",
                   "kind": "supports", "text": "两个原文条件共同约束存储", "evidence": ["storage", "retention"]}]})
    fresh = memory.prepare(["guide.md"])
    memory.apply({"sources": [], "expected": fresh["expected"], "edges": batch["edges"]})
    assert next(row for row in memory._rows("semantic") if row["id"] == "semantic:requires")["stale"] is False
    with pytest.raises(RuntimeError, match="requires expected revision"):
        memory.apply({"sources": [], "edges": batch["edges"]})

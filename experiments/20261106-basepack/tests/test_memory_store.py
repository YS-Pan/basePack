"""Opt-in integration checks against an actual local SurrealDB server.

The namespace/database are disposable. Start an authenticated loopback server,
then set BASEPACK_MEMORY_TEST_ENDPOINT and BASEPACK_MEMORY_TEST_PASSWORD_FILE.
"""

from copy import deepcopy
from hashlib import sha256
import os
from pathlib import Path
import sys
from uuid import uuid4

import pytest

from basepack.memory.draft import freeze
from basepack.memory.store import Memory
from basepack.project.config import MachineConfig, ProjectConfig


EMBEDDING_IDENTITY = "deterministic-memory-tests-v1"


def deterministic_vector(value):
    payload = Path(value["image"]).read_bytes() if isinstance(value, dict) else value.encode("utf-8")
    return [1.0 + byte / 255 for byte in sha256(payload).digest()[:8]]


class DeterministicEmbeddingClient:
    def __init__(self, machine):
        pass

    def embed(self, inputs, *, timeout):
        return {"embedding_identity": EMBEDDING_IDENTITY,
                "vectors": [deterministic_vector(value) for value in inputs]}


def _memory(tmp_path):
    if "BASEPACK_MEMORY_TEST_ENDPOINT" not in os.environ:
        pytest.skip("requires an actual disposable SurrealDB server")
    config = ProjectConfig(tmp_path / "project.toml", Path(sys.executable), tmp_path,
                           {"memory": {"data_dir": ".basepack/memory", "search_mode": "vector", "project_id": uuid4().hex,
                                       "endpoint": os.environ["BASEPACK_MEMORY_TEST_ENDPOINT"], "username": "root",
                                       "password_file": os.environ["BASEPACK_MEMORY_TEST_PASSWORD_FILE"],
                                       "namespace": os.environ.get("BASEPACK_MEMORY_TEST_NAMESPACE", "identity_tests"),
                                       "database": os.environ.get("BASEPACK_MEMORY_TEST_DATABASE", "store") + "_" + uuid4().hex}},
                           MachineConfig(tmp_path / "machine.toml", {}))
    memory = Memory(config)
    memory.install_schema()
    return memory


@pytest.fixture
def memory(tmp_path, monkeypatch):
    from basepack.embedding import admin
    from basepack.memory import candidate_vectors, vectors

    for module in (candidate_vectors, vectors):
        monkeypatch.setattr(module, "EmbeddingClient", DeterministicEmbeddingClient)
        monkeypatch.setattr(module, "status", lambda _: {"model": {"embedding_identity": EMBEDDING_IDENTITY}})
    monkeypatch.setattr(admin, "status", lambda _: {"model": {"embedding_identity": EMBEDDING_IDENTITY}})
    return _memory(tmp_path)


@pytest.fixture
def real_memory(tmp_path):
    """The shared-model checks must use the actual configured service."""
    return _memory(tmp_path)


def batch_for(memory, text, *, previous=None):
    (memory.config.root / "guide.md").write_bytes(text.encode("utf-8"))
    prepared = memory.prepare(["guide.md"])
    source = prepared["sources"][0]
    lines = text.splitlines(keepends=True)
    draft = {"sources": [{"path": "guide.md", "revision": source["revision"]}], "expected": prepared["expected"], "members": [
        {"kind": "file", "path": "guide.md", "parent": None,
         "start_line": 1, "end_line": 5, "title": "项目说明", "text": "项目必须采用本地数据库并保留资料。",
         "evidence": [{"member": 2}, {"member": 3}], "mandatory": True},
        {"kind": "section", "path": "guide.md", "parent": {"member": 0},
         "start_line": 1, "end_line": 3, "title": "数据库", "text": "本地数据库支持项目隔离。", "evidence": [{"member": 2}]},
        {"kind": "chunk", "path": "guide.md", "parent": {"member": 1},
         "start_line": 2, "end_line": 2, "title": "数据库约束", "text": lines[1]},
        {"kind": "chunk", "path": "guide.md", "parent": {"member": 0},
         "start_line": 5, "end_line": 5, "title": "资料保留", "text": lines[4]},
    ], "nodes": [{"id": "local", "kind": "decision", "text": "采用本地数据库", "evidence": [{"member": 2}]}],
            "edges": [{"id": "requires", "in": "node:local", "out": {"member": 2}, "kind": "depends",
                       "text": "决定依赖项目隔离", "evidence": [{"member": 2}]}]}

    if previous is not None:
        ids = [member["id"] for member in previous["members"]]
        for index, member in enumerate(draft["members"]):
            member["id"] = ids[index]
            if member["parent"] is not None:
                member["parent"] = ids[member["parent"]["member"]]
            member["evidence"] = [ids[value["member"]] for value in member.get("evidence", [])]
        for item in draft["nodes"] + draft["edges"]:
            item["evidence"] = [ids[value["member"]] for value in item["evidence"]]
        draft["edges"][0]["out"] = ids[2]
    return draft


@pytest.mark.parametrize("mode", ["vector", "hybrid"])
def test_publication_always_contains_matching_vectors(memory, mode):
    memory.config.raw["memory"]["search_mode"] = mode
    memory.apply(freeze([batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")]))
    rows = memory._execute("SELECT * FROM member;")[0]
    assert len(rows) == 4
    assert all(row["embedding_identity"] == EMBEDDING_IDENTITY
               and row["embedded_revision"] == row["input_revision"]
               and row["embedding"] == deterministic_vector(row["title"] + "\n" + row["text"])
               for row in rows)
    assert len(memory.embed_members()["reused"]) == 4


def test_legacy_text_mode_rejects_publication_before_database_access(tmp_path):
    password_file = tmp_path / "password.txt"
    password_file.write_text("test-password", encoding="utf-8")
    config = ProjectConfig(tmp_path / "project.toml", Path(sys.executable), tmp_path,
                           {"memory": {"search_mode": "text", "username": "root", "password_file": str(password_file)}},
                           MachineConfig(tmp_path / "machine.toml", {}))
    memory = Memory(config)
    memory._execute = lambda *args, **kwargs: pytest.fail("invalid mode touched the database")
    with pytest.raises(ValueError, match="search_mode.*(vector|hybrid)"):
        memory.apply(freeze([{"sources": []}]))


def test_real_multilevel_roundtrip_local_edit_and_correction(memory):
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    batch = freeze([batch])
    guide, storage_section, storage, retention = [row["id"] for row in batch["members"]]
    memory.apply(batch)
    hits = memory.search("数据库")
    assert {row["kind"] for row in hits} == {"file", "section", "chunk"}
    assert memory.search("项目说明")[0]["id"] == guide
    assert memory.search("本地数据库隔离项目", literal=True)[0]["id"] == storage
    assert memory.read(storage)["original"]["text"] == "本地数据库隔离项目。\n"
    assert memory.neighbors(storage)["parent"]["id"] == storage_section
    assert memory.neighbors("node:local")["edges"][0]["id"] == "semantic:requires"
    assert memory.brief("资料", limit=0)["mandatory"][0]["id"] == guide
    old = {row["id"]: row for row in memory._rows("member")}
    updated_text = "# 数据库\n数据库离线运行并隔离项目。\n\n# 保留\n资料必须保留。\n"
    (memory.config.root / "guide.md").write_bytes(updated_text.encode("utf-8"))
    assert memory.changes(["guide.md"])[0]["kind"] == "modified"
    assert {row["kind"] for row in memory.search("数据库")} == {"file", "section", "chunk"}
    assert memory.search("资料")[0]["id"] == retention
    assert memory.read(storage)["original"]["text"] == "本地数据库隔离项目。\n"
    prepared = memory.prepare(["guide.md"])
    assert "本地数据库隔离项目" in prepared["sources"][0]["previous"]["numbered_text"]
    updated = batch_for(memory, updated_text, previous=batch)
    updated["members"] = [row for row in updated["members"] if row["id"] != retention]
    updated["members"][0]["text"] = "项目数据库离线运行，资料必须保留。"
    updated["members"][1]["text"] = "数据库必须离线运行并隔离项目。"
    updated["edges"][0]["text"] = "本地决定依赖离线隔离"
    updated["corrections"] = [{"id": "fix", "target": storage, "reason": "原文增加离线条件",
                               "previous": "untrusted fabricated history"}]
    memory.apply(freeze([updated]))
    assert memory.read(storage)["original"]["text"] == "数据库离线运行并隔离项目。\n"
    after = {row["id"]: row for row in memory._rows("member")}
    assert after[retention]["input_revision"] == old[retention]["input_revision"]
    assert after[retention]["source_revision"] == old[retention]["source_revision"]
    assert after[retention]["stale"] is False
    assert all(row["stale"] is False for row in memory.search("离线"))
    correction = memory._execute("SELECT * FROM ONLY change:fix;")[0]
    assert correction["previous"]["text"] == old[storage]["text"]
    assert len(memory._rows("source_version")) == 2
    # Adding a second native edge leaves the first intact.
    memory.apply(freeze([{"sources": [], "expected": memory.prepare(["guide.md"])["expected"],
                  "edges": [{"id": "also", "in": storage, "out": retention,
                  "kind": "supports", "text": "隔离与保留共同约束存储", "evidence": [storage, retention]}]}]))
    assert {edge["id"] for edge in memory._rows("semantic")} == {"semantic:requires", "semantic:also"}
    assert memory.changes(["guide.md"], deep=True) == []


def test_real_bad_batch_rolls_back_and_project_binding_rejects(memory):
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    batch = freeze([batch])
    guide, storage_section, storage, retention = [row["id"] for row in batch["members"]]
    forged = deepcopy(batch)
    forged["members"][2]["text"] = "agent rewrote original"
    with pytest.raises(ValueError, match="differs"):
        memory.apply(forged)
    assert memory._rows("source") == []
    broken = deepcopy(batch)
    broken["edges"][0]["out"] = "member:" + uuid4().hex
    with pytest.raises(ValueError, match="Existing dependencies require prepare"):
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
    batch = freeze([batch])
    guide, storage_section, storage, retention = [row["id"] for row in batch["members"]]
    memory.apply(batch)
    (memory.config.root / "guide.md").write_bytes("# 数据库\n修改了数据库条件。\n\n# 保留\n资料必须保留。\n".encode("utf-8"))
    with pytest.raises(ValueError, match="revision mismatch"):
        memory.apply(freeze([{"sources": [], "expected": memory.prepare(["guide.md"])["expected"], "edges": batch["edges"]}]))
    memory.changes(["guide.md"])
    assert memory._rows("node")[0]["stale"] is False
    assert memory._rows("semantic")[0]["stale"] is False
    (memory.config.root / "guide.md").unlink()
    assert memory.changes(["guide.md"])[0]["kind"] == "deleted"
    assert memory.search("资料")
    brief = memory.brief(limit=0)
    assert brief["mandatory"][0]["stale"] is False
    assert brief["pending"] == []
    # The published evidence is read from its retained snapshot, even if the
    # business original is gone.
    assert memory.read(storage)["original"]["text"] == "本地数据库隔离项目。\n"
    assert len(memory._rows("source_version")) == 1
    prepared = memory.prepare(["guide.md"])["sources"][0]
    assert prepared["deleted"] is True
    assert "本地数据库隔离项目" in prepared["previous"]["numbered_text"]
    memory.apply(freeze([{"sources": [{"path": "guide.md", "revision": batch["sources"][0]["revision"], "deleted": True}]}]))
    assert memory.changes(["guide.md"]) == []
    assert memory._rows("source")[0]["deleted"] is True
    assert memory.search("资料") == []


def test_real_appended_exception_invalidates_complete_summaries(memory):
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    batch["members"].append({ "kind": "section", "path": "guide.md",
                             "parent": {"member": 0}, "start_line": 4, "end_line": 5,
                             "title": "保留政策", "text": "资料必须保留，没有例外。", "evidence": [{"member": 3}]})
    batch = freeze([batch])
    guide, storage_section, storage, retention, retention_section = [row["id"] for row in batch["members"]]
    memory.apply(batch)
    path = memory.config.root / "guide.md"
    path.write_bytes(path.read_bytes() + "但临时缓存允许删除。\n".encode("utf-8"))
    memory.changes(["guide.md"])
    rows = {row["id"]: row for row in memory._rows("member")}
    assert rows[guide]["stale"] is False
    assert rows[retention_section]["stale"] is False
    assert rows[storage]["stale"] is False
    assert rows[retention]["stale"] is False
    prepared = memory.prepare(["guide.md"])["sources"][0]
    memory.apply(freeze([{"sources": [{"path": "guide.md", "revision": prepared["revision"]}]}]))
    rows = {row["id"]: row for row in memory._rows("member")}
    assert rows[guide]["stale"] is False
    assert rows[retention_section]["stale"] is False
    assert rows[retention]["stale"] is False
    assert retention_section in {row["id"] for row in memory.search("保留")}
    partial = {"sources": [{"path": "guide.md", "revision": prepared["revision"]}],
               "expected": memory.prepare(["guide.md"])["expected"], "members": batch["members"][:1]}
    with pytest.raises(ValueError, match="Partial file summary"):
        memory.apply(freeze([partial]))


def test_real_node_correction_invalidates_relations_and_stale_draft_rejected(memory):
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    batch = freeze([batch])
    guide, storage_section, storage, retention = [row["id"] for row in batch["members"]]
    memory.apply(batch)
    draft_a = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n", previous=batch)
    draft_b = deepcopy(draft_a)
    independent_member = deepcopy(draft_a)
    draft_a["members"] = draft_a["members"][:1]
    draft_a["members"][0]["text"] = "人工更正：项目须保留资料并采用隔离数据库。"
    draft_a["nodes"][0]["text"] = "人工更正：隔离属于必须条件"
    draft_a["edges"] = []
    memory.apply(freeze([draft_a]))
    assert memory._rows("semantic")[0]["stale"] is True
    independent_member["members"] = independent_member["members"][2:3]
    independent_member["nodes"] = []
    independent_member["edges"] = []
    memory.apply(freeze([independent_member]))
    with pytest.raises(RuntimeError, match="Knowledge revision changed"):
        memory.apply(freeze([draft_b]))
    assert memory.read(guide)["member"]["text"].startswith("人工更正")
    assert memory._rows("node")[0]["text"].startswith("人工更正")
    # A separately prepared, independent new relation remains authorized by
    # source evidence; it does not require a global knowledge epoch.
    memory.apply(freeze([{"sources": [], "expected": memory.prepare(["guide.md"])["expected"],
                  "edges": [{"id": "independent", "in": storage, "out": retention,
                   "kind": "supports", "text": "两个原文条件共同约束存储", "evidence": [storage, retention]}]}]))
    fresh = memory.prepare(["guide.md"])
    memory.apply(freeze([{"sources": [], "expected": fresh["expected"], "edges": batch["edges"]}]))
    assert next(row for row in memory._rows("semantic") if row["id"] == "semantic:requires")["stale"] is False
    with pytest.raises(ValueError, match="Existing dependencies require prepare"):
        memory.apply(freeze([{"sources": [], "edges": batch["edges"]}]))


def test_real_prepare_includes_evidenced_node_edges_and_read_rejects_graph_ids(memory):
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    batch = freeze([batch])
    guide, storage_section, storage, retention = [row["id"] for row in batch["members"]]
    batch["nodes"].append({"id": "retention_policy", "kind": "condition", "text": "必须保留资料", "evidence": [retention]})
    batch["edges"].append({"id": "node_constraint", "in": "node:local", "out": "node:retention_policy",
                            "kind": "depends", "text": "存储决定受资料保留条件约束", "evidence": [storage]})
    memory.apply(batch)
    memory._execute("UPDATE semantic:node_constraint SET stale=true;")
    outside_text = "独立材料，不属于本次维护范围。\n"
    (memory.config.root / "outside.md").write_bytes(outside_text.encode("utf-8"))
    outside = memory.prepare(["outside.md"])["sources"][0]
    memory.apply(freeze([{"sources": [{"path": "outside.md", "revision": outside["revision"]}],
                  "members": [{ "kind": "chunk", "path": "outside.md", "start_line": 1,
                               "end_line": 1, "text": outside_text}],
                  "nodes": [{"id": value, "kind": "entity", "text": value, "evidence": [{"member": 0}]}
                            for value in ["outside_a", "outside_b"]],
                  "edges": [{"id": "unrelated", "in": "node:outside_a", "out": "node:outside_b", "kind": "supports",
                             "text": "独立材料的关系", "evidence": [{"member": 0}]}]}]))
    prepared = memory.prepare(["guide.md"])
    edge = next(edge for edge in prepared["neighborhood"]["edges"] if edge["id"] == "semantic:node_constraint")
    assert edge["stale"] is True
    assert prepared["expected"][edge["id"]] == edge["knowledge_revision"]
    assert "semantic:unrelated" not in {edge["id"] for edge in prepared["neighborhood"]["edges"]}
    assert "semantic:unrelated" not in prepared["expected"]
    for record_id in ["node:local", "semantic:node_constraint"]:
        with pytest.raises(ValueError, match="read requires a member ID"):
            memory.read(record_id)


def test_real_node_correction_rejects_edge_only_draft_prepared_before_invalidation(memory):
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    batch = freeze([batch])
    guide, storage_section, storage, retention = [row["id"] for row in batch["members"]]
    memory.apply(batch)
    prepared = memory.prepare(["guide.md"])
    memory.apply(freeze([{"sources": [], "expected": prepared["expected"], "nodes": [
        {"id": "local", "kind": "decision", "text": "人工更正：隔离属于必须条件", "evidence": [storage]}]}]))
    relation = memory._rows("semantic")[0]
    assert relation["stale"] is True
    assert relation["knowledge_revision"] != prepared["expected"][relation["id"]]
    with pytest.raises(RuntimeError, match="Knowledge revision changed"):
        memory.apply(freeze([{"sources": [], "expected": prepared["expected"], "edges": batch["edges"]}]))
    assert memory._rows("semantic")[0]["stale"] is True


def test_real_wrong_project_init_preserves_existing_database_schema(memory):
    memory._execute("REMOVE TABLE semantic; REMOVE TABLE node; REMOVE TABLE member; "
                    "REMOVE TABLE source_version; REMOVE TABLE source; REMOVE TABLE change; REMOVE TABLE feedback; "
                    "REMOVE TABLE knowledge_version; REMOVE TABLE access_state; REMOVE TABLE delivery; "
                    "REMOVE ANALYZER memory_zh;")
    before = memory._execute("INFO FOR DB;")[0]
    assert set(before["tables"]) == {"meta"}
    wrong = deepcopy(memory.config.raw)
    wrong["memory"]["project_id"] = "another_project"
    config = ProjectConfig(memory.config.path, memory.config.python, memory.config.root, wrong, memory.config.machine)
    with pytest.raises(RuntimeError, match="another project"):
        Memory(config).install_schema()
    assert memory._execute("INFO FOR DB;")[0] == before


def test_real_new_relations_check_used_dependencies_and_allow_unrelated_changes(memory):
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    batch = freeze([batch])
    guide, storage_section, storage, retention = [row["id"] for row in batch["members"]]
    memory.apply(batch)
    prepared = memory.prepare(["guide.md"])
    memory.apply(freeze([{"sources": [], "expected": prepared["expected"], "nodes": [
        {"id": "local", "kind": "decision", "text": "人工更正：隔离属于必须条件", "evidence": [storage]}]}]))
    drafted = {"sources": [], "expected": prepared["expected"],
               "edges": [{**batch["edges"][0], "id": "drafted_relation"}]}
    with pytest.raises(RuntimeError, match="Knowledge revision changed"):
        memory.apply(freeze([drafted]))
    assert {row["id"] for row in memory._rows("semantic")} == {"semantic:requires"}

    prepared = memory.prepare(["guide.md"])
    corrected = {**batch["members"][0], "text": "人工更正：项目必须隔离并保留资料。"}
    memory.apply(freeze([{"sources": batch["sources"], "expected": prepared["expected"], "members": [corrected]}]))
    # The changed guide is in expected, but is not used by this new relation.
    independent = {"sources": [], "expected": prepared["expected"], "edges": [
        {"id": "independent", "in": storage, "out": retention, "kind": "supports",
         "text": "两个原文条件共同约束存储", "evidence": [storage, retention]}]}
    memory.apply(freeze([independent]))
    assert next(row for row in memory._rows("semantic") if row["id"] == "semantic:independent")["stale"] is False
    with pytest.raises(RuntimeError, match="Knowledge revision changed"):
        memory.apply(freeze([{"sources": [], "expected": prepared["expected"], "nodes": [
            {"id": "stale_evidence", "kind": "condition", "text": "旧摘要形成的主张", "evidence": [guide]}]}]))
    assert "node:stale_evidence" not in {row["id"] for row in memory._rows("node")}


def test_real_prepare_includes_relation_endpoints_and_their_original_evidence(memory):
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    batch = freeze([batch])
    guide, storage_section, storage, retention = [row["id"] for row in batch["members"]]
    memory.apply(batch)
    text = "另一份存储约束。\n"
    (memory.config.root / "other.md").write_bytes(text.encode("utf-8"))
    prepared = memory.prepare(["guide.md", "other.md"])
    other = next(source for source in prepared["sources"] if source["path"] == "other.md")
    memory.apply(freeze([{"sources": [{"path": "other.md", "revision": other["revision"]}],
                  "expected": prepared["expected"],
                  "members": [{ "kind": "chunk", "path": "other.md", "start_line": 1, "end_line": 1}],
                  "edges": [{"id": "across", "in": storage, "out": {"member": 0}, "kind": "supports",
                             "text": "两份材料共同约束存储", "evidence": [storage, {"member": 0}]}]}]))
    prepared = memory.prepare(["other.md"])
    assert {row["id"] for row in prepared["neighborhood"]["members"]} >= {storage}
    assert storage in prepared["expected"]

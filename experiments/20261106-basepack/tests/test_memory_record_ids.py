"""Native record identity, vector writes, and actionable batch input failures."""

from dataclasses import replace
import os

import pytest

from basepack.memory.store import _Record, _record, _sql
from basepack.memory.draft import freeze
from basepack.project.config import load_machine_config
from test_memory_store import batch_for, memory, real_memory


@pytest.mark.parametrize(("value", "key"), [
    ("123", "123"), ("`quoted`", "`quoted`"), ("⟨quoted⟩", "⟨quoted⟩"),
    (r"literal\n", r"literal\n"), ("member:123", 123), ("member:-1", -1),
    ("member:9223372036854775807", 9223372036854775807),
    ("member:-9223372036854775808", -9223372036854775808),
    ("member:9223372036854775808", "9223372036854775808"),
    ("member:`123`", "123"), ("member:`brief-order`", "brief-order"),
    (r"member:`tick\`slash\\key`", "tick`slash\\key"),
    (r"member:`line\nnull\0tab\treturn\rform\fback\u{8}`", "line\nnull\0tab\treturn\rform\fback\b"),
    ("member:⟨brief-order⟩", "brief-order"),
])
def test_raw_string_keys_and_canonical_record_ids_keep_their_identity(value, key):
    actual = _record(value)
    assert actual == _Record("member", key)
    assert type(actual.key) is type(key)


@pytest.mark.parametrize("value", ["member:[1]", "member:{key:1}", "member:u'019f0164-940d-745b-a867-e1a9f4abecb3'"])
def test_unsupported_native_key_types_are_not_remapped_to_string_records(value):
    with pytest.raises(ValueError, match="string or integer key"):
        _record(value)


def test_real_native_emitted_escapes_decode_once(memory):
    for key in ["line\nnull\0tab\treturn\rform\fback\b", "tick`slash\\key", r"literal\n", "right⟩key", "emoji😊"]:
        canonical = memory._execute(f"RETURN {_sql(_Record('node', key))};")[0]
        assert _record(canonical) == _Record("node", key)
        assert memory._execute(f"RETURN record::id({_sql(_record(canonical))});")[0] == key


@pytest.mark.parametrize("key", [
    "plain9", "brief-order", "123", "with space", "tick`slash\\key", "part:key",
    "`quoted`", "⟨quoted⟩", r"literal\n", "line\nkey", "back\bkey",
    "9223372036854775808",
])
def test_real_canonical_graph_ids_survive_prepare_apply_evidence_and_corrections(memory, key):
    canonical = memory._execute(f"RETURN {_sql(_Record('node', key))};")[0]
    input_id = canonical if ":" in key else key
    draft = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    draft["nodes"][0].update(id=input_id, evidence=[{"member": 0}])
    draft["edges"][0].update(id="edge-order", **{"in": canonical, "out": {"member": 0}}, evidence=[{"member": 0}])
    batch = freeze([draft])
    guide, section = [item["id"] for item in batch["members"][:2]]
    memory.apply(batch)
    original = memory.read(guide)
    assert original["member"]["id"] == guide
    assert original["original"]["text"].startswith("# 数据库\n")
    assert memory.neighbors(section)["parent"]["id"] == guide
    edge = memory.neighbors(canonical)["edges"][0]
    assert edge["in"] == canonical and edge["out"] == guide
    assert edge["basis"][0]["member"] == guide
    assert memory.search("项目说明")[0]["id"] == guide

    prepared = memory.prepare(["guide.md"])
    assert guide in prepared["expected"] and canonical in prepared["expected"]
    changed = {"sources": batch["sources"], "expected": prepared["expected"],
               "members": [{**batch["members"][0], "text": "更正：隔离与保留均为必要条件。"}],
               "corrections": [{"id": "fix-order", "target": guide, "reason": "明确条件"}]}
    memory.apply(freeze([changed]))
    assert memory.read(guide)["member"]["text"].startswith("更正：")
    correction = memory._execute(f"SELECT * FROM ONLY {_sql(_Record('change', 'fix-order'))};")[0]
    assert correction["target"] == guide
    assert correction["previous"]["text"] == original["member"]["text"]
    with pytest.raises(RuntimeError, match="Knowledge revision changed"):
        memory.apply(freeze([{**changed, "corrections": []}]))


def test_real_numeric_and_string_graph_record_keys_remain_distinct(memory):
    source = memory.config.root / "numbers.md"
    source.write_text("数字身份保持区分。\n", encoding="utf-8")
    prepared = memory.prepare([source.name])
    draft = {"sources": [{"path": source.name, "revision": prepared["sources"][0]["revision"]}],
             "members": [{"kind": "chunk", "path": source.name, "start_line": 1, "end_line": 1}],
             "nodes": [{"id": value, "kind": "entity", "text": "数字身份", "evidence": [{"member": 0}]}
                       for value in ["123", "node:123"]]}
    batch = freeze([draft])
    memory.apply(batch)
    assert {row["id"] for row in memory._rows("node")} == {"node:`123`", "node:123"}
    prepared = memory.prepare([source.name])
    memory.apply(freeze([{"sources": [], "expected": prepared["expected"],
                          "delete_nodes": ["node:123", "node:`123`"]}]))
    assert all(row["retired"] for row in memory._rows("node"))


def special_id_chunks(memory):
    source = memory.config.root / "vectors.md"
    source.write_text("项目数据库保持隔离和原始依据。\n", encoding="utf-8")
    prepared = memory.prepare([source.name])
    draft = {"sources": [{"path": source.name, "revision": prepared["sources"][0]["revision"]}],
             "members": [{"kind": "chunk", "path": source.name, "start_line": 1, "end_line": 1,
                          "title": title}
                         for title in ["brief-order", "123", "with space", "tick`slash\\key", "line\nkey"]]}
    batch = freeze([draft])
    memory.apply(batch)
    return [row["id"] for row in batch["members"]]


def test_real_special_id_vector_write_reuse_and_concurrent_change(memory, monkeypatch):
    from basepack.memory import vectors
    ids = special_id_chunks(memory)
    identity = "deterministic-record-id-regression"
    monkeypatch.setattr(vectors, "status", lambda _: {"model": {"embedding_identity": identity}})

    def encode(client, inputs, *, timeout):
        return {"embedding_identity": identity, "vectors": [[1.0, 0.0] for _ in inputs]}

    monkeypatch.setattr(vectors.EmbeddingClient, "embed", encode)
    assert set(memory.embed_members(ids)["embedded"]) == set(ids)
    assert set(memory.embed_members(ids)["reused"]) == set(ids)
    assert {row["id"] for row in memory.hybrid_search("隔离", limit=10)["matches"]} == set(ids)
    memory._execute("UPDATE member SET embedding=NONE, embedded_revision=NONE;")
    target = next(row for row in memory._rows("member") if row["id"] == ids[0])

    def change_during_encode(client, inputs, *, timeout):
        memory._execute(f"UPDATE {_sql(_record(target['id']))} SET input_revision='changed-during-encoding';")
        return encode(client, inputs, timeout=timeout)

    monkeypatch.setattr(vectors.EmbeddingClient, "embed", change_during_encode)
    with pytest.raises(RuntimeError, match="Member changed while embedding"):
        memory.embed_members(ids)
    assert all(row.get("embedding") is None for row in memory._execute("SELECT embedding FROM member;")[0])


def test_real_shared_service_encodes_special_ids(real_memory):
    if "BASEPACK_MEMORY_TEST_MACHINE" not in os.environ:
        pytest.skip("requires an explicit existing shared embedding service")
    memory = real_memory
    memory.config = replace(memory.config, machine=load_machine_config(os.environ["BASEPACK_MEMORY_TEST_MACHINE"]))
    ids = special_id_chunks(memory)
    assert set(memory.embed_members(ids)["reused"]) == set(ids)
    assert set(memory.embed_members(ids)["reused"]) == set(ids)
    assert {row["id"] for row in memory.hybrid_search("项目数据库隔离", limit=10)["matches"]} == set(ids)
    assert all(memory.read(value)["original"]["text"].startswith("项目数据库") for value in ids)


@pytest.mark.parametrize("kind", ["file", "section", "chunk"])
def test_missing_text_ranges_identify_member_and_batch_position_without_writes(memory, kind):
    batch = freeze([batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")])
    batch["members"][1]["kind"] = kind
    del batch["members"][1]["start_line"], batch["members"][1]["end_line"]
    with pytest.raises(ValueError, match=rf"members\[1\].*{batch['members'][1]['id']}.*start_line.*end_line"):
        memory.apply(batch)
    assert all(memory._rows(table) == [] for table in ["source", "source_version", "member", "node", "semantic", "change"])


def test_missing_read_id_reports_the_target(memory):
    with pytest.raises(ValueError, match="Member not found: member:missing-order"):
        memory.read("member:missing-order")

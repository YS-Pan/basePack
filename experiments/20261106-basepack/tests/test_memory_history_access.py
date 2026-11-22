"""History and delivery contracts against a disposable SurrealDB server."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import sys
from uuid import uuid4

import pytest

from basepack.memory.draft import freeze
from basepack.memory.store import Memory, PublicationOutcomeUnknown, _record, _sql
from basepack.project.config import MachineConfig, ProjectConfig
from test_memory_store import EMBEDDING_IDENTITY, DeterministicEmbeddingClient, batch_for


TEXT = "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"


@pytest.fixture
def memory(tmp_path, monkeypatch):
    if "BASEPACK_MEMORY_TEST_ENDPOINT" not in os.environ:
        pytest.skip("requires an actual disposable SurrealDB server")
    from basepack.embedding import admin
    from basepack.memory import candidate_vectors, vectors

    for module in (candidate_vectors, vectors):
        monkeypatch.setattr(module, "EmbeddingClient", DeterministicEmbeddingClient)
        monkeypatch.setattr(module, "status", lambda _: {"model": {"embedding_identity": EMBEDDING_IDENTITY}})
    monkeypatch.setattr(admin, "status", lambda _: {"model": {"embedding_identity": EMBEDDING_IDENTITY}})
    database = "history_access_" + uuid4().hex
    config = ProjectConfig(tmp_path / "project.toml", Path(sys.executable), tmp_path,
                           {"memory": {"data_dir": ".basepack/memory", "search_mode": "vector",
                                       "project_id": "history_access_test",
                                       "endpoint": os.environ["BASEPACK_MEMORY_TEST_ENDPOINT"],
                                       "username": "root", "password_file": os.environ["BASEPACK_MEMORY_TEST_PASSWORD_FILE"],
                                       "namespace": os.environ.get("BASEPACK_MEMORY_TEST_NAMESPACE", "identity_tests"), "database": database}},
                           MachineConfig(tmp_path / "machine.toml", {}))
    instance = Memory(config)
    instance.install_schema()
    yield instance
    instance._execute(f"REMOVE DATABASE {database};", check_project=False)


def identity(record):
    return {"id": record["id"], "knowledge_revision": record["knowledge_revision"]}


def delivery_context():
    return {"anchors": [], "knowledge_cutoff": {}, "query": "history test", "episode": "test",
            "candidates": [], "budget": 100, "policy": {}, "model": None}


def hint(memory, record):
    return memory.access_hints([identity(record)])[0]


def test_history_preserves_exact_summary_original_and_invalidated_relation(memory):
    batch = freeze([batch_for(memory, TEXT)])
    memory.apply(batch)
    guide = batch["members"][0]["id"]
    storage = batch["members"][2]["id"]
    old_summary = memory.knowledge(guide)
    old_chunk = memory.knowledge(storage)
    old_node = memory.knowledge("node:local")
    old_edge = memory.knowledge("semantic:requires")
    old_original = memory.read(storage)["original"]

    updated = batch_for(memory, "# 数据库\n数据库离线运行并隔离项目。\n\n# 保留\n资料必须保留。\n", previous=batch)
    updated["members"][0]["text"] = "数据库必须离线运行并保留资料。"
    updated["members"][1]["text"] = "数据库必须离线运行并隔离项目。"
    # Explicitly correcting an endpoint invalidates the old relation.
    updated["nodes"][0]["text"] = "离线使用本地数据库"
    updated["edges"] = []
    updated["corrections"] = [{"id": "fix_guide", "target": guide, "reason": "增加离线条件"},
                              {"id": "fix_local", "target": "node:local", "reason": "增加离线条件"}]
    memory.apply(freeze([updated]))

    current = memory.knowledge(guide)
    assert current["knowledge_revision"] != old_summary["knowledge_revision"]
    assert memory.knowledge(guide, knowledge_revision=old_summary["knowledge_revision"])["text"] == old_summary["text"]
    historical_summary = memory.read(guide, knowledge_revision=old_summary["knowledge_revision"])
    assert historical_summary["member"]["text"] == old_summary["text"]
    assert historical_summary["original"]["source_version"] == old_summary["source_version"]
    assert historical_summary["member"]["basis"] == old_summary["basis"]
    historical = memory.read(storage, knowledge_revision=old_chunk["knowledge_revision"])
    assert historical["member"]["knowledge_revision"] == old_chunk["knowledge_revision"]
    assert historical["member"]["text"] == old_chunk["text"]
    assert historical["original"] == old_original
    assert memory.read(storage)["original"]["text"] != old_original["text"]

    history = memory.history("semantic:requires")
    assert "coverage" in history
    assert old_edge["knowledge_revision"] in {row["knowledge_revision"] for row in history["versions"]}
    edge = memory.knowledge("semantic:requires")
    assert edge["stale"] is True
    assert edge["knowledge_revision"] == old_edge["knowledge_revision"]
    assert edge["exact_id"] == old_edge["exact_id"]
    with pytest.raises(ValueError, match="Knowledge version not found"):
        memory.knowledge(guide, knowledge_revision="never-observed")
    old_graph = memory.neighbors("node:local", knowledge_revision=old_node["knowledge_revision"], include_stale=True)
    related = next(row for row in old_graph["edges"] if row["knowledge_revision"] == old_edge["knowledge_revision"])
    assert related["endpoint_versions"]["in"] == identity(old_node)
    assert related["endpoint_versions"]["out"] == identity(old_chunk)


def test_retirement_keeps_prior_member_and_dependent_edge_versions(memory):
    batch = freeze([batch_for(memory, TEXT)])
    memory.apply(batch)
    storage = batch["members"][2]["id"]
    old = memory.knowledge(storage)
    edge = memory.knowledge("semantic:requires")
    expected = memory.prepare(["guide.md"])["expected"]
    memory.apply(freeze([{"sources": [], "expected": expected, "delete_members": [storage]}]))
    retired = memory.knowledge(storage)
    assert retired["retired"] is True
    assert retired["knowledge_revision"] == old["knowledge_revision"]
    exact = memory.prepare(["guide.md"])["sources"][0]["members"]
    exact_id = next(row["exact_id"] for row in exact if row["id"] == storage)
    assert memory.knowledge(exact_id)["retired"] is False
    assert memory.knowledge("semantic:requires")["stale"] is True
    assert memory.knowledge("semantic:requires", knowledge_revision=edge["knowledge_revision"])["exact_id"] == edge["exact_id"]
    assert memory.read(storage, knowledge_revision=old["knowledge_revision"])["original"]["text"] == old["text"]


def test_legacy_change_requires_an_actual_recorded_preimage(memory):
    batch = freeze([batch_for(memory, TEXT)])
    memory.apply(batch)
    guide = batch["members"][0]["id"]
    old_member = memory.knowledge(guide)
    old_edge = memory.knowledge("semantic:requires")
    updated = batch_for(memory, "# 数据库\n数据库离线运行并隔离项目。\n\n# 保留\n资料必须保留。\n", previous=batch)
    updated["nodes"][0]["text"] = "离线使用本地数据库"
    updated["edges"] = []
    memory.apply(freeze([updated]))
    # The audit contains the member's preimage, and the relation remains
    # addressable through the native graph independent of its head archive.
    memory._execute("DELETE knowledge_version WHERE "
                    f"(target={_sql(_record(guide))} AND knowledge_revision='{old_member['knowledge_revision']}') OR "
                    f"(target=semantic:requires AND knowledge_revision='{old_edge['knowledge_revision']}');")
    restored = memory.knowledge(guide, knowledge_revision=old_member["knowledge_revision"])
    assert restored["text"] == old_member["text"]
    assert memory.read(guide, knowledge_revision=old_member["knowledge_revision"])["member"]["text"] == old_member["text"]
    assert memory.history(guide)["coverage"]["complete"] is False
    assert memory.knowledge("semantic:requires", knowledge_revision=old_edge["knowledge_revision"])["exact_id"] == old_edge["exact_id"]


def test_correction_and_retirement_preserve_one_exact_content_version(memory):
    batch = freeze([batch_for(memory, TEXT)])
    memory.apply(batch)
    storage = batch["members"][2]["id"]
    targets = (storage, "node:local", "semantic:requires")
    original = {target: memory.knowledge(target) for target in targets}
    expected = memory.prepare(["guide.md"])["expected"]
    memory.apply(freeze([{"sources": [], "expected": expected, "corrections": [
        {"id": "wrong_storage", "target": storage, "reason": "发现错误"}]}]))
    stale = {target: memory.knowledge(target) for target in targets}
    assert all(row["stale"] is True for row in stale.values())
    expected = memory.prepare(["guide.md"])["expected"]
    memory.apply(freeze([{"sources": [], "expected": expected,
                  "delete_members": [storage], "delete_nodes": ["local"], "delete_edges": ["requires"]}]))
    retired = {target: memory.knowledge(target) for target in targets}
    assert all(row["retired"] is True for row in retired.values())
    for target in targets:
        assert original[target]["knowledge_revision"] == stale[target]["knowledge_revision"] == retired[target]["knowledge_revision"]
        versions = memory.history(target)["versions"]
        assert len(versions) == 1
        assert versions[0]["retired"] is True


def test_failed_native_transaction_does_not_leave_history_or_partial_changes(memory):
    batch = freeze([batch_for(memory, TEXT)])
    memory.apply(batch)
    storage = batch["members"][2]["id"]
    targets = (storage, "node:local", "semantic:requires")
    before = {target: memory.history(target) for target in targets}
    with pytest.raises(RuntimeError):
        memory._execute("BEGIN; "
                        f"UPDATE {_sql(_record(storage))} SET knowledge_revision='rollback_member', stale=true; "
                        "UPDATE node:local SET knowledge_revision='rollback_node', stale=true; "
                        "UPDATE semantic:requires SET knowledge_revision='rollback_edge', stale=true; "
                        "THROW 'intentional rollback'; COMMIT;")
    assert {target: memory.history(target) for target in targets} == before


def test_old_delivery_never_rewards_new_version_or_related_records(memory):
    batch = freeze([batch_for(memory, TEXT)])
    memory.apply(batch)
    storage_section = batch["members"][1]["id"]
    storage = batch["members"][2]["id"]
    old = memory.knowledge(storage)
    parent = memory.knowledge(storage_section)
    memory.train_behavior()
    memory.record_delivery("pre-update", [identity(old)], context=delivery_context())
    updated = batch_for(memory, "# 数据库\n数据库离线运行并隔离项目。\n\n# 保留\n资料必须保留。\n", previous=batch)
    memory.apply(freeze([updated]))
    new = memory.knowledge(storage)
    parent = memory.knowledge(parent["id"])
    vectors = memory._execute("SELECT id, embedding, embedded_revision, input_revision FROM member ORDER BY id;")[0]
    receipt = memory.record_delivery("observed-old", [identity(old)], context=delivery_context())
    assert receipt["duplicate"] is False
    assert hint(memory, old)["access_hits"] == 2
    assert hint(memory, new)["access_hits"] == 0
    assert hint(memory, new)["access_interval"] == pytest.approx([8 / 9, 8 / 8.001])
    assert hint(memory, parent)["access_hits"] == 0
    assert memory._execute("SELECT id, embedding, embedded_revision, input_revision FROM member ORDER BY id;")[0] == vectors


def test_delivery_is_idempotent_and_empty_delivery_does_not_advance(memory):
    batch = freeze([batch_for(memory, TEXT)])
    memory.apply(batch)
    storage = batch["members"][2]["id"]
    retention = batch["members"][3]["id"]
    one = memory.knowledge(storage)
    two = memory.knowledge(retention)
    item = identity(one)
    memory.train_behavior()
    first = memory.record_delivery("stable-id", [item], context=delivery_context())
    duplicate = memory.record_delivery("stable-id", [item], context=delivery_context())
    assert duplicate["duplicate"] is True
    assert duplicate["j"] == first["j"]
    assert hint(memory, one)["access_hits"] == 1
    with pytest.raises(ValueError):
        memory.record_delivery("stable-id", [identity(two)], context=delivery_context())
    empty = memory.record_delivery("empty", [], context=delivery_context())
    assert memory.record_delivery("empty", [], context=delivery_context())["duplicate"] is True
    later = memory.record_delivery("next", [identity(two)], context=delivery_context())
    assert empty["j"] == first["j"] + 1
    assert later["j"] == first["j"] + 2
    assert later["projection"]["c"] == 2
    assert hint(memory, one)["access_hits"] == 1
    assert hint(memory, two)["access_hits"] == 1
    usage = memory.history(one["id"])
    assert usage["current_knowledge_revision"] == one["knowledge_revision"]
    assert usage["delivery_count"] == 1
    assert usage["delivery_limit"] == 20
    assert usage["deliveries"][0]["delivery_id"] == "stable-id"
    assert usage["deliveries"][0]["items"] == [item]


def test_delivery_recovers_only_when_a_lost_response_has_a_receipt(memory, monkeypatch):
    batch = freeze([batch_for(memory, TEXT)])
    memory.apply(batch)
    storage = batch["members"][2]["id"]
    item = identity(memory.knowledge(storage))
    memory.train_behavior()
    execute = memory._execute
    fail_after_commit = True

    def lost_response(sql, **kwargs):
        nonlocal fail_after_commit
        if fail_after_commit and 'CREATE type::record("delivery",' in sql:
            fail_after_commit = False
            execute(sql, **kwargs)
            raise ConnectionError("response lost after commit")
        return execute(sql, **kwargs)

    monkeypatch.setattr(memory, "_execute", lost_response)
    receipt = memory.record_delivery("lost-response", [item], context=delivery_context())
    assert receipt["duplicate"] is True
    assert memory.record_delivery("lost-response", [item], context=delivery_context())["j"] == receipt["j"]
    assert hint(memory, item)["access_hits"] == 1

    def lost_before_commit(sql, **kwargs):
        if 'CREATE type::record("delivery",' in sql:
            raise ConnectionError("connection lost before commit")
        return execute(sql, **kwargs)

    monkeypatch.setattr(memory, "_execute", lost_before_commit)
    with pytest.raises(PublicationOutcomeUnknown, match="no-receipt") as uncertain:
        memory.record_delivery("no-receipt", [item], context=delivery_context())
    assert isinstance(uncertain.value.__cause__, ConnectionError)
    monkeypatch.setattr(memory, "_execute", execute)
    assert hint(memory, item)["access_hits"] == 1
    recovered = memory.record_delivery("no-receipt", [item], context=delivery_context())
    assert recovered["duplicate"] is False
    assert recovered["j"] == receipt["j"] + 1
    assert hint(memory, item)["access_hits"] == 2


def test_reads_do_not_count_as_delivery(memory):
    batch = freeze([batch_for(memory, TEXT)])
    memory.apply(batch)
    storage = batch["members"][2]["id"]
    memory.train_behavior()
    record = memory.knowledge(storage)
    memory.record_delivery("observed", [identity(record)], context=delivery_context())
    before = hint(memory, record)
    memory.search("数据库")
    memory.read(storage)
    memory.neighbors(storage)
    assert hint(memory, record) == before
    assert before["access_hits"] == 1
    assert before["access_interval"] == [1.0, 1.0]


def test_concurrent_deliveries_are_atomic_and_same_id_is_deduplicated(memory):
    batch = freeze([batch_for(memory, TEXT)])
    memory.apply(batch)
    storage = batch["members"][2]["id"]
    item = identity(memory.knowledge(storage))
    memory.train_behavior()
    with ThreadPoolExecutor(max_workers=4) as executor:
        receipts = list(executor.map(lambda i: memory.record_delivery(f"parallel-{i}", [item], context=delivery_context()), range(4)))
    assert len({receipt["j"] for receipt in receipts}) == 4
    assert hint(memory, item)["access_hits"] == 4
    with ThreadPoolExecutor(max_workers=4) as executor:
        duplicates = list(executor.map(lambda _: memory.record_delivery("same-parallel", [item], context=delivery_context()), range(4)))
    assert sum(not receipt["duplicate"] for receipt in duplicates) == 1
    assert len({receipt["j"] for receipt in duplicates}) == 1
    assert hint(memory, item)["access_hits"] == 5

"""History and delivery contracts against a disposable SurrealDB server."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import sys
from uuid import uuid4

import pytest

from basepack.memory.store import Memory, PublicationOutcomeUnknown
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
                                       "namespace": "memsys", "database": database}},
                           MachineConfig(tmp_path / "machine.toml", {}))
    instance = Memory(config)
    instance.install_schema()
    yield instance
    instance._execute(f"REMOVE DATABASE {database};", check_project=False)


def identity(record):
    return {"id": record["id"], "knowledge_revision": record["knowledge_revision"]}


def hint(memory, record):
    return memory.access_hints([identity(record)])[0]


def test_history_preserves_exact_summary_original_and_invalidated_relation(memory):
    memory.apply(batch_for(memory, TEXT))
    old_summary = memory.knowledge("member:guide")
    old_chunk = memory.knowledge("member:storage")
    old_node = memory.knowledge("node:local")
    old_edge = memory.knowledge("semantic:requires")
    old_original = memory.read("member:storage")["original"]

    updated = batch_for(memory, "# 数据库\n数据库离线运行并隔离项目。\n\n# 保留\n资料必须保留。\n")
    updated["members"][0]["text"] = "数据库必须离线运行并保留资料。"
    updated["members"][1]["text"] = "数据库必须离线运行并隔离项目。"
    # Replacing a node invalidates the old edge without accepting a new edge.
    updated["nodes"][0]["text"] = "离线使用本地数据库"
    updated["edges"] = []
    updated["corrections"] = [{"id": "fix_guide", "target": "member:guide", "reason": "增加离线条件"}]
    memory.apply(updated)

    current = memory.knowledge("member:guide")
    assert current["knowledge_revision"] != old_summary["knowledge_revision"]
    assert memory.knowledge("member:guide", knowledge_revision=old_summary["knowledge_revision"])["text"] == old_summary["text"]
    historical_summary = memory.read("member:guide", knowledge_revision=old_summary["knowledge_revision"])
    assert historical_summary["member"]["text"] == old_summary["text"]
    assert historical_summary["original"]["source_version"] == old_summary["source_version"]
    assert historical_summary["member"]["basis"] == old_summary["basis"]
    historical = memory.read("member:storage", knowledge_revision=old_chunk["knowledge_revision"])
    assert historical["member"]["knowledge_revision"] == old_chunk["knowledge_revision"]
    assert historical["member"]["text"] == old_chunk["text"]
    assert historical["original"] == old_original
    assert memory.read("member:storage")["original"]["text"] != old_original["text"]

    history = memory.history("semantic:requires")
    assert "coverage" in history
    assert old_edge["knowledge_revision"] in {row["knowledge_revision"] for row in history["versions"]}
    edge = memory.knowledge("semantic:requires")
    assert edge["stale"] is True
    assert edge["knowledge_revision"] != old_edge["knowledge_revision"]
    assert memory.knowledge("semantic:requires", knowledge_revision=old_edge["knowledge_revision"])["stale"] is False
    with pytest.raises(ValueError, match="Knowledge version not found"):
        memory.knowledge("member:guide", knowledge_revision="never-observed")
    old_graph = memory.neighbors("node:local", knowledge_revision=old_node["knowledge_revision"], include_stale=True)
    related = next(row for row in old_graph["edges"] if row["knowledge_revision"] == old_edge["knowledge_revision"])
    assert related["endpoint_versions"]["in"] == identity(old_node)
    assert related["endpoint_versions"]["out"] == identity(old_chunk)


def test_retirement_keeps_prior_member_and_dependent_edge_versions(memory):
    memory.apply(batch_for(memory, TEXT))
    old = memory.knowledge("member:storage")
    edge = memory.knowledge("semantic:requires")
    expected = memory.prepare(["guide.md"])["expected"]
    memory.apply({"sources": [], "expected": expected, "delete_members": ["storage"]})
    retired = memory.knowledge("member:storage")
    assert retired["retired"] is True
    assert retired["knowledge_revision"] != old["knowledge_revision"]
    assert memory.knowledge("member:storage", knowledge_revision=old["knowledge_revision"])["retired"] is False
    assert memory.knowledge("semantic:requires")["stale"] is True
    assert memory.knowledge("semantic:requires", knowledge_revision=edge["knowledge_revision"])["stale"] is False
    assert memory.read("member:storage", knowledge_revision=old["knowledge_revision"])["original"]["text"] == old["text"]


def test_legacy_change_requires_an_actual_recorded_preimage(memory):
    memory.apply(batch_for(memory, TEXT))
    old_member = memory.knowledge("member:guide")
    old_edge = memory.knowledge("semantic:requires")
    updated = batch_for(memory, "# 数据库\n数据库离线运行并隔离项目。\n\n# 保留\n资料必须保留。\n")
    updated["nodes"][0]["text"] = "离线使用本地数据库"
    updated["edges"] = []
    memory.apply(updated)
    # Recreate a pre-history-installation gap: change has the member's exact
    # previous record, but the old implicit edge invalidation had no preimage.
    memory._execute("DELETE knowledge_version WHERE "
                    f"(target=member:guide AND knowledge_revision='{old_member['knowledge_revision']}') OR "
                    f"(target=semantic:requires AND knowledge_revision='{old_edge['knowledge_revision']}');")
    restored = memory.knowledge("member:guide", knowledge_revision=old_member["knowledge_revision"])
    assert restored["text"] == old_member["text"]
    assert memory.read("member:guide", knowledge_revision=old_member["knowledge_revision"])["member"]["text"] == old_member["text"]
    assert memory.history("member:guide")["coverage"]["complete"] is False
    with pytest.raises(ValueError, match="Knowledge version not found"):
        memory.knowledge("semantic:requires", knowledge_revision=old_edge["knowledge_revision"])


def test_legacy_install_records_birth_before_future_deliveries_and_is_idempotent(memory):
    memory.apply(batch_for(memory, TEXT))
    old = memory.knowledge("member:storage")
    other = memory.knowledge("member:retention")
    # Simulate a database created before knowledge_version existed.
    memory._execute("DELETE knowledge_version;")
    memory.install_schema()
    assert hint(memory, old)["access_event"] == 0
    memory.record_delivery("other-delivered", [identity(other)])
    before_update = hint(memory, old)
    assert before_update["access_hits"] == 0
    assert before_update["access_weight"] == pytest.approx(8 / 9)

    updated = batch_for(memory, "# 数据库\n数据库离线运行并隔离项目。\n\n# 保留\n资料必须保留。\n")
    memory.apply(updated)
    new = memory.knowledge("member:storage")
    assert new["knowledge_revision"] != old["knowledge_revision"]
    assert hint(memory, old)["access_weight"] == pytest.approx(before_update["access_weight"])
    assert hint(memory, old)["access_event"] == before_update["access_event"]
    assert hint(memory, new)["access_hits"] == 0
    assert hint(memory, new)["access_weight"] == 1
    old_state, new_state, other_state = (hint(memory, row) for row in (old, new, other))
    memory.install_schema()
    assert [hint(memory, row) for row in (old, new, other)] == [old_state, new_state, other_state]


def test_intermediate_stale_and_retired_versions_are_addressable(memory):
    memory.apply(batch_for(memory, TEXT))
    targets = ("member:storage", "node:local", "semantic:requires")
    original = {target: memory.knowledge(target) for target in targets}
    expected = memory.prepare(["guide.md"])["expected"]
    memory.apply({"sources": [], "expected": expected, "corrections": [
        {"id": "wrong_storage", "target": "member:storage", "reason": "发现错误"}]})
    stale = {target: memory.knowledge(target) for target in targets}
    assert all(row["stale"] is True for row in stale.values())
    expected = memory.prepare(["guide.md"])["expected"]
    memory.apply({"sources": [], "expected": expected,
                  "delete_members": ["storage"], "delete_nodes": ["local"], "delete_edges": ["requires"]})
    retired = {target: memory.knowledge(target) for target in targets}
    assert all(row["retired"] is True for row in retired.values())
    for target in targets:
        assert len({original[target]["knowledge_revision"], stale[target]["knowledge_revision"],
                    retired[target]["knowledge_revision"]}) == 3
        versions = {row["knowledge_revision"]: row for row in memory.history(target)["versions"]}
        assert versions[original[target]["knowledge_revision"]]["stale"] is False
        assert versions[stale[target]["knowledge_revision"]]["stale"] is True
        assert versions[stale[target]["knowledge_revision"]]["retired"] is False
        assert versions[retired[target]["knowledge_revision"]]["retired"] is True


def test_failed_native_transaction_does_not_leave_history_or_partial_changes(memory):
    memory.apply(batch_for(memory, TEXT))
    targets = ("member:storage", "node:local", "semantic:requires")
    before = {target: memory.history(target) for target in targets}
    with pytest.raises(RuntimeError):
        memory._execute("BEGIN; "
                        "UPDATE member:storage SET knowledge_revision='rollback_member', stale=true; "
                        "UPDATE node:local SET knowledge_revision='rollback_node', stale=true; "
                        "UPDATE semantic:requires SET knowledge_revision='rollback_edge', stale=true; "
                        "THROW 'intentional rollback'; COMMIT;")
    assert {target: memory.history(target) for target in targets} == before


def test_old_delivery_never_rewards_new_version_or_related_records(memory):
    memory.apply(batch_for(memory, TEXT))
    old = memory.knowledge("member:storage")
    parent = memory.knowledge("member:storage_section")
    memory.record_delivery("pre-update", [identity(old)])
    updated = batch_for(memory, "# 数据库\n数据库离线运行并隔离项目。\n\n# 保留\n资料必须保留。\n")
    memory.apply(updated)
    new = memory.knowledge("member:storage")
    parent = memory.knowledge(parent["id"])
    vectors = memory._execute("SELECT id, embedding, embedded_revision, input_revision FROM member ORDER BY id;")[0]
    receipt = memory.record_delivery("observed-old", [identity(old)], context={"test": "history"})
    assert receipt["duplicate"] is False
    assert hint(memory, old)["access_hits"] == 2
    assert hint(memory, new)["access_hits"] == 0
    assert hint(memory, new)["access_weight"] == pytest.approx(8 / 9)
    assert hint(memory, parent)["access_hits"] == 0
    assert memory._execute("SELECT id, embedding, embedded_revision, input_revision FROM member ORDER BY id;")[0] == vectors


def test_delivery_is_idempotent_and_empty_delivery_does_not_advance(memory):
    memory.apply(batch_for(memory, TEXT))
    one = memory.knowledge("member:storage")
    two = memory.knowledge("member:retention")
    item = identity(one)
    first = memory.record_delivery("stable-id", [item])
    duplicate = memory.record_delivery("stable-id", [item])
    assert duplicate["duplicate"] is True
    assert duplicate["event"] == first["event"]
    assert hint(memory, one)["access_hits"] == 1
    with pytest.raises(ValueError):
        memory.record_delivery("stable-id", [identity(two)])
    empty = memory.record_delivery("empty", [])
    assert memory.record_delivery("empty", [])["duplicate"] is True
    later = memory.record_delivery("next", [identity(two)])
    assert later["event"] == first["event"] + 1
    assert hint(memory, one)["access_hits"] == 1
    assert hint(memory, two)["access_hits"] == 1
    usage = memory.history(one["id"])
    assert usage["current_knowledge_revision"] == one["knowledge_revision"]
    assert usage["delivery_count"] == 1
    assert usage["delivery_limit"] == 20
    assert usage["deliveries"][0]["delivery_id"] == "stable-id"
    assert usage["deliveries"][0]["items"] == [item]


def test_delivery_recovers_only_when_a_lost_response_has_a_receipt(memory, monkeypatch):
    memory.apply(batch_for(memory, TEXT))
    item = identity(memory.knowledge("member:storage"))
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
    receipt = memory.record_delivery("lost-response", [item])
    assert receipt["duplicate"] is True
    assert memory.record_delivery("lost-response", [item])["event"] == receipt["event"]
    assert hint(memory, item)["access_hits"] == 1

    def lost_before_commit(sql, **kwargs):
        if 'CREATE type::record("delivery",' in sql:
            raise ConnectionError("connection lost before commit")
        return execute(sql, **kwargs)

    monkeypatch.setattr(memory, "_execute", lost_before_commit)
    with pytest.raises(PublicationOutcomeUnknown, match="no-receipt") as uncertain:
        memory.record_delivery("no-receipt", [item])
    assert isinstance(uncertain.value.__cause__, ConnectionError)
    monkeypatch.setattr(memory, "_execute", execute)
    assert hint(memory, item)["access_hits"] == 1
    recovered = memory.record_delivery("no-receipt", [item])
    assert recovered["duplicate"] is False
    assert recovered["event"] == receipt["event"] + 1
    assert hint(memory, item)["access_hits"] == 2


def test_lazy_weights_match_full_event_reference_and_reads_do_not_count(memory):
    memory.apply(batch_for(memory, TEXT))
    records = [memory.knowledge("member:storage"), memory.knowledge("member:retention"),
               memory.knowledge("member:guide")]
    hits = [0, 0, 0]
    last = [0, 0, 0]
    eager_weights = [1.0, 1.0, 1.0]
    order = [0, 1, 0, 2, 1, 0, 0, 2, 1, 2, 2, 0]
    for event, chosen in enumerate(order, 1):
        eager_weights = [weight / (1 + weight / (8 * (1 + hit)))
                         for weight, hit in zip(eager_weights, hits, strict=True)]
        memory.record_delivery(f"event-{event}", [identity(records[chosen])])
        hits[chosen] += 1
        last[chosen] = event
        eager_weights[chosen] = 1.0
        supplied = [{**identity(record), "marker": i} for i, record in enumerate(records)]
        result = memory.access_hints(supplied)
        assert [row["id"] for row in result] == [record["id"] for record in records]
        assert [row["marker"] for row in result] == list(range(len(records)))
        for i, row in enumerate(result):
            assert row["access_hits"] == hits[i]
            assert row["access_event"] == last[i]
            assert row["access_weight"] == pytest.approx(eager_weights[i])
    before = memory.access_hints([identity(record) for record in records])
    memory.search("数据库")
    memory.read("member:storage")
    memory.neighbors("member:storage")
    assert memory.access_hints([identity(record) for record in records]) == before


def test_concurrent_deliveries_are_atomic_and_same_id_is_deduplicated(memory):
    memory.apply(batch_for(memory, TEXT))
    item = identity(memory.knowledge("member:storage"))
    with ThreadPoolExecutor(max_workers=4) as executor:
        receipts = list(executor.map(lambda i: memory.record_delivery(f"parallel-{i}", [item]), range(4)))
    assert len({receipt["event"] for receipt in receipts}) == 4
    assert hint(memory, item)["access_hits"] == 4
    with ThreadPoolExecutor(max_workers=4) as executor:
        duplicates = list(executor.map(lambda _: memory.record_delivery("same-parallel", [item]), range(4)))
    assert sum(not receipt["duplicate"] for receipt in duplicates) == 1
    assert len({receipt["event"] for receipt in duplicates}) == 1
    assert hint(memory, item)["access_hits"] == 5

"""Projection and strict delivery facts against a disposable database."""
from unittest.mock import patch

import pytest

from test_memory_history_access import memory
from basepack.memory.behavior_projection import _snapshot, compile_behavior, train_behavior


def ctx(anchors=()):
    return {"anchors": list(anchors), "knowledge_cutoff": {}, "query": "q", "episode": "e",
            "candidates": [], "budget": 20, "policy": {}, "model": None}


def test_incremental_snapshot_uses_both_cursor_indexes(memory):
    memory._execute("CREATE meta:behavior SET active='test',j=2; UPDATE meta:delivery SET j=3; "
                    "CREATE behavior_projection:test SET j=2; "
                    "CREATE knowledge_version:older SET j_enter=1; CREATE knowledge_version:current SET j_enter=2; "
                    "CREATE knowledge_version:newer SET j_enter=3; "
                    "CREATE delivery:current SET j=2; CREATE delivery:newer SET j=3;")
    with patch.object(memory, "_execute", wraps=memory._execute) as execute:
        active, head, projections, _, _, versions, events = _snapshot(memory)
    assert active["j"] == projections[0]["j"] == 2 and head["j"] == 3
    assert {row["j_enter"] for row in versions} == {2, 3}
    assert [row["j"] for row in events] == [3]

    query = execute.call_args_list[0].args[0]
    explained = query.replace("SELECT target,knowledge_revision,j_enter", "EXPLAIN SELECT target,knowledge_revision,j_enter")
    explained = explained.replace("SELECT * FROM delivery WHERE", "EXPLAIN SELECT * FROM delivery WHERE")
    versions_plan, events_plan = memory._execute(explained)[-3:-1]
    assert "IndexScan" in versions_plan and "knowledge_j_enter" in versions_plan
    assert "IndexScan" in events_plan and "delivery_j" in events_plan


def test_delivery_projection_replay_and_version_isolation(memory, monkeypatch):
    memory._execute("CREATE member:a SET knowledge_revision='a1'; CREATE member:b SET knowledge_revision='b1';")
    a = {"id": "member:a", "knowledge_revision": "a1"}
    b = {"id": "member:b", "knowledge_revision": "b1"}
    first = memory.record_delivery("first", [a, b], context=ctx())
    empty = memory.record_delivery("empty", [], context=ctx())
    assert (first["j"], empty["j"]) == (1, 2)
    assert memory.record_delivery("empty", [], context=ctx())["j"] == 2
    with pytest.raises(ValueError, match="different content"):
        memory.record_delivery("empty", [], context={**ctx(), "query": "different"})
    trained = train_behavior(memory)
    assert trained["compiled_j"] == 2 and trained["c"] == 1
    from basepack.memory.behavior_projection import behavior_candidates
    related = behavior_candidates(memory, [{**a, "alpha": 1.0}], limit=10)
    assert {row["id"] for row in related["candidates"]} == {"member:a", "member:b"}
    assert all(len(row["behavior_similarity_interval"]) == 2 for row in related["candidates"])
    old = memory.access_hints([a, b])
    assert [row["access_hits"] for row in old] == [1, 1]
    anchor = {**a, "alpha": 1.0, "base_quality": 1.0}
    import basepack.memory.behavior_projection as projection
    original_compile = projection.compile_behavior
    def fail_compile(_):
        raise RuntimeError("projection failed")
    monkeypatch.setattr(projection, "compile_behavior", fail_compile)
    with pytest.raises(RuntimeError, match="projection failed"):
        memory.record_delivery("third", [a], context=ctx([anchor]))
    monkeypatch.setattr(projection, "compile_behavior", original_compile)
    lagging = memory.access_hints([b])[0]
    assert lagging["access_status"] == "lagging" and lagging["access_fact_j"] == 3
    compile_behavior(memory)
    after = memory.access_hints([a, b])
    assert after[0]["access_hits"] == 2
    assert after[0]["access_interval"] == [1.0, 1.0]
    assert after[1]["access_interval"][1] < 1
    memory._execute("UPDATE member:a SET knowledge_revision='a2';")
    compile_behavior(memory)
    new = memory.access_hints([{"id": "member:a", "knowledge_revision": "a2"}])[0]
    assert new["access_hits"] == 0 and new["access_interval"] == [1.0, 1.0]
    train_behavior(memory)
    assert memory.access_hints([b])[0]["access_interval"] == pytest.approx(after[1]["access_interval"])


def test_legacy_observation_origin_and_late_model_delivery(memory):
    memory._execute("CREATE member:a SET knowledge_revision='a1'; "
                    "CREATE member:b SET knowledge_revision='b1'; "
                    "UPDATE knowledge_version SET j_enter=NULL,observed_j=0,age_origin='legacy_cutover'; "
                    "CREATE delivery:legacy SET delivery_id='old',legacy=true,legacy_event=1,j=NULL,context=NULL, "
                    "items=[{id:'member:a',knowledge_revision:'a1'}];")
    a = {"id": "member:a", "knowledge_revision": "a1"}
    b = {"id": "member:b", "knowledge_revision": "b1"}
    old_model = train_behavior(memory)["model"]
    a_before, b_before = memory.access_hints([a, b])
    assert a_before["access_hits"] == 1
    assert b_before["access_hits"] == 0 and b_before["access_age_origin"] == "legacy_cutover"
    memory.record_delivery("new", [a], context={**ctx(), "model": old_model})
    b_after = memory.access_hints([b])[0]
    assert b_after["access_interval"][0] < 1
    new_model = train_behavior(memory)["model"]
    assert new_model != old_model
    assert memory.access_hints([b])[0]["access_interval"] == pytest.approx(b_after["access_interval"])
    memory.record_delivery("late", [b], context={**ctx(), "model": old_model})
    history = memory.history("member:a")
    assert [row["delivery_id"] for row in history["deliveries"]] == ["new", "old"]
    assert history["deliveries"][0]["j"] == 1
    assert history["deliveries"][1]["legacy_event"] == 1
    assert history["legacy_order"] == "event_only_ties_unknown"
    b_late = memory.access_hints([b])[0]
    assert b_late["access_model"] == new_model and b_late["access_hits"] == 1
    assert b_late["access_interval"] == [1.0, 1.0]


def test_concurrent_duplicate_fact_is_single_event(memory):
    from concurrent.futures import ThreadPoolExecutor
    memory._execute("CREATE member:a SET knowledge_revision='a1';")
    a = {"id": "member:a", "knowledge_revision": "a1"}
    train_behavior(memory)
    with ThreadPoolExecutor(max_workers=4) as pool:
        receipts = list(pool.map(lambda _: memory.record_delivery("same", [a], context=ctx()), range(4)))
    assert sum(not row["duplicate"] for row in receipts) == 1
    assert {row["j"] for row in receipts} == {1}
    assert memory.access_hints([a])[0]["access_hits"] == 1

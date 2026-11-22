"""Archival relation reads retain observed fields without creating graph topology."""

from types import SimpleNamespace
from unittest.mock import Mock

from basepack.memory.history import history, knowledge, semantic_rows


def test_legacy_relationship_remains_available_for_precise_history_only():
    target = "semantic:rule"
    original = {"id": target, "knowledge_revision": "v1", "kind": "supports", "text": "Original relation",
                "stale": False, "retired": False, "private": False, "in": "member:a", "out": "member:b",
                "endpoint_versions": {"in": {"id": "member:a", "knowledge_revision": "observed"}}}
    archive = {"record": original, "legacy_reason": "incomplete_endpoint_pins"}
    archived = {**original, "legacy_history_only": True, "legacy_reason": archive["legacy_reason"]}
    head = {"id": target, "knowledge_revision": "v1", "stale": True, "retired": False, "legacy_history_only": True}
    memory = SimpleNamespace(_execute=Mock(side_effect=[
        [[]],
        [[]], [[archive]],
        [[]], [head], [[archive]],
        [{"target": target, "id": "knowledge_version:old", "knowledge_revision": "v1",
          "legacy_history_only": True, **archive}],
    ]))

    assert semantic_rows(memory, [target]) == []
    assert knowledge(memory, target, knowledge_revision="v1") == archived
    assert knowledge(memory, target) == {**archived, "stale": True}
    assert knowledge(memory, "knowledge_version:old") == archived
    assert original["stale"] is False


def test_relationship_history_merges_native_and_archived_versions():
    target = "semantic:rule"
    archived = {"record": {"id": target, "knowledge_revision": "unknown", "text": "Original wording"},
                "legacy_reason": "incomplete_endpoint_pins"}
    current = {"id": target, "knowledge_revision": "unknown", "stale": True, "retired": False,
               "legacy_history_only": True}
    native = {"id": "graph_edge:verified", "logical_id": target, "knowledge_revision": "verified",
              "type": "supports", "in": "knowledge_version:a", "out": "knowledge_version:b",
              "text": "Verified wording", "conditions": "", "scope_paths": [], "private": False,
              "status": "historical"}
    memory = SimpleNamespace(_execute=Mock(side_effect=[
        [current, [archived], [], [{"delivery_id": "seen"}], [], [{"count": 1}]], [[native]], [[]],
    ]))

    result = history(memory, target)
    assert result["current_knowledge_revision"] == "unknown"
    assert result["deliveries"] == [{"delivery_id": "seen"}]
    assert result["delivery_count"] == 1
    v1, v2 = result["versions"]
    assert v1["exact_id"] == native["id"]
    assert v2 == {**archived["record"], "stale": True, "retired": False, "legacy_history_only": True,
                  "private": True, "privacy_unknown": True,
                  "legacy_reason": archived["legacy_reason"]}

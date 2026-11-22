"""Schema 3 conversion and rollback on a disposable native database."""

import pytest

from basepack.memory.graph_upgrade import _Schema3Publication, upgrade
from basepack.memory.store import _digest, _record, _sql
from test_memory_store import memory


def _restore_old_fixture(memory):
    """Use the schema 3 layout with exact versions available only as preimages."""
    parent = _record("member:overview")
    current = _record("member:claim")
    logical = _record("source:guide")
    old_snapshot = _record("source_version:old")
    new_snapshot = _record("source_version:new")
    old_text = "Original fixture claim.\n"
    new_text = "Revised fixture claim.\n"
    parent_record = {"knowledge_revision": "parent_now", "text": new_text,
                     "path": "guide.txt", "source": logical, "source_version": new_snapshot,
                     "start_line": 1, "end_line": 1, "kind": "file", "private": False,
                     "stale": False, "retired": False, "basis": []}
    current_record = {**parent_record, "knowledge_revision": "claim_now", "kind": "chunk", "parent": parent}
    old_record = {**current_record, "id": current, "knowledge_revision": "claim_before",
                  "text": old_text, "source_version": old_snapshot, "raw_revision": _digest(old_text)}
    basis = {"member": current, "knowledge_revision": "claim_before", "source_version": old_snapshot,
             "start_line": 1, "end_line": 1}
    initial = [
        "REMOVE TABLE graph_edge;",
        "REMOVE TABLE graph_state;",
        "REMOVE TABLE semantic;",
        "REMOVE EVENT retain_member_version ON member;",
        "DEFINE TABLE semantic TYPE RELATION IN member|node OUT member|node ENFORCED SCHEMALESS;",
        "UPDATE meta:project SET memory_schema_version=3;",
        "UPDATE meta:delivery SET j=1;",
        f"CREATE {_sql(logical)} CONTENT {_sql({'path': 'guide.txt', 'version': new_snapshot, 'deleted': False})};",
        f"CREATE {_sql(parent)} CONTENT {_sql(parent_record)};",
        f"CREATE {_sql(current)} CONTENT {_sql(current_record)};",
        f"CREATE change:preimage SET operation='accept', previous={_sql(old_record)};",
        f"CREATE delivery:fact SET j=1, items={_sql([{'id': 'member:claim', 'knowledge_revision': 'claim_before'}])};",
    ]
    for version, text in ((old_snapshot, old_text), (new_snapshot, new_text)):
        value = {"text": text, "source": logical, "revision": _digest(text), "kind": "text",
                 "path": "guide.txt"}
        if version == new_snapshot:
            value["private"] = False
        initial.append(f"CREATE {_sql(version)} CONTENT {_sql(value)};")
    relation = {"kind": "depends", "text": "The overview depends on the historic claim.", "conditions": "",
                "knowledge_revision": "edge_before", "private": False, "stale": False, "retired": False,
                "basis": [basis],
                "endpoint_versions": {"in": {"id": parent, "knowledge_revision": "parent_now"},
                                      "out": {"id": current, "knowledge_revision": "claim_before"}}}
    partial = {**relation, "knowledge_revision": "partial",
               "endpoint_versions": {"in": relation["endpoint_versions"]["in"]}}
    for name, row in (("exact", relation), ("partial", partial)):
        initial.append(f"RELATE member:overview->semantic:{name}->member:claim CONTENT {_sql(row)};")
    memory._execute(" ".join(initial), check_project=False)


def test_graph_upgrade_rolls_back_then_reuses_exact_preimages(memory, monkeypatch):
    _restore_old_fixture(memory)
    decisions = [{"id": "semantic:exact", "knowledge_revision": "edge_before",
                  "legacy_kind": "depends", "type": "requires"}]
    source_digest = _digest("fixture")
    old = memory._execute("SELECT * FROM semantic ORDER BY id; INFO FOR DB;", check_project=False)
    publish = _Schema3Publication._publish

    def fail_after_writes(self, statements):
        return publish(self, [*statements[:-1], "THROW 'failed upgrade';", statements[-1]])

    with monkeypatch.context() as failure:
        failure.setattr(_Schema3Publication, "_publish", fail_after_writes)
        with pytest.raises(RuntimeError, match="failed upgrade"):
            upgrade(memory, source_sha256=source_digest, relations=decisions)
    assert memory._execute("SELECT * FROM semantic ORDER BY id; INFO FOR DB;", check_project=False) == old
    assert memory._execute("SELECT VALUE memory_schema_version FROM ONLY meta:project;", check_project=False)[0] == 3

    report = upgrade(memory, source_sha256=source_digest, relations=decisions)
    assert report["counts"]["converted_relations"] == 1
    assert report["reference_gaps"] == []
    assert report["archived_relations"][0]["known_endpoint_versions"] == {
        "in": {"id": "member:overview", "knowledge_revision": "parent_now"}}
    assert upgrade(memory, source_sha256=source_digest, relations=decisions) == report
    read = memory.read("member:claim", knowledge_revision="claim_before")
    assert read["original"]["text"] == "Original fixture claim.\n"
    assert read["member"]["private"] and read["original"]["private"]
    exact = memory._execute(
        "SELECT id, record.private AS old_private FROM ONLY (fn::knowledge_id(member:claim, 'claim_before'));")[0]
    assert exact["old_private"] is False
    assert memory.knowledge(exact["id"])["private"] is True
    history = memory.history("member:claim")["versions"]
    assert next(row for row in history if row["knowledge_revision"] == "claim_before")["private"] is True
    assert memory._execute("SELECT VALUE privacy_unknown FROM ONLY source_version:old;")[0] is True
    assert memory.neighbors("member:claim", knowledge_revision="claim_before", allow_private=False)["record"] is None
    assert memory.knowledge("semantic:exact")["out"] == "member:claim"
    archive = memory.knowledge("semantic:partial", knowledge_revision="partial")
    assert archive["legacy_history_only"] and "out" not in archive["endpoint_versions"]
    assert archive["private"] and archive["privacy_unknown"]
    assert memory._execute("SELECT VALUE record.private FROM knowledge_version WHERE target=semantic:partial;")[0] == [False]
    assert [edge["id"] for edge in memory.neighbors("member:overview")["edges"]] == ["semantic:exact"]
    assert memory._execute("SELECT * FROM delivery:fact;")[0][0]["j"] == 1

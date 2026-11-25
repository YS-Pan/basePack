"""Schema 3 conversion and rollback on a disposable native database."""

import json

import pytest

from basepack.memory.draft import freeze_file
from basepack.memory.graph_upgrade import _Schema3Publication, upgrade
from basepack.memory.stages import fixed_reference
from basepack.memory.store import _digest, _input_revision, _record, _sql
from test_memory_store import memory


OVERVIEW = "member:" + "a" * 32
CLAIM = "member:" + "b" * 32
LEGACY_CLAIM = "member:" + "c" * 32
OLD_SNAPSHOT = "source_version:old"
DECISIONS = [{"id": "semantic:exact", "knowledge_revision": "edge_before",
              "legacy_kind": "depends", "type": "requires"}]


def _restore_old_fixture(memory, *, old_private=None, include_legacy_claim=False):
    """Set up current heads, an old preimage, and its exact original snapshot."""
    parent = _record(OVERVIEW)
    current = _record(CLAIM)
    logical = _record("source:guide")
    old_snapshot = _record(OLD_SNAPSHOT)
    new_snapshot = _record("source_version:new")
    old_text = "Original fixture claim.\n"
    new_text = "Revised fixture claim.\n"
    file = memory.config.root / "guide.txt"
    file.write_bytes(new_text.encode("utf-8"))
    info = file.stat()
    source = {"path": "guide.txt", "version": new_snapshot, "deleted": False, "private": False,
              "revision": _digest(new_text), "size": info.st_size, "mtime_ns": info.st_mtime_ns}
    parent_record = {"knowledge_revision": "parent_now", "text": new_text,
                     "path": "guide.txt", "source": logical, "source_version": new_snapshot,
                     "source_revision": _digest(new_text), "raw_revision": _digest(new_text),
                     "input_revision": _input_revision("", new_text),
                     "start_line": 1, "end_line": 1, "kind": "file", "private": False,
                     "stale": False, "retired": False, "basis": []}
    current_record = {**parent_record, "knowledge_revision": "claim_now", "kind": "chunk", "parent": parent}
    old_record = {**current_record, "id": current, "knowledge_revision": "claim_before",
                  "text": old_text, "source_version": old_snapshot,
                  "source_revision": _digest(old_text), "raw_revision": _digest(old_text),
                  "input_revision": _input_revision("", old_text)}
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
        f"CREATE {_sql(logical)} CONTENT {_sql(source)};",
        f"CREATE {_sql(parent)} CONTENT {_sql(parent_record)};",
        f"CREATE {_sql(current)} CONTENT {_sql(current_record)};",
        f"CREATE change:preimage SET operation='accept', previous={_sql(old_record)};",
        f"CREATE delivery:fact SET j=1, items={_sql([{'id': current, 'knowledge_revision': 'claim_before'}])};",
    ]
    if include_legacy_claim:
        legacy_claim = {**old_record, "knowledge_revision": "legacy_claim"}
        del legacy_claim["id"], legacy_claim["private"]
        initial.append(f"CREATE {_sql(_record(LEGACY_CLAIM))} CONTENT {_sql(legacy_claim)};")
    for version, text, private in ((old_snapshot, old_text, old_private), (new_snapshot, new_text, False)):
        value = {"text": text, "source": logical, "revision": _digest(text), "kind": "text",
                 "path": "guide.txt"}
        if private is not None:
            value["private"] = private
        initial.append(f"CREATE {_sql(version)} CONTENT {_sql(value)};")
    relation = {"kind": "depends", "text": "The overview depends on the historic claim.", "conditions": "",
                "knowledge_revision": "edge_before", "private": False, "stale": False, "retired": False,
                "basis": [basis],
                "endpoint_versions": {"in": {"id": parent, "knowledge_revision": "parent_now"},
                                      "out": {"id": current, "knowledge_revision": "claim_before"}}}
    partial = {**relation, "knowledge_revision": "partial",
               "endpoint_versions": {"in": relation["endpoint_versions"]["in"]}}
    for name, row in (("exact", relation), ("partial", partial)):
        initial.append(f"RELATE {OVERVIEW}->semantic:{name}->{CLAIM} CONTENT {_sql(row)};")
    memory._execute(" ".join(initial), check_project=False)


def test_graph_upgrade_rolls_back_then_reuses_exact_preimages(memory, monkeypatch):
    _restore_old_fixture(memory)
    source_digest = _digest("fixture")
    old = memory._execute("SELECT * FROM semantic ORDER BY id; INFO FOR DB;", check_project=False)
    publish = _Schema3Publication._publish

    def fail_after_writes(self, statements):
        return publish(self, [*statements[:-1], "THROW 'failed upgrade';", statements[-1]])

    with monkeypatch.context() as failure:
        failure.setattr(_Schema3Publication, "_publish", fail_after_writes)
        with pytest.raises(RuntimeError, match="failed upgrade"):
            upgrade(memory, source_sha256=source_digest, relations=DECISIONS)
    assert memory._execute("SELECT * FROM semantic ORDER BY id; INFO FOR DB;", check_project=False) == old
    assert memory._execute("SELECT VALUE memory_schema_version FROM ONLY meta:project;", check_project=False)[0] == 3

    report = upgrade(memory, source_sha256=source_digest, relations=DECISIONS)
    assert report["counts"]["converted_relations"] == 1
    assert report["reference_gaps"] == []
    assert report["archived_relations"][0]["known_endpoint_versions"] == {
        "in": {"id": OVERVIEW, "knowledge_revision": "parent_now"}}
    assert upgrade(memory, source_sha256=source_digest, relations=DECISIONS) == report
    read = memory.read(CLAIM, knowledge_revision="claim_before")
    assert read["original"]["text"] == "Original fixture claim.\n"
    assert read["member"]["private"] and read["original"]["private"]
    exact = memory._execute(
        f"SELECT id, record.private AS old_private FROM ONLY (fn::knowledge_id({CLAIM}, 'claim_before'));")[0]
    assert exact["old_private"] is False
    assert memory.knowledge(exact["id"])["private"] is True
    history = memory.history(CLAIM)["versions"]
    assert next(row for row in history if row["knowledge_revision"] == "claim_before")["private"] is True
    assert memory._execute("SELECT VALUE privacy_unknown FROM ONLY source_version:old;")[0] is True
    assert memory.neighbors(CLAIM, knowledge_revision="claim_before", allow_private=False)["record"] is None
    assert memory.knowledge("semantic:exact")["out"] == CLAIM
    archive = memory.knowledge("semantic:partial", knowledge_revision="partial")
    assert archive["legacy_history_only"] and "out" not in archive["endpoint_versions"]
    assert archive["private"] and archive["privacy_unknown"]
    assert memory._execute("SELECT VALUE record.private FROM knowledge_version WHERE target=semantic:partial;")[0] == [False]
    assert [edge["id"] for edge in memory.neighbors(OVERVIEW)["edges"]] == ["semantic:exact"]
    assert memory._execute("SELECT * FROM delivery:fact;")[0][0]["j"] == 1


def _prepare_legacy_claim(memory, tmp_path, *, old_private):
    _restore_old_fixture(memory, old_private=old_private, include_legacy_claim=True)
    upgrade(memory, source_sha256=_digest("privacy fixture"), relations=DECISIONS)
    prepared = memory.prepare(["guide.txt"])
    source = prepared["sources"][0]
    assert source["private"] is False and source["previous"]["private"] is False
    member = next(row for row in source["members"] if row["id"] == LEGACY_CLAIM)
    exact = memory._execute(f"SELECT * FROM ONLY {_sql(_record(member['exact_id']))};")[0]
    assert "private" not in exact["record"]
    assert member["source_version"] == OLD_SNAPSHOT
    snapshot = next(row for row in prepared["snapshots"] if row["id"] == OLD_SNAPSHOT)
    path = tmp_path / "prepare.json"
    path.write_text(json.dumps(prepared), encoding="utf-8")
    return fixed_reference(path), member, snapshot


def _relation(prepare, target, revision=None):
    edge = {"in": OVERVIEW, "out": target, "type": "supports", "text": "The overview cites the old claim.",
            "basis": [{"id": OVERVIEW, "knowledge_revision": "parent_now"}]}
    if revision is not None:
        edge["endpoint_versions"] = {"out": {"id": target, "knowledge_revision": revision}}
    return {"prepare": prepare, "sources": [], "edges": [edge]}


def test_prepare_freeze_and_publish_known_private_legacy_member(memory, tmp_path):
    reference, member, snapshot = _prepare_legacy_claim(memory, tmp_path, old_private=True)
    assert member["private"] is True and not member.get("privacy_unknown")
    assert snapshot["private"] is True and not snapshot.get("privacy_unknown")
    assert memory.read(LEGACY_CLAIM, knowledge_revision="legacy_claim")["original"]["text"] == "Original fixture claim.\n"

    batch = freeze_file([_relation(reference, LEGACY_CLAIM, "legacy_claim")],
                        tmp_path / "known-private.json", config=memory.config)
    edge_id = batch["edges"][0]["id"]
    assert batch["compiled_private"] == {edge_id: True}
    receipt = memory.apply(batch)
    exact_id = receipt["edge_versions"][edge_id]
    edge = memory.knowledge(exact_id)
    assert edge["private"] is True and edge["out"] == member["exact_id"]
    assert memory.knowledge(edge["out"])["knowledge_revision"] == "legacy_claim"
    assert exact_id in {row["exact_id"] for row in memory.neighbors(OVERVIEW, types=("supports",))["edges"]}
    assert memory.neighbors(OVERVIEW, types=("supports",), allow_private=False)["edges"] == []
    assert memory.neighbors(exact_id, allow_private=False)["record"] is None
    assert memory.apply(batch) == receipt

    pending = freeze_file([_relation(reference, OLD_SNAPSHOT)],
                          tmp_path / "known-before-change.json", config=memory.config)
    pending_edge = pending["edges"][0]["id"]
    assert pending["compiled_private"] == {pending_edge: True}
    memory._execute(f"UPDATE {OLD_SNAPSHOT} SET privacy_unknown=true;")
    assert memory.knowledge(OLD_SNAPSHOT)["private"] is True
    with pytest.raises(ValueError, match=f"private classification unknown.*{OLD_SNAPSHOT}"):
        memory.apply(pending)
    assert memory._execute(f"SELECT * FROM ONLY meta:batch_{pending['batch_id']};")[0] is None
    assert memory._execute(f"SELECT * FROM ONLY {_sql(_record(pending_edge))};")[0] is None
    assert memory.apply(batch) == receipt


def test_prepare_keeps_unknown_legacy_provenance_out_of_published_subset(memory, tmp_path):
    reference, member, snapshot = _prepare_legacy_claim(memory, tmp_path, old_private=None)
    assert member["private"] is True and member["privacy_unknown"] is True
    assert snapshot["private"] is True and snapshot["privacy_unknown"] is True
    assert memory.neighbors(member["exact_id"], allow_private=False)["record"] is None

    unaffected = []
    for path in ("left.txt", "right.txt"):
        (tmp_path / path).write_bytes(b"Independent original.\n")
        manifest = tmp_path / f"{path}.prepare.json"
        manifest.write_text(json.dumps(memory.prepare(["guide.txt", path])), encoding="utf-8")
        unaffected.append({"prepare": fixed_reference(manifest), "sources": [path],
                           "members": [{"path": path, "kind": "chunk", "title": path,
                                        "start_line": 1, "end_line": 1}]})

    output = tmp_path / "unknown.json"
    for target, revision in ((OLD_SNAPSHOT, None), (LEGACY_CLAIM, "legacy_claim")):
        with pytest.raises(ValueError, match=r"proposals\[2\]\.edges\[0\]\.out: Unknown exact privacy") as error:
            freeze_file([*unaffected, _relation(reference, target, revision)], output, config=memory.config)
        assert target in str(error.value)
        if revision is not None:
            assert revision in str(error.value)
        assert not output.exists()

    subset = freeze_file(unaffected, tmp_path / "unaffected.json", config=memory.config)
    receipt = memory.apply(subset)
    for row in subset["members"]:
        member = memory.knowledge(row["id"])
        assert member["path"] == row["path"] and member["private"] is False
        assert memory.neighbors(row["id"], allow_private=False)["record"]["id"] == row["id"]
    assert memory.apply(subset) == receipt


@pytest.mark.parametrize("old_private", [True, None])
def test_prepare_checks_provenance_of_migration_privacy_promotion(memory, tmp_path, old_private):
    _restore_old_fixture(memory, old_private=old_private)
    upgrade(memory, source_sha256=_digest("privacy fixture"), relations=DECISIONS)
    prepared = memory.prepare(["guide.txt"],
                              historical_versions=[{"id": CLAIM, "knowledge_revision": "claim_before"}])
    old = next(row for row in prepared["historical_versions"] if row["id"] == CLAIM)
    exact = memory._execute(f"SELECT * FROM ONLY {_sql(_record(old['exact_id']))};")[0]
    assert exact["record"]["private"] is False
    assert exact["private"] is True and not exact.get("privacy_unknown")
    assert old["source_version"] == OLD_SNAPSHOT and old["private"] is True
    path = tmp_path / "prepare-promoted.json"
    path.write_text(json.dumps(prepared), encoding="utf-8")
    draft = _relation(fixed_reference(path), CLAIM, "claim_before")
    output = tmp_path / "promoted.json"
    if old_private is None:
        assert old["privacy_unknown"] is True
        with pytest.raises(ValueError, match=r"Unknown exact privacy classification.*claim_before"):
            freeze_file([draft], output, config=memory.config)
        assert not output.exists()

        # Recreate the earlier prepare view that exposed only the outer marker.
        del old["privacy_unknown"]
        stale = tmp_path / "prepare-before-promotion-check.json"
        stale.write_text(json.dumps(prepared), encoding="utf-8")
        batch = freeze_file([_relation(fixed_reference(stale), CLAIM, "claim_before")],
                            tmp_path / "frozen-before-promotion-check.json", config=memory.config)
        with pytest.raises(ValueError, match=f"private classification unknown.*{old['exact_id']}"):
            memory.apply(batch)
        assert memory._execute(f"SELECT * FROM ONLY meta:batch_{batch['batch_id']};")[0] is None
    else:
        assert not old.get("privacy_unknown")
        batch = freeze_file([draft], output, config=memory.config)
        receipt = memory.apply(batch)
        exact_edge = receipt["edge_versions"][batch["edges"][0]["id"]]
        assert memory.knowledge(exact_edge)["private"] is True
        assert memory.neighbors(exact_edge, allow_private=False)["record"] is None


@pytest.mark.parametrize(("action", "previous_status"), [
    ("replace", "historical"), ("correct", "needs_review"), ("retire", "retired"),
])
def test_maintain_a_legacy_member_with_unknown_privacy(memory, tmp_path, action, previous_status):
    reference, member, _ = _prepare_legacy_claim(memory, tmp_path, old_private=None)
    assert member["private"] and member["privacy_unknown"]
    previous = member["exact_id"]
    draft = {"prepare": reference, "sources": []}
    if action == "retire":
        draft["delete_members"] = [LEGACY_CLAIM]
    else:
        draft["sources"] = ["guide.txt"]
        draft["members"] = [{"id": LEGACY_CLAIM, "path": "guide.txt", "kind": "chunk",
                             "title": "Updated claim", "start_line": 1, "end_line": 1}]
        if action == "correct":
            draft["corrections"] = [{"id": "fix_legacy_claim", "target": LEGACY_CLAIM,
                                     "reason": "The fixed public revision replaces the earlier claim."}]
    batch = freeze_file([draft], tmp_path / "maintain-legacy.json", config=memory.config)
    receipt = memory.apply(batch)
    original = memory.knowledge(previous)
    assert original["knowledge_revision"] == "legacy_claim" and original["source_version"] == OLD_SNAPSHOT
    assert original["private"] is True and original["privacy_unknown"] is True
    assert memory._execute(f"SELECT VALUE state.status FROM ONLY {_sql(_record(previous))};")[0] == previous_status

    current = memory.knowledge(LEGACY_CLAIM)
    if action == "retire":
        assert current["retired"] and receipt["members"] == 0
    else:
        assert current["knowledge_revision"] != original["knowledge_revision"] and receipt["members"] == 1
        assert current["private"] is False and current["text"] == "Revised fixture claim.\n"
        if action == "correct":
            correction = memory._execute("SELECT * FROM ONLY change:fix_legacy_claim;")[0]
            assert correction["previous"]["knowledge_revision"] == original["knowledge_revision"]
    assert memory.apply(batch) == receipt

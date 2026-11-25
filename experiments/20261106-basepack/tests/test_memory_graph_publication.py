"""Publish, revise, and reject graph facts through the native store."""

from base64 import b64decode

import pytest

from basepack.memory.draft import freeze
from basepack.memory.graph_write import Vertex, edge_sql, set_state
from basepack.memory.store import _record, _sql
from test_memory_store import batch_for, memory


def _facts(memory, anchor):
    return memory._execute(
        f"SELECT * FROM graph_edge WHERE in={_sql(_record(anchor))};")[0]


def test_neighbors_reads_a_relationship_with_whole_image_basis(memory):
    originals = {
        "figure.png": b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aSqoAAAAASUVORK5CYII="),
        "editor.md": b"Draw the reviewed circuit as one figure.\n",
    }
    for path, data in originals.items():
        (memory.config.root / path).write_bytes(data)
    prepared = memory.prepare(list(originals))
    memory.apply(freeze([{"sources": [{"path": row["path"], "revision": row["revision"]}
                                       for row in prepared["sources"]]}]))
    versions = {row["path"]: row["previous"]["source_version"]
                for row in memory.prepare(list(originals))["sources"]}
    image, editor = versions["figure.png"], versions["editor.md"]
    published = memory.apply(freeze([{"sources": [], "edges": [{
        "id": "figure_edit", "type": "derived_from", "in": image, "out": editor,
        "text": "The editable drawing produced the reviewed image.",
        "basis": [{"source_version": image}],
    }]}]))
    exact = published["edge_versions"]["semantic:figure_edit"]
    assert any(row["type"] == "has_basis" and row.get("locator") is None for row in _facts(memory, exact))
    for source, direction in ((image, "out"), (editor, "in")):
        result = memory.neighbors(source, direction=direction, types=["derived_from"])
        assert [row["id"] for row in result["adjacency"]] == [exact]
        assert [row["direct_basis"] for row in result["edges"]] == [[{"source_version": image}]]


def test_graph_publish_replay_and_exact_evidence_after_revision(memory):
    raw = "# 数据库\n旧条件。\n\n# 保留\n资料必须保留。\n"
    first_draft = batch_for(memory, raw)
    first_draft["edges"][0].update(conditions={"workload": "small"}, basis=[
        {"path": "guide.md", "start_line": 2, "end_line": 2, "locator": {"start_col": 0, "end_col": 2}},
        {"path": "guide.md", "start_line": 2, "end_line": 2, "locator": {"start_col": 2, "end_col": 3}},
    ])
    first = freeze([first_draft])
    receipt = memory.apply(first)
    old_id = receipt["edge_versions"]["semantic:requires"]
    old_edge = memory.knowledge(old_id)
    assert old_edge["conditions"] == {"workload": "small"}
    facts = _facts(memory, old_id)
    assert {fact["type"] for fact in facts} == {"has_basis", "version_of"}
    snapshot_facts = sorted(
        (fact for fact in facts if fact["type"] == "has_basis" and fact.get("locator")),
        key=lambda fact: fact["locator"]["locator"]["start_col"])
    assert [fact["locator"]["locator"]["end_col"] for fact in snapshot_facts] == [2, 3]
    assert len({fact["id"] for fact in snapshot_facts}) == 2
    assert len({fact["out"] for fact in snapshot_facts}) == 1
    assert memory.apply(first) == receipt
    assert _facts(memory, old_id) == facts

    second = freeze([batch_for(memory, raw.replace("旧条件", "新条件"), previous=first)])
    new_id = memory.apply(second)["edge_versions"]["semantic:requires"]
    assert new_id != old_id
    assert memory.knowledge("semantic:requires")["exact_id"] == new_id
    assert memory.knowledge("semantic:requires", knowledge_revision=old_edge["knowledge_revision"])["exact_id"] == old_id
    assert memory.knowledge(old_id) == old_edge
    status = memory._execute(f"SELECT VALUE state.status FROM ONLY {_sql(_record(old_id))};")[0]
    assert status == "historical"
    old_member = memory.knowledge(old_edge["out"])
    assert old_member["text"] == "旧条件。\n"
    assert memory.read(old_member["id"], knowledge_revision=old_member["knowledge_revision"])["original"]["text"] == old_member["text"]
    assert memory.knowledge(snapshot_facts[0]["out"])["text"] == raw
    assert {fact["type"] for fact in _facts(memory, old_edge["out"])} == {"part_of", "from_snapshot", "version_of"}


def test_native_graph_failure_rolls_back_versions_heads_and_receipt(memory, monkeypatch):
    batch = freeze([batch_for(memory, "# 数据库\n旧条件。\n\n# 保留\n资料必须保留。\n")])
    apply = memory._publish
    absent = Vertex(_record("source_version:missing"), False, ())
    bad = _record("graph_edge:invalid")

    def fail_with_invalid_endpoint(statements, *, control):
        # Keep the original transaction and add an invalid native relation
        # after all draft source, head, edge, state, and receipt writes.
        apply([*statements[:-1], set_state(bad, "current"),
               edge_sql(bad, absent, absent, "version_of"), statements[-1]], control=control)

    monkeypatch.setattr(memory, "_publish", fail_with_invalid_endpoint)
    with pytest.raises(RuntimeError, match="does not exist"):
        memory.apply(batch)
    tables = "source source_version member node semantic knowledge_version graph_edge graph_state change".split()
    results = memory._execute(" ".join(f"SELECT VALUE id FROM {table};" for table in tables))
    assert results == [[] for _ in tables]
    assert memory._execute("SELECT VALUE id FROM meta WHERE string::starts_with(<string>id, 'meta:batch_');")[0] == []


def test_retiring_a_source_withdraws_relations_to_its_historical_members(memory):
    initial = freeze([batch_for(memory, "# 数据库\n旧条件。\n\n# 保留\n资料必须保留。\n")])
    exact = memory.apply(initial)["edge_versions"]["semantic:requires"]
    storage = initial["members"][2]["id"]
    old_edge = memory.knowledge(exact)
    (memory.config.root / "current.md").write_bytes("同一条目的新原件。\n".encode())
    prepared = memory.prepare(["guide.md", "current.md"])
    new_source = next(row for row in prepared["sources"] if row["path"] == "current.md")
    memory.apply(freeze([{
        "sources": [{"path": new_source["path"], "revision": new_source["revision"]}],
        "expected": prepared["expected"],
        "members": [{"id": storage, "kind": "chunk", "path": new_source["path"],
                     "start_line": 1, "end_line": 1, "parent": None}],
    }]))
    assert memory.knowledge("semantic:requires")["stale"] is False
    assert memory.knowledge(old_edge["out"])["path"] == "guide.md"
    prepared = memory.prepare(["guide.md"])
    source = prepared["sources"][0]
    (memory.config.root / "guide.md").unlink()
    memory.apply(freeze([{
        "sources": [{"path": source["path"], "revision": source["revision"], "deleted": True}],
        "expected": prepared["expected"],
    }]))
    assert memory.knowledge(exact) == old_edge
    assert memory.knowledge("semantic:requires")["stale"] is True
    assert memory.knowledge("node:local")["stale"] is True
    assert memory.knowledge(storage)["path"] == "current.md"
    assert memory.knowledge(storage)["stale"] is False


def test_publish_rejects_direct_basis_retired_before_or_during_the_batch(memory):
    batch = freeze([batch_for(memory, "# 数据库\n旧条件。\n\n# 保留\n资料必须保留。\n")])
    memory.apply(batch)
    original = memory.config.root / "basis.txt"
    original.write_bytes(b"evidence\n")
    source = memory.prepare(["basis.txt"])["sources"][0]
    identity = {"path": source["path"], "revision": source["revision"]}
    memory.apply(freeze([{"sources": [identity]}]))
    snapshot = memory.prepare(["basis.txt"])["sources"][0]["previous"]["source_version"]
    expected = memory.prepare(["guide.md"])["expected"]
    edge = {"id": "retired_basis", "in": "node:local", "out": batch["members"][2]["id"],
            "type": "supports", "text": "Uses the cited passage as evidence",
            "basis": [{"source_version": snapshot, "start_line": 1, "end_line": 1}]}

    original.unlink()
    retire = {**identity, "deleted": True}
    with pytest.raises(RuntimeError, match="Relationship evidence is unavailable"):
        memory.apply(freeze([{"sources": [retire], "expected": expected, "edges": [edge]}]))
    assert memory._execute(f"SELECT VALUE state.status FROM ONLY {_sql(_record(snapshot))};")[0] == "current"

    memory.apply(freeze([{"sources": [retire]}]))
    with pytest.raises(RuntimeError, match="Relationship evidence is unavailable"):
        memory.apply(freeze([{"sources": [], "expected": expected, "edges": [edge]}]))
    assert memory._execute("SELECT * FROM ONLY semantic:retired_basis;")[0] is None


def test_edge_endpoints_distinguish_historical_from_withdrawn_versions(memory):
    text = "# 数据库\n旧条件。\n\n# 保留\n资料必须保留。\n"
    draft = batch_for(memory, text)
    (memory.config.root / "review.txt").write_bytes(b"The alternative method was validated.\n")
    review = memory.prepare(["review.txt"])["sources"][0]
    draft["sources"].append({"path": review["path"], "revision": review["revision"]})
    initial = freeze([draft])
    old_relation = memory.apply(initial)["edge_versions"]["semantic:requires"]
    old_claim = memory.knowledge(old_relation)["in"]
    review_id = memory.prepare(["review.txt"])["sources"][0]["previous"]["source_version"]
    citation = {"source_version": review_id, "start_line": 1, "end_line": 1}
    memory.apply(freeze([batch_for(memory, text.replace("旧条件", "新条件"), previous=initial)]))

    def relation(identity, kind, start, end):
        return {"id": identity, "in": start, "out": end, "type": kind,
                "text": "Relates the validation result to the stated rule", "basis": [citation]}

    historical = [
        relation("historical_claim", "supports", review_id, old_claim),
        relation("historical_producer", "uses", old_claim, review_id),
        relation("prior_supersedes", "supersedes", review_id, old_claim),
        relation("prior_contradicts", "contradicts", review_id, old_claim),
        {**relation("prior_dependent_basis", "contradicts", review_id, old_claim),
         "basis": [{"id": old_claim}]},
    ]
    assert memory.apply(freeze([{"sources": [], "edges": historical}]))["edges"] == len(historical)
    original = memory.prepare(["guide.md"])["sources"][0]
    old_snapshot = original["previous"]["source_version"]
    (memory.config.root / "guide.md").unlink()
    withdrawal = {"path": original["path"], "revision": original["revision"], "deleted": True}
    current = relation("invalid_support", "supports", review_id, old_claim)
    mixed = freeze([{"sources": [withdrawal], "edges": [current]}])
    statements = "SELECT * FROM graph_edge ORDER BY id; SELECT * FROM graph_state ORDER BY id;"
    before = memory._execute(statements)
    with pytest.raises(RuntimeError, match="Relationship endpoint is unavailable"):
        memory.apply(mixed)
    assert memory._execute(statements) == before
    receipt = _sql(_record(f"meta:batch_{mixed['batch_id']}"))
    assert memory._execute(f"SELECT * FROM ONLY {receipt};")[0] is None

    same_batch = relation("same_batch_supersedes", "supersedes", review_id, old_claim)
    memory.apply(freeze([{"sources": [withdrawal], "edges": [same_batch]}]))
    for identity in ("prior_supersedes", "prior_contradicts", "same_batch_supersedes"):
        assert memory.knowledge(f"semantic:{identity}")["stale"] is False
    for identity in ("historical_claim", "historical_producer", "prior_dependent_basis"):
        assert memory.knowledge(f"semantic:{identity}")["stale"] is True
    for target in (old_claim, old_snapshot):
        with pytest.raises(RuntimeError, match="Relationship endpoint is unavailable"):
            memory.apply(freeze([{"sources": [], "edges": [{**current, "out": target}]}]))
    for kind in ("supersedes", "contradicts"):
        invalid = relation(f"withdrawn_producer_{kind}", kind, old_claim, review_id)
        with pytest.raises(RuntimeError, match="Relationship endpoint is unavailable"):
            memory.apply(freeze([{"sources": [], "edges": [invalid]}]))
        intentional = relation(f"withdrawn_target_{kind}", kind, review_id, old_claim)
        result = memory.apply(freeze([{"sources": [], "edges": [intentional]}]))
        exact = memory.knowledge(result["edge_versions"][f"semantic:{intentional['id']}"])
        assert (exact["in"], exact["out"], exact["type"]) == (review_id, old_claim, kind)

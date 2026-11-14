"""Private markers follow exact retained provenance, without filtering memory."""

import pytest

from basepack.memory.draft import freeze
from basepack.memory.privacy import derive_private, source_private
from basepack.memory.store import _record, _sql
from test_memory_store import memory


@pytest.mark.parametrize(("path", "private"), [
    ("private/source.md", True), ("./private/source.md", True),
    ("docs/../private/source.md", True), ("private\\source.md", True),
    ("PRIVATE/source.md", True), ("docs/private/source.md", False),
    ("private-notes.md", False), ("private/../guide.md", False),
])
def test_private_path_is_only_the_normalized_project_root(path, private):
    assert source_private(path) is private


def test_legacy_derivation_uses_pinned_knowledge_and_preserves_unknown():
    snapshots = {"source_version:public": {"path": "guide.md"},
                 "source_version:private": {"path": "private/source.md"}}
    versions = {
        ("member:mixed", "old"): {"id": "member:mixed", "knowledge_revision": "old",
                                   "source_version": "source_version:public", "path": "guide.md",
                                   "basis": [{"member": "member:secret", "knowledge_revision": "secret",
                                              "source_version": "source_version:private"}]},
        ("member:secret", "secret"): {"private": True},
        ("member:mixed", "current"): {"private": False},
        ("member:plain", "old"): {"private": False},
        ("member:plain", "current"): {"private": True},
    }
    def marker(row):
        return derive_private(row, source_version=snapshots.get,
                              knowledge_version=lambda record, revision: versions.get((record, revision)))

    assert marker({"basis": [{"member": "member:mixed", "knowledge_revision": "old",
                               "source_version": "source_version:public"}]}) is True
    assert marker({"basis": [{"member": "member:plain", "knowledge_revision": "old",
                               "source_version": "source_version:public"}]}) is False
    assert marker({"id": "node:legacy"}) is None
    assert marker({"id": "node:legacy", "basis": []}) is None
    assert marker({"basis": [{"member": "member:missing", "knowledge_revision": "old",
                               "source_version": "source_version:public"}]}) is None
    # A retained member path also classifies old snapshots lacking their path.
    snapshots["source_version:legacy"] = {"source": "source:moved"}
    assert marker({"source_version": "source_version:legacy", "path": "private/before.md"}) is True


def test_anonymous_in_batch_evidence_cycle_terminates():
    row = {"source_version": "source_version:public", "basis": [
        {"member": "self", "knowledge_revision": "new", "source_version": "source_version:public"}]}
    assert derive_private(row, source_version=lambda _: {"path": "guide.md"},
                          knowledge_version=lambda *_: row) is False


def _initial(memory):
    (memory.config.root / "private").mkdir()
    paths = {"guide.md": "Public context cites private/source.md as an optional path.\n",
             "private/source.md": "Confidential context.\n"}
    for path, text in paths.items():
        (memory.config.root / path).write_text(text, encoding="utf-8")
    prepared = memory.prepare(list(paths))
    batch = freeze([{
        "sources": [{"path": row["path"], "revision": row["revision"]} for row in prepared["sources"]],
        "members": [
            {"path": "guide.md", "kind": "chunk", "title": "Public context", "start_line": 1, "end_line": 1,
             "private": True},
            {"path": "private/source.md", "kind": "chunk", "title": "Private context", "start_line": 1, "end_line": 1,
             "private": False},
            {"path": "guide.md", "kind": "file", "title": "Mixed context", "text": "Combined context.",
             "start_line": 1, "end_line": 1, "mandatory": True,
             "evidence": [{"member": 0}, {"member": 1}], "private": False},
        ],
        "nodes": [{"id": "anchor", "kind": "fact", "text": "Public context",
                   "evidence": [{"member": 0}]},
                  {"id": "mixed", "kind": "fact", "text": "Combined context",
                   "evidence": [{"member": 2}], "private": False}],
        "edges": [{"id": "mixed", "in": "node:mixed", "out": {"member": 0},
                   "kind": "supports", "text": "Mixed endpoint", "evidence": [{"member": 0}], "private": False}],
    }])
    memory.apply(batch)
    return [row["id"] for row in batch["members"]]


def test_private_sources_mixed_knowledge_and_read_brief_history_roundtrip(memory):
    public, private, mixed = _initial(memory)
    sources = {row["path"]: row for row in memory.sources()}
    assert sources["guide.md"]["private"] is False
    assert sources["private/source.md"]["private"] is True
    snapshots = {row["path"]: row for row in memory._rows("source_version")}
    assert snapshots["guide.md"]["private"] is False
    assert snapshots["private/source.md"]["private"] is True
    assert memory.knowledge(public)["private"] is False
    assert memory.knowledge(private)["private"] is True
    assert memory.knowledge(mixed)["private"] is True
    assert memory.knowledge("node:mixed")["private"] is True
    assert memory.knowledge("semantic:mixed")["private"] is True
    assert {row["id"]: row["private"] for row in memory.search("context", literal=True)} == {
        public: False, private: True, mixed: True}
    read = memory.read(mixed)
    assert read["member"]["private"] is True
    assert read["original"]["private"] is False
    assert memory.read(private)["original"]["private"] is True
    brief = memory.brief()
    assert brief["mandatory"][0]["private"] is True
    assert {row["path"]: row["private"] for row in brief["sources"]} == {
        "guide.md": False, "private/source.md": True}
    prepared = memory.prepare(["guide.md", "private/source.md"])
    assert [(row["private"], row["previous"]["private"]) for row in prepared["sources"]] == [
        (False, False), (True, True)]
    retained = memory.history(mixed)["versions"]
    assert retained and all(row["private"] is True for row in retained)
    before = memory.knowledge(mixed)
    memory.apply(freeze([{"sources": [], "expected": memory.prepare(["guide.md", "private/source.md"])["expected"],
                         "delete_members": [mixed]}]))
    after = memory.knowledge(mixed)
    assert after["stale"] and after["retired"] and after["private"]
    assert memory.knowledge(mixed, knowledge_revision=before["knowledge_revision"])["private"] is True


def test_relations_use_retained_endpoint_markers_in_both_directions(memory):
    public, private, _ = _initial(memory)
    old_public = memory.knowledge("node:anchor")

    def expected():
        return memory.prepare(["guide.md", "private/source.md"])["expected"]

    memory.apply(freeze([{"sources": [], "expected": expected(), "nodes": [
        {"id": "anchor", "kind": "fact", "text": "Private context", "evidence": [private]}]}]))
    old_private = memory.knowledge("node:anchor")
    assert old_private["private"] is True
    memory.apply(freeze([{"sources": [], "expected": expected(), "edges": [
        {"id": "old_public", "in": "node:anchor", "out": public,
         "kind": "supports", "text": "Earlier public endpoint", "evidence": [public],
         "endpoint_versions": {"in": {"id": "node:anchor", "knowledge_revision": old_public["knowledge_revision"]}}},
        {"id": "current_private", "in": "node:anchor", "out": public,
         "kind": "supports", "text": "Current private endpoint", "evidence": [public]},
    ]}]))
    assert memory.knowledge("semantic:old_public")["private"] is False
    assert memory.knowledge("semantic:current_private")["private"] is True
    memory.apply(freeze([{"sources": [], "expected": expected(), "nodes": [
        {"id": "anchor", "kind": "fact", "text": "Public context again", "evidence": [public]}]}]))
    memory.apply(freeze([{"sources": [], "expected": expected(), "edges": [
        {"id": "old_private", "in": "node:anchor", "out": public,
         "kind": "supports", "text": "Earlier private endpoint", "evidence": [public],
         "endpoint_versions": {"in": {"id": "node:anchor", "knowledge_revision": old_private["knowledge_revision"]}}},
    ]}]))
    assert memory.knowledge("node:anchor")["private"] is False
    assert memory.knowledge("semantic:old_private")["private"] is True
    # A metadata-only upgrade keeps identity, knowledge versions and vectors.
    row = memory._execute(f"SELECT * FROM ONLY {_sql(_record(public))};")[0]
    memory._execute(f"UPDATE {_sql(_record(public))} UNSET private;")
    legacy = memory.knowledge(public)
    marker = derive_private(legacy,
                            source_version=lambda version: memory._execute(
                                f"SELECT * FROM ONLY {_sql(_record(version))};")[0],
                            knowledge_version=lambda record, revision: memory.knowledge(
                                record, knowledge_revision=revision))
    assert marker is False
    memory._execute(f"UPDATE {_sql(_record(public))} SET private={_sql(marker)};")
    updated = memory._execute(f"SELECT * FROM ONLY {_sql(_record(public))};")[0]
    assert updated == row

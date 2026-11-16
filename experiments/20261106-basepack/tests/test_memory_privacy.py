"""Private markers follow exact retained provenance, without filtering memory."""

import pytest

from basepack.memory.draft import freeze
from basepack.memory.privacy import derive_private, privacy_rules, source_private
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


@pytest.mark.parametrize(('path', 'scope', 'private'), [
    ('research/data.md', ['research'], True), ('research-old/data.md', ['research'], False),
    ('research.md', ['research.md'], True), ('research.md.old', ['research.md'], False),
    ('any/source.md', ['.'], True), ('private/source.md', [], True),
    ('RESEARCH/data.md', ['research'], True),
])
def test_extra_private_paths_use_project_directory_boundaries(path, scope, private):
    assert source_private(path, scope) is private


def _one_source(memory):
    (memory.config.root / 'guide.md').write_bytes(b'Original context.\r\n')
    prepared = memory.prepare(['guide.md'])
    return {'sources': [{'path': 'guide.md', 'revision': prepared['sources'][0]['revision']}],
            'expected': prepared['expected'],
            'members': [{'kind': 'chunk', 'path': 'guide.md', 'title': 'Context',
                         'start_line': 1, 'end_line': 1}],
            'nodes': [{'id': 'context', 'kind': 'fact', 'text': 'Original context.',
                       'evidence': [{'member': 0}]}]}


def test_classification_change_versions_original_and_reuses_vector(memory, monkeypatch):
    from test_memory_store import DeterministicEmbeddingClient

    draft = _one_source(memory)
    batch = freeze([draft], config=memory.config)
    memory.apply(batch)
    identity = batch['members'][0]['id']
    original = memory.read(identity)['original']
    old_member = memory.knowledge(identity)
    old_node = memory.knowledge('node:context')
    vector = memory._execute(f'SELECT * FROM ONLY {_sql(_record(identity))};')[0]['embedding']
    memory.connection['private_scope'] = ['guide.md']
    assert memory.changes([], deep=True) == []
    changes = memory.changes(['guide.md'], deep=True)
    assert len(changes) == 1 and changes[0]['privacy_changed'] is True
    prepared = memory.prepare(['guide.md'])
    assert prepared['sources'][0]['private'] is True
    assert prepared['sources'][0]['previous']['private'] is False
    draft['expected'] = prepared['expected']
    draft['members'][0]['id'] = identity
    monkeypatch.setattr(DeterministicEmbeddingClient, 'embed',
                        lambda *args, **kwargs: pytest.fail('classification-only change re-encoded content'))
    memory.apply(freeze([draft], config=memory.config))
    current = memory.read(identity)['original']
    assert current['revision'] == original['revision'] and current['source_version'] != original['source_version']
    assert current['private'] is True
    assert memory.knowledge(identity)['private'] is True and memory.knowledge('node:context')['private'] is True
    assert memory.knowledge(identity, knowledge_revision=old_member['knowledge_revision'])['private'] is False
    assert memory.knowledge('node:context', knowledge_revision=old_node['knowledge_revision'])['private'] is False
    assert memory.read(identity, source_version=original['source_version'], start_line=1, end_line=1)['original'] == original
    assert memory._execute(f'SELECT * FROM ONLY {_sql(_record(identity))};')[0]['embedding'] == vector
    assert memory.changes(['guide.md'], deep=True) == []
    # The newly configured policy does not reinterpret legacy source provenance.
    assert derive_private({'source_version': 'source_version:old'},
                          source_version=lambda _: {'path': 'guide.md'}, knowledge_version=lambda *_: None) is False


def test_frozen_rules_conflict_but_committed_receipt_still_recovers(memory):
    draft = _one_source(memory)
    frozen = freeze([draft], config=memory.config)
    memory.connection['private_scope'] = ['unrelated']
    with pytest.raises(ValueError, match='rules changed'):
        memory.apply(frozen)
    assert memory._rows('source') == []
    configured = freeze([draft], config=memory.config)
    assert configured['sources'][0]['private'] is False
    result = memory.apply(configured)
    memory.connection['private_scope'] = ['.']
    assert memory.apply(configured) == result
    with pytest.raises(ValueError, match='rules changed'):
        memory.apply(freeze([draft]))


def test_configured_private_scope_does_not_discover_files(memory):
    directory = memory.config.root / 'research'
    directory.mkdir()
    (directory / 'secret.md').write_bytes(b'Secret context.\n')
    memory.connection['private_scope'] = ['research']
    assert memory.changes([], deep=True) == []
    prepared = memory.prepare(['research/secret.md'])
    assert prepared['sources'][0]['private'] is True
    assert memory.sources() == []


def _legacy_frozen(draft):
    batch = freeze([draft])
    del batch['privacy_rules'], batch['privacy_rules_revision']
    for source in batch['sources']:
        del source['private']
    return batch


def test_legacy_frozen_root_private_policy_preserves_batch_and_member_ids(memory):
    legacy = _legacy_frozen(_one_source(memory))
    identity, batch_id = legacy['members'][0]['id'], legacy['batch_id']
    result = memory.apply(legacy)
    assert memory.apply(legacy) == result
    assert legacy['batch_id'] == batch_id
    assert memory.knowledge(identity)['private'] is False
    assert memory._execute(f'SELECT * FROM ONLY meta:batch_{batch_id};')[0]['result'] == result
    memory.connection['private_scope'] = ['.']
    assert memory.apply(legacy) == result


def test_legacy_frozen_conflicts_with_added_scope_and_partial_rules_are_rejected(memory):
    legacy = _legacy_frozen(_one_source(memory))
    memory.connection['private_scope'] = ['guide.md']
    with pytest.raises(ValueError, match='Legacy frozen.*private_scope rules changed'):
        memory.apply(legacy)
    assert memory._rows('source') == memory._rows('member') == []
    memory.connection['private_scope'] = []
    legacy['privacy_rules'] = privacy_rules(memory.config)
    with pytest.raises(ValueError, match='rules changed'):
        memory.apply(legacy)
    del legacy['privacy_rules']
    memory.apply(legacy)
    assert memory.knowledge(legacy['members'][0]['id'])['private'] is False


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

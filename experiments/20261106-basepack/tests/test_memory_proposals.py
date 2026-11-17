from hashlib import sha256
import json

import pytest

from basepack.memory.draft import compile_proposals, freeze_file
from basepack.memory.privacy import privacy_rules, rules_revision


def prepared(tmp_path, *, expected=None, members=None):
    rules = privacy_rules()
    value = {'sources': [{'path': 'a.md', 'revision': 'source-rev', 'kind': 'text',
                          'members': members or []}],
             'neighborhood': {'members': [], 'nodes': [], 'edges': []},
             'expected': expected or {}, 'privacy_rules': rules,
             'privacy_rules_revision': rules_revision(rules)}
    path = tmp_path / 'reading.json'
    path.write_text(json.dumps(value), encoding='utf-8')
    return {'path': str(path), 'file_sha256': sha256(path.read_bytes()).hexdigest()}


def test_compiles_source_versions_scoped_members_and_graph(tmp_path):
    ref = prepared(tmp_path)
    proposals = [{'prepare': ref, 'sources': ['a.md'], 'members': [
        {'kind': 'chunk', 'path': 'a.md', 'start_line': 1, 'end_line': 1}],
        'nodes': [{'kind': 'topic', 'text': 'A', 'evidence': [{'member': 0}]}],
        'edges': [{'kind': 'relates', 'text': 'A', 'in': {'member': 0},
                   'out': {'node': 0}, 'evidence': [{'member': 0}]}]}]
    batch = freeze_file(proposals, tmp_path / 'frozen.json')
    assert batch['sources'][0]['revision'] == 'source-rev'
    assert batch['edges'][0]['in'] == batch['members'][0]['id']
    assert batch['edges'][0]['out'] == batch['nodes'][0]['id']
    assert batch['expected'] == {}


def test_prepare_versions_are_compiled_for_only_actual_dependencies(tmp_path):
    mid = 'member:' + 'a' * 32
    ref = prepared(tmp_path, expected={mid: 'v1', 'node:extra': 'v2'},
                   members=[{'id': mid, 'knowledge_revision': 'v1', 'stale': False, 'retired': False, 'private': False}])
    batch = compile_proposals([{'prepare': ref, 'sources': ['a.md'], 'members': [
        {'kind': 'chunk', 'path': 'a.md', 'start_line': 1, 'end_line': 1,
         'evidence': [mid]}]}])
    assert batch['expected'] == {mid: 'v1'}


def test_missing_or_retired_evidence_and_changed_prepare_fail_before_freeze(tmp_path):
    mid = 'member:' + 'a' * 32
    ref = prepared(tmp_path)
    proposal = {'prepare': ref, 'sources': ['a.md'], 'members': [
        {'kind': 'chunk', 'path': 'a.md', 'start_line': 1, 'end_line': 1, 'evidence': [mid]}]}
    with pytest.raises(ValueError, match='absent from prepare'):
        freeze_file([proposal], tmp_path / 'frozen.json')
    assert not (tmp_path / 'frozen.json').exists()
    ref = prepared(tmp_path, expected={mid: 'v1'}, members=[{'id': mid, 'retired': True}])
    proposal['prepare'] = ref
    with pytest.raises(ValueError, match='stale or retired'):
        compile_proposals([proposal])
    (tmp_path / 'reading.json').write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='SHA256 mismatch'):
        compile_proposals([proposal])


def test_conflicting_graph_writes_are_rejected_before_freeze(tmp_path):
    ref = prepared(tmp_path, expected={'node:one': 'v1'})
    proposal = {'prepare': ref, 'sources': [], 'nodes': [
        {'id': 'node:one', 'kind': 'topic', 'text': 'A', 'evidence': []}]}
    with pytest.raises(ValueError, match='Duplicate or conflicting node'):
        freeze_file([proposal, proposal], tmp_path / 'frozen.json')


def test_transitive_basis_versions_and_missing_dependency_are_explicit(tmp_path):
    parent = 'member:' + 'a' * 32
    child = 'member:' + 'b' * 32
    rows = [{'id': parent, 'knowledge_revision': 'v1', 'stale': False, 'retired': False,
             'private': True, 'basis': [{'member': child, 'knowledge_revision': 'v2'}]},
            {'id': child, 'knowledge_revision': 'v2', 'stale': False, 'retired': False}]
    ref = prepared(tmp_path, expected={parent: 'v1', child: 'v2'}, members=rows)
    proposal = {'prepare': ref, 'sources': ['a.md'], 'nodes': [
        {'kind': 'topic', 'text': 'A', 'evidence': [parent]}]}
    batch = compile_proposals([proposal])
    assert batch['expected'] == {parent: 'v1', child: 'v2'}
    assert set(batch['dependency_closure']) == {parent, child}
    assert batch['compiled_private'][batch['nodes'][0]['id']] is True
    ref = prepared(tmp_path, expected={parent: 'v1'}, members=rows)
    proposal['prepare'] = ref
    with pytest.raises(ValueError, match='Basis absent from prepare'):
        compile_proposals([proposal])


def test_newly_rewritten_stale_evidence_is_allowed(tmp_path):
    mid = 'member:' + 'a' * 32
    ref = prepared(tmp_path, expected={mid: 'v1'}, members=[{'id': mid, 'stale': True}])
    batch = compile_proposals([{'prepare': ref, 'sources': ['a.md'], 'members': [
        {'id': mid, 'kind': 'chunk', 'path': 'a.md', 'start_line': 1, 'end_line': 1},
        {'kind': 'file', 'path': 'a.md', 'start_line': 1, 'end_line': 1, 'evidence': [mid]}]}])
    assert batch['expected'][mid] == 'v1'


def test_historical_endpoint_classification_uses_exact_fixed_version(tmp_path):
    mid = 'member:' + 'a' * 32
    ref = prepared(tmp_path, expected={mid: 'current'}, members=[
        {'id': mid, 'knowledge_revision': 'current', 'stale': False, 'retired': False, 'private': False}])
    package = json.loads((tmp_path / 'reading.json').read_text(encoding='utf-8'))
    package['historical_versions'] = [{'id': mid, 'knowledge_revision': 'old', 'private': True}]
    (tmp_path / 'reading.json').write_text(json.dumps(package), encoding='utf-8')
    ref['file_sha256'] = sha256((tmp_path / 'reading.json').read_bytes()).hexdigest()
    proposal = {'prepare': ref, 'sources': ['a.md'], 'members': [
        {'kind': 'chunk', 'path': 'a.md', 'start_line': 1, 'end_line': 1}],
        'edges': [{'kind': 'evolution', 'text': 'historical', 'in': mid, 'out': {'member': 0},
                   'endpoint_versions': {'in': {'id': mid, 'knowledge_revision': 'old'}},
                   'evidence': [{'member': 0}]}]}
    batch = compile_proposals([proposal])
    assert batch['compiled_private'][batch['edges'][0]['id']] is True
    proposal['edges'][0]['endpoint_versions']['in']['knowledge_revision'] = 'missing'
    with pytest.raises(ValueError, match='Pinned knowledge version absent from prepare'):
        compile_proposals([proposal])

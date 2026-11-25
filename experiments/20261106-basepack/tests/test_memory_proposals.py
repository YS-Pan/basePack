from hashlib import sha256
import json

import pytest

from basepack.memory.draft import PrivacyUnknown, compile_proposals, freeze_file, proposal_privacy_unknown
from basepack.memory.privacy import privacy_rules, rules_revision


def prepared(tmp_path, *, expected=None, members=None, filename='reading.json', **extra):
    rules = privacy_rules()
    value = {'sources': [{'path': 'a.md', 'revision': 'source-rev', 'kind': 'text',
                          'members': members or []}],
             'neighborhood': {'members': [], 'nodes': [], 'edges': []},
             'expected': expected or {}, 'privacy_rules': rules,
             'privacy_rules_revision': rules_revision(rules), **extra}
    path = tmp_path / filename
    path.write_text(json.dumps(value), encoding='utf-8')
    return {'path': str(path), 'file_sha256': sha256(path.read_bytes()).hexdigest()}


def chunk_prepare(tmp_path):
    ref = prepared(tmp_path)
    path = tmp_path / 'reading.json'
    package = json.loads(path.read_text(encoding='utf-8'))
    source = package['sources'][0]
    source['revision'] = sha256('αbeta\r\n尾行\n'.encode('utf-8')).hexdigest()
    source['numbered_text'] = '1: αbeta\r\n2: 尾行\n'
    path.write_text(json.dumps(package, ensure_ascii=False), encoding='utf-8')
    ref['file_sha256'] = sha256(path.read_bytes()).hexdigest()
    return ref


def test_explicit_chunk_uses_fixed_prepare_original_exact_lines_and_locator(tmp_path):
    ref = chunk_prepare(tmp_path)
    # The live source is different; freeze uses the hash-pinned reading package.
    (tmp_path / 'a.md').write_text('changed after prepare', encoding='utf-8')
    chunks = [
        {'kind': 'chunk', 'path': 'a.md', 'start_line': 1, 'end_line': 2,
         'text': 'αbeta\r\n尾行\n'},
        {'kind': 'chunk', 'path': 'a.md', 'start_line': 1, 'end_line': 1,
         'locator': {'start_col': 1, 'end_col': 4}, 'text': 'bet'},
        {'kind': 'chunk', 'path': 'a.md', 'start_line': 2, 'end_line': 2},
        {'kind': 'file', 'path': 'a.md', 'start_line': 1, 'end_line': 2, 'text': 'Author summary'},
    ]
    batch = freeze_file([{'prepare': ref, 'sources': ['a.md'], 'members': chunks}], tmp_path / 'frozen.json')
    assert batch['members'][0]['text'] == 'αbeta\r\n尾行\n'
    assert batch['members'][1]['text'] == 'bet'
    assert 'text' not in batch['members'][2]
    assert batch['members'][3]['text'] == 'Author summary'


@pytest.mark.parametrize('chunk', [
    {'start_line': 1, 'end_line': 2, 'text': 'Author paraphrase'},
    {'start_line': 1, 'end_line': 1, 'text': 'αbeta\n'},
    {'start_line': 1, 'end_line': 1, 'locator': {'start_col': 1, 'end_col': 4}, 'text': 'beta'},
])
def test_freeze_rejects_nonliteral_chunk_without_writing_batch(tmp_path, chunk):
    ref = chunk_prepare(tmp_path)
    proposal = {'prepare': ref, 'sources': ['a.md'],
                'members': [{'kind': 'chunk', 'path': 'a.md', **chunk}]}
    output = tmp_path / 'frozen.json'
    with pytest.raises(ValueError, match='text differs from its original range'):
        freeze_file([proposal], output)
    assert not output.exists()


def test_freeze_rejects_prepared_original_that_does_not_match_source_revision(tmp_path):
    ref = chunk_prepare(tmp_path)
    path = tmp_path / 'reading.json'
    package = json.loads(path.read_text(encoding='utf-8'))
    package['sources'][0]['numbered_text'] = '1: changed\n'
    path.write_text(json.dumps(package, ensure_ascii=False), encoding='utf-8')
    ref['file_sha256'] = sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match='Prepared original revision mismatch'):
        compile_proposals([{'prepare': ref, 'sources': ['a.md'], 'members': [
            {'kind': 'chunk', 'path': 'a.md', 'start_line': 1, 'end_line': 1, 'text': 'changed\n'}]}])


def test_compiles_source_versions_scoped_members_and_graph(tmp_path):
    ref = prepared(tmp_path)
    proposals = [{'prepare': ref, 'sources': ['a.md'], 'members': [
        {'kind': 'chunk', 'path': 'a.md', 'start_line': 1, 'end_line': 1}],
        'nodes': [{'kind': 'topic', 'text': 'A', 'evidence': [{'member': 0}]}],
        'edges': [{'type': 'other', 'label': 'illustrates', 'text': 'A', 'in': {'member': 0},
                   'out': {'node': 0}, 'evidence': [{'member': 0}]}]}]
    batch = freeze_file(proposals, tmp_path / 'frozen.json')
    assert batch['sources'][0]['revision'] == 'source-rev'
    assert batch['edges'][0]['in'] == batch['members'][0]['id']
    assert batch['edges'][0]['out'] == batch['nodes'][0]['id']
    assert batch['expected'] == {}


def test_disposition_kind_is_required_before_a_proposal_can_freeze(tmp_path):
    disposition = {'start_line': 1, 'end_line': 1, 'reason': 'Read'}
    proposal = {'prepare': prepared(tmp_path),
                'sources': [{'path': 'a.md', 'dispositions': [disposition]}]}
    output = tmp_path / 'frozen.json'
    with pytest.raises(ValueError, match=r'proposals\[0\]\.sources\[0\]\.dispositions\[0\].*kind'):
        freeze_file([proposal], output)
    assert not output.exists()

    disposition['kind'] = 'no_knowledge'
    batch = freeze_file([proposal], output)
    assert batch['sources'][0]['dispositions'] == [disposition]


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
        'edges': [{'type': 'supersedes', 'text': 'Replaces earlier rule', 'in': {'member': 0}, 'out': mid,
                   'endpoint_versions': {'out': {'id': mid, 'knowledge_revision': 'old'}},
                   'evidence': [{'member': 0}]}]}
    batch = compile_proposals([proposal])
    assert batch['compiled_private'][batch['edges'][0]['id']] is True
    proposal['edges'][0]['endpoint_versions']['out']['knowledge_revision'] = 'missing'
    with pytest.raises(ValueError, match='Pinned knowledge version absent from prepare'):
        compile_proposals([proposal])


def test_duplicate_unknown_neighborhood_does_not_require_classification(tmp_path):
    identity = 'member:' + 'a' * 32
    exact = 'knowledge_version:' + 'b' * 64
    row = {'id': identity, 'knowledge_revision': 'v1', 'exact_id': exact}
    refs = [prepared(tmp_path, expected={identity: 'v1'}, filename=name,
                     neighborhood={'members': [row], 'nodes': [], 'edges': []})
            for name in ('first.json', 'second.json')]
    proposals = [{'prepare': ref, 'sources': [], 'nodes': [{'kind': 'topic', 'text': 'Independent'}]}
                 for ref in refs]
    batch = freeze_file(proposals, tmp_path / 'frozen.json')
    assert batch['expected'] == {}
    assert batch['compiled_private'] == {node['id']: False for node in batch['nodes']}


@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('marker', [False, True])
def test_merged_exact_privacy_supplies_historical_logical_alias(tmp_path, reverse, marker):
    member = 'member:' + 'a' * 32
    exact = 'knowledge_version:' + 'b' * 64
    current = {'id': member, 'knowledge_revision': 'current', 'private': False}
    historical = {'id': member, 'knowledge_revision': 'old'}
    unknown = prepared(tmp_path, expected={member: 'current'}, members=[current], filename='unknown.json',
                       historical_versions=[{**historical, 'exact_id': exact, 'private': True,
                                             'privacy_unknown': True}])
    known = prepared(tmp_path, filename='known.json', historical_versions=[{**historical, 'private': marker}])
    proposal = {'prepare': unknown, 'sources': ['a.md'], 'members': [
        {'kind': 'chunk', 'path': 'a.md', 'start_line': 1, 'end_line': 1}],
        'edges': [{'type': 'supports', 'text': 'Related older assertion', 'in': {'member': 0}, 'out': member,
                   'endpoint_versions': {'out': {'id': member, 'knowledge_revision': 'old'}},
                   'evidence': [{'member': 0}]}]}
    proposals = [proposal, {'prepare': known, 'sources': []}]
    if reverse:
        proposals.reverse()
    [issue] = proposal_privacy_unknown(proposal, label='fixed-proposal.json')
    assert (issue.identity, issue.revision, issue.authored_identity) == (exact, 'old', member)
    assert issue.prepare_refs == (unknown,)
    assert issue.location == 'fixed-proposal.json.edges[0].out'
    batch = compile_proposals(proposals)
    assert batch['compiled_private'][batch['edges'][0]['id']] is marker


@pytest.mark.parametrize('reverse', [False, True])
def test_conflicting_historical_privacy_names_exact_id_and_both_fixed_prepares(tmp_path, reverse):
    member = 'a' * 32
    identity = 'member:' + member
    alias = 'member:`' + member + '`'
    exact = 'knowledge_version:' + 'b' * 64
    history = {'knowledge_revision': 'v1', 'kind': 'chunk'}
    public = prepared(tmp_path, filename='public.json', historical_versions=[{
        **history, 'id': alias, 'exact_id': exact, 'private': False}])
    private = prepared(tmp_path, filename='private.json', historical_versions=[{
        **history, 'id': identity, 'private': True}])
    proposals = [{'prepare': ref, 'sources': []} for ref in (public, private)]
    if reverse:
        proposals.reverse()
    with pytest.raises(ValueError, match=f'Conflicting prepare private markers for {exact}@v1') as failure:
        compile_proposals(proposals)
    for ref in (public, private):
        assert ref['path'] in str(failure.value)
        assert ref['file_sha256'] in str(failure.value)


@pytest.mark.parametrize('privacy', [{}, {'private': True, 'privacy_unknown': True}])
def test_referenced_unknown_reports_exact_snapshot_and_keeps_batch_unwritten(tmp_path, privacy):
    exact = 'source_version:' + 'a' * 64
    snapshot = {'id': exact, 'path': 'old.md', 'revision': 'old-source-revision', 'kind': 'text', **privacy}
    ref = prepared(tmp_path, snapshots=[snapshot])
    proposal = {'prepare': ref, 'sources': ['a.md'], 'members': [
        {'kind': 'chunk', 'path': 'a.md', 'start_line': 1, 'end_line': 1}],
        'edges': [{'type': 'supports', 'text': 'Evidence in the older original', 'in': {'member': 0},
                   'out': exact, 'evidence': [{'member': 0}]}]}
    clean = {'prepare': ref, 'sources': [], 'nodes': [{'kind': 'topic', 'text': 'Independent'}]}
    assert proposal_privacy_unknown(clean) == []
    output = tmp_path / 'frozen.json'
    with pytest.raises(PrivacyUnknown, match=r'proposals\[1\]\.edges\[0\]\.out') as failure:
        freeze_file([clean, proposal], output)
    issue = failure.value
    assert (issue.identity, issue.revision, issue.prepare_refs) == (exact, 'old-source-revision', (ref,))
    assert not output.exists()
    batch = freeze_file([clean], output)
    assert len(batch['nodes']) == 1


def test_node_privacy_also_uses_evidence_members_exact_source(tmp_path):
    member = 'member:' + 'a' * 32
    exact = 'source_version:' + 'b' * 64
    row = {'id': member, 'knowledge_revision': 'member-rev', 'private': False, 'source_version': exact}
    snapshot = {'id': exact, 'path': 'old.md', 'revision': 'source-rev', 'kind': 'text', 'private': True}
    proposal = {'prepare': prepared(tmp_path, expected={member: 'member-rev'}, members=[row], snapshots=[snapshot]),
                'sources': [], 'nodes': [{'kind': 'topic', 'text': 'Old evidence', 'evidence': [member]}]}
    batch = compile_proposals([proposal])
    assert batch['compiled_private'][batch['nodes'][0]['id']] is True

    snapshot['privacy_unknown'] = True
    proposal['prepare'] = prepared(tmp_path, expected={member: 'member-rev'}, members=[row], snapshots=[snapshot])
    [issue] = proposal_privacy_unknown(proposal)
    assert (issue.identity, issue.authored_identity, issue.revision) == (exact, member, 'source-rev')
    with pytest.raises(PrivacyUnknown, match=r'proposals\[0\]\.nodes\[0\]\.evidence\[0\]'):
        compile_proposals([proposal])


def test_same_batch_parent_can_cite_child_without_privacy_cycle(tmp_path):
    proposal = {'prepare': prepared(tmp_path), 'sources': ['a.md'], 'members': [
        {'kind': 'file', 'path': 'a.md', 'start_line': 1, 'end_line': 1, 'evidence': [{'member': 1}]},
        {'kind': 'chunk', 'path': 'a.md', 'start_line': 1, 'end_line': 1, 'parent': {'member': 0}}]}
    batch = compile_proposals([proposal])
    assert batch['compiled_private'] == {item['id']: False for item in batch['members']}


def test_freeze_pins_current_endpoint_and_private_original_snapshot_basis(tmp_path):
    member = 'member:' + 'a' * 32
    snapshot = 'source_version:' + 'c' * 64
    ref = chunk_prepare(tmp_path)
    path = tmp_path / 'reading.json'
    package = json.loads(path.read_text(encoding='utf-8'))
    current = package['sources'][0]
    current['members'] = [{'id': member, 'knowledge_revision': 'v1',
                           'stale': False, 'retired': False, 'private': False}]
    package['expected'] = {member: 'v1'}
    old_text = 'Exact evidence\n'
    current['previous'] = {'source_version': snapshot, 'private': True,
                           'revision': sha256(old_text.encode('utf-8')).hexdigest(),
                           'numbered_text': '1: ' + old_text}
    path.write_text(json.dumps(package), encoding='utf-8')
    ref['file_sha256'] = sha256(path.read_bytes()).hexdigest()

    basis = {'source_version': snapshot, 'start_line': 1, 'end_line': 1,
             'locator': {'start_col': 0, 'end_col': 5}}
    draft = {'prepare': ref, 'sources': ['a.md'], 'members': [
        {'kind': 'chunk', 'path': 'a.md', 'start_line': 1, 'end_line': 1}],
        'edges': [{'type': 'contradicts', 'text': 'Conflicts under load',
                   'in': {'member': 0}, 'out': member, 'conditions': {'load': 'high'},
                   'basis': [basis]}]}
    batch = compile_proposals([draft])
    [edge] = batch['edges']
    assert edge['endpoint_versions'] == {'out': {'id': member, 'knowledge_revision': 'v1'}}
    assert edge['basis'] == [basis] and edge['conditions'] == {'load': 'high'}
    assert batch['expected_status'] == {member: True}
    assert batch['compiled_private'][edge['id']] is True

    basis['end_line'] = 2
    with pytest.raises(ValueError, match='Invalid line range'):
        compile_proposals([draft])
    basis['source_version'] = 'source_version:' + 'd' * 64
    with pytest.raises(ValueError, match='References absent from prepare: source_version'):
        compile_proposals([draft])


def test_freeze_resolves_new_relationship_endpoint_and_source_basis(tmp_path):
    draft = {'prepare': chunk_prepare(tmp_path), 'sources': ['a.md'], 'members': [
        {'kind': 'chunk', 'path': 'a.md', 'start_line': 1, 'end_line': 1},
        {'kind': 'chunk', 'path': 'a.md', 'start_line': 2, 'end_line': 2}],
        'edges': [
            {'type': 'supports', 'text': 'First statement supports second',
             'in': {'member': 0}, 'out': {'member': 1}, 'basis': [{'id': {'member': 0}}]},
            {'type': 'other', 'label': 'clarifies the scope of', 'text': 'An exact source clarifies the relation',
             'in': {'member': 1}, 'out': {'edge': 0},
             'basis': [{'path': 'a.md', 'start_line': 2, 'end_line': 2}]},
        ]}
    batch = freeze_file([draft], tmp_path / 'edges.json')
    first, second = batch['edges']
    assert second['out'] == first['id']
    assert first['basis'] == [{'id': batch['members'][0]['id']}]
    assert second['basis'] == draft['edges'][1]['basis']
    assert not batch['compiled_private'][second['id']]


@pytest.mark.parametrize(('fields', 'error'), [
    ({'kind': 'supports'}, 'Unknown edge fields'),
    ({'type': 'from_snapshot'}, 'Choose an authored edge type'),
    ({'type': 'other'}, 'specific English relation phrase'),
    ({'label': 'supports'}, 'Only other takes a label'),
    ({'conditions': []}, 'Use text or an object'),
    ({'private': False}, 'Unknown edge fields'),
])
def test_freeze_rejects_invalid_authored_relationship_shape(tmp_path, fields, error):
    draft = {'prepare': prepared(tmp_path), 'sources': [], 'edges': [
        {'in': 'node:a', 'out': 'node:b', 'type': 'supports', 'text': 'Supporting evidence',
         'evidence': ['member:' + 'a' * 32], **fields}]}
    with pytest.raises(ValueError, match=error):
        compile_proposals([draft])

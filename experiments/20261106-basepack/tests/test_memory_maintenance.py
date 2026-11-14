import json
import os

import pytest

from basepack.memory.draft import freeze
from basepack.memory.store import _record, _sql
from test_memory_store import batch_for, memory as store_memory


@pytest.fixture
def memory(store_memory):
    """Run each direct maintenance call under a temporary project owner."""
    from uuid import uuid4
    from basepack.memory import owner

    memory = store_memory
    maintain = memory.maintain

    def owned_maintain(scope, *, control=None, timeout=600):
        if control is not None:
            return maintain(scope, control=control, timeout=timeout)
        control = memory.config.memory_dir / "maintenance" / f"test-{uuid4().hex}.control"
        claim = owner.acquire(memory.config.memory_dir, memory.connection["project_id"], "test", control)
        assert claim["acquired"]
        try:
            return maintain(scope, control=str(control), timeout=timeout)
        finally:
            owner.stop_owned(memory.config.memory_dir, control)
            if not owner.status(memory.config.memory_dir)["publications"]:
                owner.release(memory.config.memory_dir, control)

    memory.maintain = owned_maintain
    return memory


def test_pending_feedback_alone_dispatches_semantic_work(memory):
    from basepack.memory import feedback

    report = feedback.report(memory, kind='retrieval', issue='Expected result missing', query='requirement')
    result = memory.maintain([])
    receipt = json.loads(open(result['receipt'], encoding='utf-8').read())
    assert result['needs_semantic'] and result['feedback'] == 1
    assert receipt['semantic'] == [] and receipt['pending_relations'] == []
    assert [item['id'] for item in receipt['feedback']] == [report['id']]


def test_reviewed_ranges_persist_only_for_the_read_source_version(memory):
    path = memory.config.root / 'reviewed.md'
    path.write_bytes(b'read\nunread\n')
    source = memory.prepare(['reviewed.md'])['sources'][0]
    reviewed = {'kind': 'no_knowledge', 'start_line': 1, 'end_line': 1, 'reason': 'No project knowledge'}
    memory.apply(freeze([{'sources': [{'path': 'reviewed.md', 'revision': source['revision'],
                               'dispositions': [reviewed]}]}]))
    result = memory.maintain([])
    report = json.loads(open(result['receipt'], encoding='utf-8').read())
    assert report['semantic'][0]['uncovered_ranges'][0]['text'] == 'unread\n'
    source = memory.prepare(['reviewed.md'])['sources'][0]
    memory.apply(freeze([{'sources': [{'path': 'reviewed.md', 'revision': source['revision'],
                               'dispositions': [reviewed, {'kind': 'no_knowledge', 'start_line': 2,
                                                            'end_line': 2, 'reason': 'No project knowledge'}]}]}]))
    assert not memory.maintain([])['needs_semantic']
    source = memory.prepare(['reviewed.md'])['sources'][0]
    memory.apply(freeze([{'sources': [{'path': 'reviewed.md', 'revision': source['revision']}]}]))
    assert not memory.maintain([])['needs_semantic']
    path.write_bytes(b'read\nunread\nnew\n')
    assert memory.maintain([])['needs_semantic']


def test_duplicate_disposition_requeues_when_representation_changes(memory):
    batch = freeze([batch_for(memory, '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n')])
    storage_id = batch['members'][2]['id']
    memory.apply(batch)
    (memory.config.root / 'duplicate.md').write_text('同一约束。\n', encoding='utf-8')
    prepared = memory.prepare(['duplicate.md', 'guide.md'])
    source = prepared['sources'][0]
    representation = next(row for row in memory._rows('member') if row['id'] == storage_id)
    memory.apply(freeze([{'sources': [{'path': 'duplicate.md', 'revision': source['revision'], 'dispositions': [{
        'kind': 'duplicate', 'start_line': 1, 'end_line': 1, 'reason': 'Already represented',
        'representations': [{'id': representation['id'], 'knowledge_revision': representation['knowledge_revision']}]}]}],
        'expected': prepared['expected']}]))
    assert not memory.maintain([])['needs_semantic']
    memory._execute(f'UPDATE {_sql(_record(storage_id))} SET stale=true, knowledge_revision="changed";')
    report = json.loads(open(memory.maintain([])['receipt'], encoding='utf-8').read())
    assert any(item['path'] == 'duplicate.md' and item.get('uncovered_ranges') for item in report['semantic'])


def test_deferred_gap_requires_exact_current_member_and_leaves_other_gaps(memory):
    batch = batch_for(memory, '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n')
    batch['members'][0]['coverage_gaps'] = ['read and deferred', 'unread']
    batch = freeze([batch])
    guide_id = batch['members'][0]['id']
    memory.apply(batch)
    guide = next(row for row in memory._rows('member') if row['id'] == guide_id)
    source = memory.prepare(['guide.md'])['sources'][0]
    deferred = {'start_line': 1, 'end_line': 5, 'reason': 'Refine later', 'gaps': [
        {'member': guide['id'], 'knowledge_revision': guide['knowledge_revision'], 'gap': 'read and deferred'}]}
    memory.apply(freeze([{'sources': [{'path': 'guide.md', 'revision': source['revision'],
                               'deferred_refinement': [deferred]}], 'expected': {guide_id: guide['knowledge_revision']}}]))
    report = json.loads(open(memory.maintain([])['receipt'], encoding='utf-8').read())
    assert 'coverage_gaps' in report['semantic'][0]['members'][0]['reasons']
    deferred['gaps'].append({'member': guide['id'], 'knowledge_revision': guide['knowledge_revision'], 'gap': 'unread'})
    memory.apply(freeze([{'sources': [{'path': 'guide.md', 'revision': source['revision'],
                               'deferred_refinement': [deferred]}], 'expected': {guide_id: guide['knowledge_revision']}}]))
    assert not memory.maintain([])['needs_semantic']
    memory._execute(f'UPDATE {_sql(_record(guide_id))} SET knowledge_revision="changed";')
    assert memory.maintain([])['needs_semantic']


@pytest.mark.parametrize('dependency_first', [False, True])
def test_mechanical_sources_with_cross_source_evidence_publish_together(memory, dependency_first):
    paths = ['a.md', 'z.md'] if dependency_first else ['z.md', 'a.md']
    for path in paths:
        (memory.config.root / path).write_bytes(b'Accepted requirement.\n')
    prepared = memory.prepare(paths)
    batch = freeze([{'sources': [{'path': row['path'], 'revision': row['revision']}
                              for row in prepared['sources']],
                  'members': [
                      {'kind': 'chunk', 'path': paths[0],
                       'start_line': 1, 'end_line': 1},
                      {'kind': 'file', 'path': paths[1],
                       'start_line': 1, 'end_line': 1, 'text': 'Accepted requirement.',
                       'evidence': [{'member': 0}]}]}])
    evidence_id = batch['members'][0]['id']
    summary_id = batch['members'][1]['id']
    memory.apply(batch)
    old = memory.read(evidence_id)['member']['source_version']
    for path in paths:
        (memory.config.root / path).write_bytes(b'Accepted requirement.\r\n')
    result = memory.maintain(paths)
    assert result['mechanical_batches'] == 1
    assert not result['needs_semantic']
    evidence = memory.read(evidence_id)
    summary = memory.read(summary_id)['member']
    assert evidence['original']['text'] == 'Accepted requirement.\r\n'
    assert summary['basis'][0]['source_version'] == evidence['member']['source_version']
    assert summary['basis'][0]['knowledge_revision'] == evidence['member']['knowledge_revision']
    assert memory.read(evidence_id, source_version=old, start_line=1, end_line=1)['original']['text'] == 'Accepted requirement.\n'
    assert not memory.maintain(paths)['needs_semantic']


@pytest.mark.parametrize('external_change', ['replace', 'append_accepted_source', 'delete'])
def test_mechanical_source_with_changed_external_evidence_remains_semantic(memory, external_change):
    for path in ['evidence.md', 'summary.md']:
        (memory.config.root / path).write_bytes(b'Accepted requirement.\n')
    prepared = memory.prepare(['evidence.md', 'summary.md'])
    batch = freeze([{'sources': [{'path': row['path'], 'revision': row['revision']}
                              for row in prepared['sources']],
                  'members': [
                      {'kind': 'chunk', 'path': 'evidence.md',
                       'start_line': 1, 'end_line': 1},
                      {'kind': 'chunk', 'path': 'summary.md',
                       'start_line': 1, 'end_line': 1, 'evidence': [{'member': 0}]}]}])
    summary_id = batch['members'][1]['id']
    memory.apply(batch)
    before = memory.read(summary_id)['member']
    if external_change == 'delete':
        (memory.config.root / 'evidence.md').unlink()
    elif external_change == 'append_accepted_source':
        (memory.config.root / 'evidence.md').write_bytes(b'Accepted requirement.\nException to the requirement.\n')
        prepared = memory.prepare(['evidence.md'])
        memory.apply(freeze([{'sources': [{'path': 'evidence.md', 'revision': prepared['sources'][0]['revision']}]}]))
    else:
        (memory.config.root / 'evidence.md').write_bytes(b'Changed requirement.\n')
    (memory.config.root / 'summary.md').write_bytes(b'Accepted requirement.\r\n')
    result = memory.maintain([])
    material = json.loads(open(result['receipt'], encoding='utf-8').read())
    summary = next(row for row in material['semantic'] if row['path'] == 'summary.md')
    assert 'mechanical_dependency_pending' in summary['members'][0]['reasons']
    assert memory.read(summary_id)['member'] == before


def test_empty_text_source_registration_finishes_until_body_appears(memory):
    path = memory.config.root / '__init__.py'
    path.write_bytes(b'')
    result = memory.maintain(['__init__.py'])
    assert result['mechanical_batches'] == 1
    assert not result['needs_semantic']
    assert memory.sources()[0]['path'] == '__init__.py'
    assert memory._rows('member') == []
    assert not memory.maintain([])['needs_semantic']
    path.write_bytes(b'New requirement.\n')
    assert memory.maintain([])['needs_semantic']


def test_cleared_source_requires_old_knowledge_retirement_before_empty_completion(memory):
    path = memory.config.root / 'cleared.md'
    path.write_bytes(b'Old requirement.\n')
    prepared = memory.prepare(['cleared.md'])
    batch = freeze([{'sources': [{'path': 'cleared.md', 'revision': prepared['sources'][0]['revision']}],
                  'members': [{'kind': 'chunk', 'path': 'cleared.md',
                               'start_line': 1, 'end_line': 1}],
                  'nodes': [{'id': 'old_claim', 'kind': 'decision', 'text': 'Old requirement.',
                             'evidence': [{'member': 0}]}]}])
    old_id = batch['members'][0]['id']
    memory.apply(batch)
    path.write_bytes(b'')
    assert memory.maintain([])['needs_semantic']
    prepared = memory.prepare(['cleared.md'])
    memory.apply(freeze([{'sources': [{'path': 'cleared.md', 'revision': prepared['sources'][0]['revision']}],
                  'expected': prepared['expected'], 'delete_members': [old_id]}]))
    assert memory.maintain([])['needs_semantic']  # the dependent claim still needs disposition
    prepared = memory.prepare(['cleared.md'])
    memory.apply(freeze([{'sources': [], 'expected': prepared['expected'], 'delete_nodes': ['old_claim']}]))
    assert not memory.maintain([])['needs_semantic']


def test_maintenance_reuses_semantics_for_line_endings_and_preserves_old_snapshot(memory, monkeypatch):
    from basepack.memory import candidate_vectors

    original = '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n'
    batch = batch_for(memory, original)
    batch['nodes'].append({'id': 'archive', 'kind': 'decision', 'text': '保留资料', 'evidence': [{'member': 3}]})
    batch['edges'].append({'id': 'node_link', 'in': 'node:local', 'out': 'node:archive',
                           'kind': 'depends', 'text': '两项要求', 'evidence': [{'member': 2}, {'member': 3}]})
    batch = freeze([batch])
    storage_id = batch['members'][2]['id']
    memory.apply(batch)
    old = memory.read(storage_id)['member']['source_version']
    calls = []
    embed = candidate_vectors.EmbeddingClient.embed

    def counted(self, inputs, *, timeout):
        calls.extend(inputs)
        return embed(self, inputs, timeout=timeout)

    monkeypatch.setattr(candidate_vectors.EmbeddingClient, 'embed', counted)
    (memory.config.root / 'guide.md').write_bytes(original.replace('\n', '\r\n').encode('utf-8'))
    result = memory.maintain(['guide.md'])
    assert result['mechanical_batches'] == 1
    assert not result['needs_semantic']
    assert len(calls) == 2  # only the two raw chunks changed; summaries were reused
    assert memory.read(storage_id)['original']['text'].endswith('\r\n')
    assert memory.read(storage_id, source_version=old, start_line=2, end_line=2)['original']['text'].endswith('\n')
    node = memory.neighbors('node:local')['record']
    edges = memory.neighbors('node:local')['edges']
    assert not node['stale'] and {edge['id'] for edge in edges} == {'semantic:requires', 'semantic:node_link'}
    assert all(not edge['stale'] for edge in edges)
    assert node['basis'][0]['source_version'] == old
    assert all(basis['source_version'] == old for edge in edges for basis in edge['basis'])
    assert not memory.maintain(['guide.md'])['needs_semantic']
    assert len(calls) == 2


def test_maintenance_finds_unaccepted_summary_after_source_only_acceptance(memory):
    original = '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n'
    batch = freeze([batch_for(memory, original)])
    guide_id = batch['members'][0]['id']
    storage_id = batch['members'][2]['id']
    memory.apply(batch)
    (memory.config.root / 'guide.md').write_bytes((original + '例外：缓存可删除。\n').encode('utf-8'))
    prepared = memory.prepare(['guide.md'])
    memory.apply(freeze([{'sources': [{'path': 'guide.md', 'revision': prepared['sources'][0]['revision']}]}]))
    assert memory.changes(['guide.md'], deep=True) == []
    result = memory.maintain(['guide.md'])
    report = json.loads(open(result['receipt'], encoding='utf-8').read())
    assert result['needs_semantic']
    source = report['semantic'][0]
    assert guide_id in {row['id'] for row in source['members']}
    assert storage_id not in {row['id'] for row in source['members']}
    assert '缓存可删除' in source['versions'][0]['changes'][0]['new_text']


def test_uncovered_addition_survives_chunk_reuse_and_source_advance(memory):
    path = memory.config.root / 'notes.md'
    path.write_bytes(b'old requirement\n')
    source = memory.prepare(['notes.md'])['sources'][0]
    batch = freeze([{'sources': [{'path': 'notes.md', 'revision': source['revision']}],
                  'members': [{'kind': 'chunk', 'path': 'notes.md',
                               'start_line': 1, 'end_line': 1}]}])
    one_id = batch['members'][0]['id']
    memory.apply(batch)
    path.write_bytes(b'old requirement\n\nnew requirement\n')
    first = memory.maintain(['notes.md'])
    # Another valid caller may accept only the source metadata. The old member
    # remains evidence of the uncovered difference after that baseline moves.
    prepared = memory.prepare(['notes.md'])
    memory.apply(freeze([{'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}]}]))
    second = memory.maintain(['notes.md'])
    assert first['reused_chunks'] == 1
    assert first['needs_semantic'] and second['needs_semantic']
    assert memory.changes(['notes.md'], deep=True) == []
    material = json.loads(open(second['receipt'], encoding='utf-8').read())
    assert 'new requirement' in material['semantic'][0]['uncovered_ranges'][0]['text']

    prepared = memory.prepare(['notes.md'])
    # A partial semantic acceptance may itself move the last old member to the
    # new version without accepting the newly added text.
    memory.apply(freeze([{'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}],
                  'expected': prepared['expected'], 'members': [
                      {'id': one_id, 'kind': 'chunk', 'path': 'notes.md', 'start_line': 1, 'end_line': 1}]}]))
    assert memory.changes(['notes.md'], deep=True) == []
    assert memory.maintain(['notes.md'])['needs_semantic']
    prepared = memory.prepare(['notes.md'])
    next_batch = freeze([{'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}],
                  'expected': prepared['expected'], 'members': [
                      {'kind': 'chunk', 'path': 'notes.md', 'start_line': 2, 'end_line': 3}]}])
    memory.apply(next_batch)
    assert not memory.maintain(['notes.md'])['needs_semantic']


@pytest.mark.parametrize('retire', [False, True])
def test_source_without_active_knowledge_remains_discoverable(memory, retire):
    path = memory.config.root / 'notes.md'
    path.write_bytes(b'new requirement\n')
    source = memory.prepare(['notes.md'])['sources'][0]
    batch = {'sources': [{'path': 'notes.md', 'revision': source['revision']}]}
    if retire:
        batch['members'] = [{'kind': 'chunk', 'path': 'notes.md', 'start_line': 1, 'end_line': 1}]
    batch = freeze([batch])
    memory.apply(batch)
    if retire:
        expected = memory.prepare(['notes.md'])['expected']
        memory.apply(freeze([{'sources': [], 'expected': expected, 'delete_members': [batch['members'][0]['id']]}]))
    assert memory.changes(['notes.md'], deep=True) == []
    for _ in range(2):
        result = memory.maintain(['notes.md'])
        material = json.loads(open(result['receipt'], encoding='utf-8').read())
        assert result['needs_semantic']
        assert material['semantic'][0]['reason'] == 'no_active_knowledge'


def test_current_file_acceptance_does_not_flag_fixed_old_relation_basis(memory):
    original = '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n'
    batch = freeze([batch_for(memory, original)])
    storage_id = batch['members'][2]['id']
    memory.apply(batch)
    old = memory.read(storage_id)['member']['source_version']
    changed = original + '例外：缓存可以删除。\n'
    update = batch_for(memory, changed, previous=batch)
    update['members'][0]['end_line'] = 6
    update['members'][0]['text'] = '本地隔离；资料须保留，但缓存可以删除。'
    update.pop('nodes')
    update.pop('edges')
    memory.apply(freeze([update]))
    result = memory.maintain(['guide.md'])
    assert not result['needs_semantic']
    assert memory.neighbors('node:local')['record']['basis'][0]['source_version'] == old
    assert memory.neighbors('node:local')['edges'][0]['basis'][0]['source_version'] == old


def test_source_only_then_first_partial_acceptance_keeps_uncovered_text(memory):
    path = memory.config.root / 'notes.md'
    path.write_bytes(b'old\n')
    prepared = memory.prepare(['notes.md'])
    memory.apply(freeze([{'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}]}]))
    path.write_bytes(b'old\nnew\n')
    prepared = memory.prepare(['notes.md'])
    batch = freeze([{'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}],
                  'members': [{'kind': 'chunk', 'path': 'notes.md', 'start_line': 1, 'end_line': 1}]}])
    memory.apply(batch)
    for _ in range(2):
        result = memory.maintain(['notes.md'])
        report = json.loads(open(result['receipt'], encoding='utf-8').read())
        assert result['needs_semantic']
        assert report['semantic'][0]['uncovered_ranges'][0]['text'] == 'new\n'


def test_multiple_partial_versions_keep_earlier_uncovered_text(memory):
    path = memory.config.root / 'notes.md'
    path.write_bytes(b'old\n')
    prepared = memory.prepare(['notes.md'])
    batch = freeze([{'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}],
                  'members': [{'kind': 'chunk', 'path': 'notes.md', 'start_line': 1, 'end_line': 1}]}])
    one_id = batch['members'][0]['id']
    memory.apply(batch)
    path.write_bytes(b'old\nX\n')
    prepared = memory.prepare(['notes.md'])
    memory.apply(freeze([{'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}],
                  'expected': prepared['expected'], 'members': [
                      {'id': one_id, 'kind': 'chunk', 'path': 'notes.md', 'start_line': 1, 'end_line': 1}]}]))
    path.write_bytes(b'old\nX\nY\n')
    prepared = memory.prepare(['notes.md'])
    next_batch = freeze([{'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}],
                  'expected': prepared['expected'], 'members': [
                      {'id': one_id, 'kind': 'chunk', 'path': 'notes.md', 'start_line': 1, 'end_line': 1},
                      {'kind': 'chunk', 'path': 'notes.md', 'start_line': 3, 'end_line': 3}]}])
    memory.apply(next_batch)
    for _ in range(2):
        result = memory.maintain(['notes.md'])
        report = json.loads(open(result['receipt'], encoding='utf-8').read())
        assert report['semantic'][0]['uncovered_ranges'][0]['text'] == 'X\n'


@pytest.mark.parametrize('addition', [b'\n', b' \n', b'  indented\n'])
def test_uncovered_whitespace_and_indentation_remain_pending(memory, addition):
    path = memory.config.root / 'notes.md'
    path.write_bytes(b'old\n')
    prepared = memory.prepare(['notes.md'])
    batch = freeze([{'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}],
                  'members': [{'kind': 'chunk', 'path': 'notes.md', 'start_line': 1, 'end_line': 1}]}])
    memory.apply(batch)
    path.write_bytes(b'old\n' + addition)
    for _ in range(2):
        result = memory.maintain(['notes.md'])
        report = json.loads(open(result['receipt'], encoding='utf-8').read())
        assert report['semantic'][0]['uncovered_ranges'][0]['text'] == addition.decode()
    prepared = memory.prepare(['notes.md'])
    next_batch = freeze([{'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}],
                  'expected': prepared['expected'], 'members': [
                      {'kind': 'file', 'path': 'notes.md', 'start_line': 1, 'end_line': 2,
                       'text': 'Accepted full source.'}]}])
    memory.apply(next_batch)
    assert not memory.maintain(['notes.md'])['needs_semantic']


def test_metadata_refresh_does_not_restore_correction(memory):
    original = '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n'
    batch = freeze([batch_for(memory, original)])
    storage_id = batch['members'][2]['id']
    memory.apply(batch)
    prepared = memory.prepare(['guide.md'])
    memory.apply(freeze([{'sources': [], 'expected': prepared['expected'], 'corrections': [
        {'id': 'known_error', 'target': storage_id, 'reason': '已知错误'}]}]))
    source = memory.config.root / 'guide.md'
    os.utime(source, ns=(source.stat().st_atime_ns, source.stat().st_mtime_ns + 1000000))
    result = memory.maintain(['guide.md'])
    assert result['mechanical_batches'] == 1
    assert result['needs_semantic']
    assert memory.read(storage_id)['member']['stale'] is True


def test_maintenance_reports_moved_lines_and_section_end_insertion(memory, monkeypatch):
    from basepack.memory import candidate_vectors

    original = '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n'
    batch = freeze([batch_for(memory, original)])
    storage_section_id = batch['members'][1]['id']
    storage_id = batch['members'][2]['id']
    retention_id = batch['members'][3]['id']
    memory.apply(batch)
    changed = '前言。\n' + original.replace('\n\n# 保留', '\n例外：临时库可共享。\n\n# 保留')
    (memory.config.root / 'guide.md').write_bytes(changed.encode('utf-8'))
    calls = []
    embed = candidate_vectors.EmbeddingClient.embed
    monkeypatch.setattr(candidate_vectors.EmbeddingClient, 'embed',
                        lambda self, inputs, *, timeout: (calls.extend(inputs), embed(self, inputs, timeout=timeout))[1])
    result = memory.maintain(['guide.md'])
    report = json.loads(open(result['receipt'], encoding='utf-8').read())
    source = report['semantic'][0]
    assert storage_section_id in {row['id'] for row in source['members']}
    assert 'node:local' in {row['id'] for row in source['related_nodes']}
    assert 'semantic:requires' in {row['id'] for row in source['related_edges']}
    moved = {row['id']: row['new_lines'] for row in source['line_mappings']}
    assert moved[storage_id] == [3, 3]
    assert report['reused_chunks'] == [retention_id]
    assert memory.read(retention_id)['original']['start_line'] == 7
    assert not calls
    assert memory.changes(['guide.md'], deep=True) == []
    assert memory.maintain(['guide.md'])['needs_semantic']


def test_same_chunk_under_another_heading_needs_semantic_review(memory):
    original = '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n'
    batch = freeze([batch_for(memory, original)])
    retention_id = batch['members'][3]['id']
    memory.apply(batch)
    changed = '# 数据库\n本地数据库隔离项目。\n资料必须保留。\n\n# 保留\n'
    (memory.config.root / 'guide.md').write_bytes(changed.encode('utf-8'))
    result = memory.maintain(['guide.md'])
    source = json.loads(open(result['receipt'], encoding='utf-8').read())['semantic'][0]
    assert retention_id in {row['id'] for row in source['members']}


def test_stopped_maintenance_does_not_publish_or_advance_source(memory):
    from basepack.memory.maintenance import MaintenanceStopped
    from basepack.memory.owner import acquire, release, stop_owned

    original = '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n'
    batch = freeze([batch_for(memory, original)])
    memory.apply(batch)
    revision = memory.sources()[0]['revision']
    (memory.config.root / 'guide.md').write_bytes(original.replace('\n', '\r\n').encode('utf-8'))
    control = memory.config.root / 'stopped'
    acquire(memory.config.memory_dir, memory.connection['project_id'], 'test', control)
    stop_owned(memory.config.memory_dir, control)
    with pytest.raises(MaintenanceStopped):
        memory.maintain(['guide.md'], control=str(control))
    release(memory.config.memory_dir, control)
    assert memory.sources()[0]['revision'] == revision


def test_mechanical_publish_rejects_concurrent_knowledge_correction(memory, monkeypatch):
    original = '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n'
    batch = freeze([batch_for(memory, original)])
    storage_id = batch['members'][2]['id']
    memory.apply(batch)
    source = memory.config.root / 'guide.md'
    source.write_bytes(original.replace('\n', '\r\n').encode('utf-8'))
    apply = memory.apply

    def concurrent(batch, **kwargs):
        expected = memory.prepare(['guide.md'])['expected']
        apply(freeze([{'sources': [], 'expected': expected, 'corrections': [
            {'id': 'racing_error', 'target': storage_id, 'reason': '并发更正'}]}]), control=kwargs['control'])
        return apply(batch, **kwargs)

    monkeypatch.setattr(memory, 'apply', concurrent)
    with pytest.raises(RuntimeError, match='Knowledge revision changed'):
        memory.maintain(['guide.md'])
    assert memory.read(storage_id)['member']['stale'] is True


def test_mechanical_publish_rejects_concurrent_original_change(memory, monkeypatch):
    original = '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n'
    batch = freeze([batch_for(memory, original)])
    memory.apply(batch)
    source = memory.config.root / 'guide.md'
    source.write_bytes(original.replace('\n', '\r\n').encode('utf-8'))
    revision = memory.sources()[0]['revision']
    apply = memory.apply

    def concurrent(batch, **kwargs):
        source.write_bytes((original + '并发补充。\n').encode('utf-8'))
        return apply(batch, **kwargs)

    monkeypatch.setattr(memory, 'apply', concurrent)
    with pytest.raises(ValueError, match='Source revision mismatch'):
        memory.maintain(['guide.md'])
    assert memory.sources()[0]['revision'] == revision


def test_brief_reports_codex_capability_without_collection(memory):
    assert memory.brief(limit=0)['codex_collection']['status'] == 'unavailable'
    memory.connection['codex'] = {'project_id': 'project', 'registry_complete': False}
    assert memory.brief(limit=0)['codex_collection']['status'] == 'registry_incomplete'
    memory.connection['codex']['registry_complete'] = True
    state = memory.brief(limit=0)['codex_collection']
    assert state['status'] == 'not_checked'
    assert 'does not collect' in state['note']


def test_task_start_detects_scoped_addition_without_claiming_it_understood(memory):
    batch = freeze([batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")])
    memory.apply(batch)
    memory.connection["source_scope"] = ["guide.md", "incoming"]
    incoming = memory.config.root / "incoming"
    incoming.mkdir()
    (incoming / "new.md").write_text("新增例外需要实际阅读。\n", encoding="utf-8")
    brief = memory.brief(limit=0)
    assert "changes" not in brief
    assert memory.changes(["incoming"])[0]["path"] == "incoming/new.md"
    assert memory.changes(["incoming"])[0]["kind"] == "added"
    assert brief["source_count"] == 1
    assert memory.search("新增例外") == []
    assert len(brief["mandatory"]) == 1


def test_task_start_checks_registered_originals_outside_new_discovery_scope(memory):
    batch = freeze([batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")])
    memory.apply(batch)
    memory.connection["source_scope"] = ["incoming"]
    source = memory.config.root / "guide.md"
    source.write_bytes(source.read_bytes() + "\n新增例外。\n".encode("utf-8"))
    assert "changes" not in memory.brief()
    assert memory.changes(["guide.md"])[0]["path"] == "guide.md"


def test_maintenance_discovery_override_keeps_registered_source_changes(memory):
    original = "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"
    batch = freeze([batch_for(memory, original)])
    memory.apply(batch)
    (memory.config.root / "guide.md").write_bytes((original + "新的历史来源约束。\n").encode("utf-8"))
    (memory.config.root / "selected.md").write_text("仅覆盖新增发现。\n", encoding="utf-8")
    result = memory.maintain(["selected.md"])
    report = json.loads(open(result["receipt"], encoding="utf-8").read())
    assert {item["path"] for item in report["semantic"]} == {"guide.md", "selected.md"}
    assert any(item["path"] == "guide.md" and item["kind"] == "modified" for item in report["changes"])


def test_maintenance_empty_discovery_keeps_unaccepted_sources_and_pending_relations(memory):
    batch = freeze([batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")])
    memory.apply(batch)
    (memory.config.root / "old-unaccepted.md").write_text("尚未接受的旧来源。\n", encoding="utf-8")
    prepared = memory.prepare(["old-unaccepted.md"])
    memory.apply(freeze([{"sources": [{"path": "old-unaccepted.md", "revision": prepared["sources"][0]["revision"]}]}]))
    memory._execute("UPDATE node:local SET stale=true;")
    result = memory.maintain([])
    report = json.loads(open(result["receipt"], encoding="utf-8").read())
    assert result["needs_semantic"]
    assert any(item["path"] == "old-unaccepted.md" and item["reason"] == "no_active_knowledge"
               for item in report["semantic"])
    assert "node:local" in {item["id"] for item in report["pending_relations"]}


def test_change_detection_keeps_published_knowledge(memory):
    batch = freeze([batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")])
    guide_id = batch['members'][0]['id']
    memory.apply(batch)
    source = memory.config.root / "guide.md"
    source.write_bytes(source.read_bytes() + "\n新增关键例外。\n".encode("utf-8"))
    count = len(memory._rows("change"))
    assert memory.changes(["guide.md"])[0]["kind"] == "modified"
    assert memory.brief(limit=0)["mandatory"][0]["stale"] is False
    assert guide_id in {row["id"] for row in memory.search("项目", literal=True)}
    assert len(memory._rows("change")) == count


def test_unchanged_start_reads_metadata_without_loading_all_member_bodies(memory, monkeypatch):
    batch = freeze([batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")])
    memory.apply(batch)
    original_rows = memory._rows

    def rows(table):
        assert table != "member", "unchanged startup must not fetch all accepted bodies"
        return original_rows(table)

    monkeypatch.setattr(memory, "_rows", rows)
    assert "changes" not in memory.brief(limit=0)


def test_startup_and_search_include_observed_version_for_feedback(memory):
    batch = freeze([batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")])
    memory.apply(batch)
    result = memory.brief()
    assert result["clues"]
    assert all(row["clue_role"] == "map" for row in result["clues"])
    assert "basis" not in result["mandatory"][0]
    assert result["mandatory"][0]["knowledge_revision"]
    candidates = memory.search("数据库")
    assert candidates
    assert all("basis" not in row and row["knowledge_revision"] for row in candidates)


def test_node_merge_and_deleted_support_preserve_remaining_evidence(memory):
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    batch["nodes"].append({"id": "alias", "kind": "decision", "text": "采用本地数据库", "evidence": [{'member': 2}]})
    batch["edges"].append({"id": "preserve", "in": "node:alias", "out": {'member': 3},
                           "kind": "depends", "text": "资料需保留", "evidence": [{'member': 3}]})
    batch = freeze([batch])
    storage_id = batch['members'][2]['id']
    retention_id = batch['members'][3]['id']
    memory.apply(batch)
    expected = memory.prepare(["guide.md"])["expected"]
    memory.apply(freeze([{"sources": [], "expected": expected, "delete_nodes": ["alias"],
                  "edges": [{"id": "preserve", "in": "node:local", "out": retention_id,
                             "kind": "depends", "text": "资料需保留", "evidence": [retention_id]}]}]))
    assert {edge["id"] for edge in memory.neighbors("node:local")["edges"]} == {"semantic:requires", "semantic:preserve"}
    assert memory.neighbors("node:alias")["record"]["retired"] is True
    assert any(row.get("previous") and row["previous"].get("in") == "node:alias"
               for row in memory._rows("change") if row.get("target") == "semantic:preserve")

    (memory.config.root / "backup.md").write_bytes("本地数据库隔离项目。\n".encode("utf-8"))
    prepared = memory.prepare(["guide.md", "backup.md"])
    backup = next(row for row in prepared["sources"] if row["path"] == "backup.md")
    members = [
        {"kind": "file", "path": "backup.md", "parent": None,
         "start_line": 1, "end_line": 1, "title": "另一依据", "text": "本地数据库隔离项目。", "evidence": [{'member': 1}]},
        {"kind": "chunk", "path": "backup.md", "parent": {'member': 0},
         "start_line": 1, "end_line": 1, "title": "隔离要求", "text": "本地数据库隔离项目。\n"}
    ]
    edge = {"id": "requires", "in": "node:local", "out": storage_id, "kind": "depends",
            "text": "本地数据库隔离项目", "evidence": [storage_id, {'member': 1}]}
    backup_batch = freeze([{"sources": [{"path": "backup.md", "revision": backup["revision"]}],
                  "expected": prepared["expected"], "members": members, "edges": [edge]}])
    backup_leaf_id = backup_batch['members'][1]['id']
    memory.apply(backup_batch)
    (memory.config.root / "backup.md").unlink()
    assert "semantic:requires" not in {row["id"] for row in memory.brief()["pending"]}
    assert memory.changes(["backup.md"])[0]["kind"] == "deleted"
    prepared = memory.prepare(["guide.md", "backup.md"])
    edge["evidence"] = [storage_id]
    memory.apply(freeze([{"sources": [{"path": "backup.md", "revision": backup["revision"], "deleted": True}],
                  "expected": prepared["expected"], "edges": [edge]}]))
    assert memory.brief()["pending_count"] == 0
    assert len(memory._rows("source_version")) == 2
    assert any(row.get("text") == "本地数据库隔离项目。\n" for row in memory._rows("source_version"))
    assert len(memory.neighbors("node:local")["edges"]) == 2
    assert next(row for row in memory._rows("member") if row["id"] == backup_leaf_id)["retired"] is True
    assert memory.changes(["backup.md"]) == []


def test_chunk_boundaries_take_exact_crlf_original_without_repeating_raw_text(memory):
    source = memory.config.root / "windows.md"
    source.write_bytes("# 标题\r\n条件与例外必须保留。\r\n".encode("utf-8"))
    prepared = memory.prepare(["windows.md"])
    batch = freeze([{"sources": [{"path": "windows.md", "revision": prepared["sources"][0]["revision"]}],
                  "expected": prepared["expected"], "members": [
                      {"kind": "file", "path": "windows.md", "parent": None,
                       "start_line": 1, "end_line": 2, "title": "标题", "text": "条件与例外须保留。", "evidence": [{'member': 1}]},
                      {"kind": "chunk", "path": "windows.md", "parent": {'member': 0},
                       "start_line": 2, "end_line": 2, "title": "条件"}]}])
    windows_body_id = batch['members'][1]['id']
    memory.apply(batch)
    assert memory.read(windows_body_id)["original"]["text"] == "条件与例外必须保留。\r\n"


def test_accepted_source_deletion_removes_retired_startup_obligations(memory):
    batch = freeze([batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")])
    memory.apply(batch)
    prepared = memory.prepare(["guide.md"])
    (memory.config.root / "guide.md").unlink()
    memory.apply(freeze([{"sources": [{"path": "guide.md", "revision": prepared["sources"][0]["revision"], "deleted": True}],
                  "expected": prepared["expected"], "delete_nodes": ["local"], "delete_edges": ["requires"]}]))
    brief = memory.brief()
    assert brief["mandatory"] == []
    assert brief["mandatory_pending_count"] == 0
    assert brief["pending_count"] == 0
    assert brief["coverage_gaps_count"] == 0


def test_retired_chunk_does_not_invalidate_reaccepted_ancestors(memory):
    batch = freeze([batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")])
    guide_id = batch['members'][0]['id']
    storage_section_id = batch['members'][1]['id']
    storage_id = batch['members'][2]['id']
    retention_id = batch['members'][3]['id']
    memory.apply(batch)
    updated = batch_for(memory, "# 数据库\n数据库离线运行并隔离项目。\n\n# 保留\n资料必须保留。\n", previous=batch)
    del updated["members"][2]["id"]
    for item in updated["members"] + updated["nodes"] + updated["edges"]:
        item["evidence"] = [{'member': 2} if value == storage_id else value for value in item.get("evidence", [])]
    updated["edges"][0]["out"] = {'member': 2}
    updated["delete_members"] = [storage_id]
    updated = freeze([updated])
    current_storage_id = updated['members'][2]['id']
    memory.apply(updated)
    prepared = memory.prepare(["guide.md"])
    before = {row["id"]: row for row in prepared["sources"][0]["members"]}
    assert before[storage_id]["retired"] is True
    assert prepared["expected"][storage_id] == before[storage_id]["knowledge_revision"]
    assert memory.brief(limit=0)["pending_count"] == 0
    relation = {"id": "current_support", "in": current_storage_id, "out": retention_id,
                "kind": "supports", "text": "当前条件共同约束存储", "evidence": [current_storage_id, retention_id]}
    result = memory.apply(freeze([{"sources": updated["sources"], "expected": prepared["expected"], "edges": [relation]}]))
    assert result["invalidated"] == []
    assert memory.brief(limit=0)["pending_count"] == 0
    assert memory.read(current_storage_id)["original"]["text"] == "数据库离线运行并隔离项目。\n"
    assert {row["id"] for row in memory.neighbors(current_storage_id)["edges"]} == {
        "semantic:requires", "semantic:current_support"}
    after = {row["id"]: row for row in memory._rows("member")}
    for member_id in (guide_id, storage_section_id, storage_id):
        assert after[member_id] == before[member_id]
    assert memory.apply(freeze([{"sources": updated["sources"]}]))["invalidated"] == []


@pytest.mark.parametrize("retired", [False, True])
def test_only_active_summary_dependencies_propagate_changes(memory, retired):
    batch = freeze([batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")])
    guide_id = batch['members'][0]['id']
    storage_section_id = batch['members'][1]['id']
    retention_id = batch['members'][3]['id']
    memory.apply(batch)
    updated = batch_for(memory, "# 数据库\n数据库离线运行并隔离项目。\n\n# 保留\n资料必须保留。\n", previous=batch)
    guide, storage = (updated["members"][0], updated["members"][2]
    )
    guide.update(start_line=4, end_line=5, text="资料必须保留。", evidence=[retention_id],
                 coverage_gaps=["数据库章节独立维护"])
    if retired:
        storage["parent"] = guide_id
    memory.apply(freeze([{"sources": updated["sources"], "expected": updated["expected"],
                  "members": [guide, storage], "delete_members": [storage_section_id] if retired else []}]))
    prepared = memory.prepare(["guide.md"])
    section = next(row for row in prepared["sources"][0]["members"] if row["id"] == storage_section_id)
    assert section["stale"] is retired
    assert section["retired"] is retired
    storage["title"] = "离线隔离条件"
    result = memory.apply(freeze([{"sources": updated["sources"], "expected": prepared["expected"], "members": [storage]}]))
    assert result["invalidated"] == []
    assert memory.read(guide_id)["member"]["stale"] is False
    # Existing node retains its old versioned evidence, even if the new member changes.
    assert memory.neighbors("node:local")["record"]["stale"] is False


def test_retired_unchanged_history_keeps_source_version_and_can_be_explicitly_revived(memory):
    original = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    original = freeze([original])
    storage_section_id = original['members'][1]['id']
    storage_id = original['members'][2]['id']
    retention_id = original['members'][3]['id']
    memory.apply(original)
    prepared = memory.prepare(["guide.md"])
    memory.apply(freeze([{"sources": [], "expected": prepared["expected"], "delete_members": [storage_id, storage_section_id],
                  "delete_nodes": ["local"], "delete_edges": ["requires"]}]))
    retired = {row["id"]: row for row in memory._rows("member") if row["retired"]}
    updated = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料与旧依据必须保留。\n", previous=original)
    updated["members"][0]["evidence"] = [retention_id]
    memory.apply(freeze([{"sources": updated["sources"], "expected": updated["expected"],
                  "members": [updated["members"][0], updated["members"][3]]}]))
    after = {row["id"]: row for row in memory._rows("member") if row["retired"]}
    assert after == retired
    snapshot = memory._execute(f"SELECT * FROM ONLY {after[storage_id]['source_version']};")[0]
    assert snapshot["text"] == "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"
    prepared = memory.prepare(["guide.md"])
    revival = {"sources": updated["sources"], "members": [{**original["members"][2], "parent": None}]}
    with pytest.raises(ValueError, match='Existing member updates require prepare UUID and expected revision'):
        memory.apply(freeze([revival]))
    memory.apply(freeze([{"sources": [], "expected": prepared["expected"], "delete_members": [storage_id]}]))
    with pytest.raises(RuntimeError, match="Knowledge revision changed"):
        memory.apply(freeze([{**revival, "expected": prepared["expected"]}]))
    memory.apply(freeze([{**revival, "expected": memory.prepare(["guide.md"])["expected"],
                  "corrections": [{"id": "revive_storage", "target": storage_id, "reason": "重新接受当前原文"}]}]))
    current = memory.read(storage_id)["member"]
    assert current["retired"] is False
    assert current["source_revision"] == updated["sources"][0]["revision"]
    previous = memory._execute("SELECT * FROM ONLY change:revive_storage;")[0]["previous"]
    assert previous["retired"] is True
    assert previous["source_version"] == retired[storage_id]["source_version"]

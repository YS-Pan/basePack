"""Persisted reading decisions are tied to real source ranges and knowledge."""

import pytest

from basepack.memory.draft import freeze

from test_memory_maintenance import memory
from test_memory_store import batch_for, memory as store_memory


@pytest.mark.parametrize('field,decision', [
    ('dispositions', {'kind': 'no_knowledge', 'start_line': 1, 'end_line': 1, 'reason': 'Read'}),
    ('deferred_refinement', {'start_line': 1, 'end_line': 1, 'reason': 'Read'}),
])
@pytest.mark.parametrize('payload_kind', ['populated', 'empty', 'null'])
@pytest.mark.parametrize('explicit_control', [False, True])
def test_source_decisions_at_batch_root_are_rejected_before_publication(
        memory, monkeypatch, field, decision, payload_kind, explicit_control):
    from basepack.memory import candidate_vectors, owner

    path = memory.config.root / 'source.md'
    path.write_bytes(b'original\n')
    source = memory.prepare(['source.md'])['sources'][0]
    monkeypatch.setattr(candidate_vectors, 'encode_candidates',
                        lambda *args, **kwargs: pytest.fail('misplaced decision reached encoding'))
    payload = {'populated': [decision], 'empty': [], 'null': None}[payload_kind]
    batch = {'sources': [{'path': 'source.md', 'revision': source['revision']}],
             'members': [{'kind': 'chunk', 'path': 'source.md',
                          'start_line': 1, 'end_line': 1}]}
    batch = freeze([batch])
    batch[field] = payload
    control = memory.config.memory_dir / 'maintenance' / 'explicit-test.control' if explicit_control else None
    if control:
        claim = owner.acquire(memory.config.memory_dir, memory.connection['project_id'], 'test', control)
        assert claim['acquired']
    try:
        with pytest.raises(ValueError, match=rf'{field}.*sources\[\]'):
            memory.apply(batch, control=str(control) if control else None)
        for table in ('source', 'source_version', 'member', 'node', 'semantic', 'change'):
            assert memory._rows(table) == []
        status = owner.status(memory.config.memory_dir)
        if control:
            assert status['run_id'] == claim['owner']['run_id']
        else:
            assert status is None
    finally:
        if control:
            owner.stop_owned(memory.config.memory_dir, control)
            owner.release(memory.config.memory_dir, control)


def test_reviewed_image_reopens_when_original_changes(memory):
    image = memory.config.root / 'image.png'
    image.write_bytes(b'first image bytes')
    source = memory.prepare(['image.png'])['sources'][0]
    memory.apply(freeze([{'sources': [{'path': 'image.png', 'kind': 'image', 'revision': source['revision'],
                               'dispositions': [{'kind': 'no_knowledge', 'whole_image': True,
                                                 'reason': 'Read image'}]}]}]))
    assert not memory.maintain([])['needs_semantic']
    image.write_bytes(b'changed image bytes')
    assert memory.maintain([])['needs_semantic']


def test_decision_rejects_unread_or_invalid_ranges(memory):
    path = memory.config.root / 'source.md'
    path.write_bytes(b'one\ntwo\n')
    source = memory.prepare(['source.md'])['sources'][0]
    for start, end in [(0, 1), (1, 3), (2, 1)]:
        with pytest.raises(ValueError, match='range'):
            memory.apply(freeze([{'sources': [{'path': 'source.md', 'revision': source['revision'],
                                      'dispositions': [{'kind': 'no_knowledge', 'start_line': start,
                                                        'end_line': end, 'reason': 'Read'}]}]}]))
    assert memory.sources() == []


def test_deferral_cannot_claim_an_unrecorded_gap(memory):
    batch = batch_for(memory, '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n')
    batch['members'][0]['coverage_gaps'] = ['unread']
    batch = freeze([batch])
    memory.apply(batch)
    guide = memory.knowledge(batch['members'][0]['id'])
    source = memory.prepare(['guide.md'])['sources'][0]
    with pytest.raises(ValueError, match='coverage gap'):
        memory.apply(freeze([{'sources': [{'path': 'guide.md', 'revision': source['revision'],
                                   'deferred_refinement': [{'start_line': 1, 'end_line': 5,
                                                            'reason': 'Read', 'gaps': [
              {'member': guide['id'], 'knowledge_revision': guide['knowledge_revision'], 'gap': 'invented'}]}]}],
                      'expected': {guide['id']: guide['knowledge_revision']}}]))


def test_deferral_does_not_replace_a_missing_coarse_representation(memory):
    import json

    path = memory.config.root / 'partial.md'
    path.write_bytes(b'first\nsecond\n')
    source = memory.prepare(['partial.md'])['sources'][0]
    memory.apply(freeze([{'sources': [{'path': 'partial.md', 'revision': source['revision'],
                               'deferred_refinement': [{'start_line': 2, 'end_line': 2, 'reason': 'Read'}]}],
                  'members': [{'kind': 'chunk', 'path': 'partial.md',
                               'start_line': 1, 'end_line': 1}]}]))
    receipt = json.loads(open(memory.maintain([])['receipt'], encoding='utf-8').read())
    assert receipt['semantic'][0]['uncovered_ranges'][0]['text'] == 'second\n'


def test_deferral_cannot_hide_gap_without_coarse_summary(memory):
    import json

    path = memory.config.root / 'partial.md'
    path.write_bytes(b'first\n')
    source = memory.prepare(['partial.md'])['sources'][0]
    memory.apply(freeze([{'sources': [{'path': 'partial.md', 'revision': source['revision']}],
                  'members': [{'kind': 'chunk', 'path': 'partial.md',
                               'start_line': 1, 'end_line': 1, 'coverage_gaps': ['not represented']}]}]))
    member = memory._rows('member')[0]
    memory.apply(freeze([{'sources': [{'path': 'partial.md', 'revision': source['revision'], 'deferred_refinement': [{
        'start_line': 1, 'end_line': 1, 'reason': 'Read', 'gaps': [{'member': member['id'],
            'knowledge_revision': member['knowledge_revision'], 'gap': 'not represented'}]}]}],
        'expected': {member['id']: member['knowledge_revision']}}]))
    receipt = json.loads(open(memory.maintain([])['receipt'], encoding='utf-8').read())
    assert 'coverage_gaps' in receipt['semantic'][0]['members'][0]['reasons']

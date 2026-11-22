from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from basepack.memory import owner, waves
from basepack.memory.cli import _maintain
from basepack.memory.draft import freeze
from basepack.memory.prompts import render_prompt
from basepack.memory.stages import fixed_reference, receipt_scope
from basepack.memory.store import _record, _sql
from basepack.memory.wave_cli import publish, task_prompt
from test_memory_history_access import delivery_context
from test_memory_store import memory


@pytest.mark.parametrize('citation', ['members', 'snapshot'])
def test_unscoped_manual_maintenance_publishes_a_fixed_candidate_once(memory, citation):
    config = memory.config
    originals = {'limit.md': b'The configured soft limit is 30 N.\n',
                 'replay.md': b'The release replay verifies the 30 N soft limit.\n'}
    config.raw['memory']['source_scope'] = list(originals)
    settings = {'model': 'test-model', 'reasoning_effort': 'low'}
    config.raw['ai'] = {'max_concurrent_subagents': 4, 'concurrency_source': 'test fixture',
                        'levels': {'1': settings, '2': settings}}
    for path, content in originals.items():
        (config.root / path).write_bytes(content)
    initial = freeze([{'sources': [{'path': path, 'revision': sha256(content).hexdigest()}
                                  for path, content in originals.items()],
                       'members': [{'path': 'limit.md', 'kind': 'chunk', 'start_line': 1, 'end_line': 1},
                                   {'path': 'replay.md', 'kind': 'chunk', 'start_line': 1, 'end_line': 1,
                                    'evidence': [{'member': 0}]}]}], config=config)
    memory.apply(initial)
    delivered = [{key: member[key] for key in ('id', 'knowledge_revision')}
                 for member in memory._rows('member')]
    memory.record_delivery('first-retrieval', delivered, context=delivery_context())
    memory.record_delivery('second-retrieval', delivered, context=delivery_context())

    def preflight(name, mode, scope=None):
        control = config.memory_dir / 'maintenance' / f'{name}.control'
        claim = owner.acquire(config.memory_dir, memory.connection['project_id'], 'parent', control)
        args = SimpleNamespace(mode=mode, scope=scope, available_subagents=4, collection=None,
                               retained=False, timeout=600)
        return control, _maintain(config, args, claim, memory=memory)

    def release(control):
        owner.stop_owned(config.memory_dir, control)
        owner.release(config.memory_dir, control)

    for name, mode, scope in [('scoped', 'manual', ['replay.md']), ('automatic', 'automatic', None)]:
        control, assessment = preflight(name, mode, scope)
        assert not assessment['needs_semantic']
        assert 'graph_candidates' not in assessment
        release(control)

    control, assessment = preflight('manual', 'manual')
    assert assessment['needs_semantic'] and assessment['graph_candidates'] == 1
    receipt = Path(assessment['receipt'])
    plan = json.loads(receipt.read_text(encoding='utf-8'))
    assert plan['changes'] == plan['semantic'] == plan['pending_relations'] == []
    candidate, = plan['graph_candidates']
    assert candidate['signals'] == ['co_delivery']
    assert candidate['delivery_events'] == [1, 2]
    assert receipt_scope(plan)['relations'] == [candidate['id']]
    assert candidate['id'] in render_prompt(config, receipt, control)['prompt']

    task = {'id': 'compare', 'graph_candidate': candidate['id'], 'goal': 'Compare fixed originals',
            'paths': [], 'write_targets': [candidate['id']], 'outputs': ['draft', 'coverage', 'errors']}
    run = assessment['owner']['run_id']
    root = config.memory_dir
    wave = waves.create(root, control, run, receipt, [task], ['reader'])['wave_id']
    waves.started(root, control, run, wave, 'reader', 'host-reader')
    waves.initialization_receipt(root, control, run, wave)
    waves.seal(root, control, run, wave)
    waves.claim(root, control, run, wave, 'reader')
    prompt = task_prompt(config, control, run, wave, 'reader', task['id'])['prompt']
    assert 'Judge the meaning, direction, applicability and future retrieval use from the originals.' in prompt
    assert '`nonpersistent` without a draft' in prompt

    def write(name, payload):
        path = config.root / name
        path.write_text(json.dumps(payload), encoding='utf-8')
        return path

    prepare = write('prepare.json', memory.prepare(list(originals)))
    endpoints = {row['path']: {key: row[key] for key in ('id', 'knowledge_revision', 'source_version')}
                 for row in candidate['endpoints']}
    origin, target = endpoints['replay.md'], endpoints['limit.md']
    basis = ({'evidence': [origin['id'], target['id']]} if citation == 'members' else
             {'basis': [{'source_version': origin['source_version'], 'start_line': 1, 'end_line': 1}]})
    draft = write('proposal.json', {'prepare': fixed_reference(prepare), 'sources': [], 'edges': [{
        'in': origin['id'], 'out': target['id'], 'type': 'supports', 'conditions': 'release replay',
        'text': 'Replay verifies the configured limit.',
        **basis, 'endpoint_versions': {
            endpoint: {key: row[key] for key in ('id', 'knowledge_revision')}
            for endpoint, row in [('in', origin), ('out', target)]}}]})
    review = write('coverage.json', {'graph_review': {'candidate': candidate['id'], 'outcome': 'proposed',
                   'reason': 'The release replay can answer what evidence supports the configured limit.',
                   'read': list(endpoints.values())}})
    errors = write('errors.json', [])
    waves.submit(root, control, run, wave, 'reader', task['id'], drafts=[draft], coverage=review, errors=errors)
    assert waves.claim(root, control, run, wave, 'reader')['retired']
    waves.notification_pending(root, control, run, wave, 'reader')
    waves.notification_result(root, control, run, wave, 'reader', accepted=True, result={'ok': True})
    waves.finish(root, control, run, wave)
    publish(config, SimpleNamespace(control=control, run_id=run, wave_id=wave,
            frozen=config.root / 'fixed.json', result=config.root / 'accepted.json', timeout=600),
            [{**fixed_reference(draft), 'assignment': task['id']}])
    closed = waves.close(root, control, run, wave)
    assert closed['closed']
    closure = json.loads(Path(closed['closure']['path']).read_text(encoding='utf-8'))
    release(control)

    edge, = memory._rows('semantic')
    assert edge['in'] == origin['id'] and edge['out'] == target['id']
    exact_id = memory.knowledge(edge['id'])['exact_id']
    assert exact_id.startswith('graph_edge:')
    [decided] = closure['graph_reviews']
    assert decided['outcome'] == 'accepted' and decided['edge'] == exact_id
    exact_ref = _sql(_record(exact_id))
    exact, published_basis = memory._execute(
        f"SELECT * FROM ONLY {exact_ref}; "
        f"SELECT out,locator FROM graph_edge WHERE in={exact_ref} AND type='has_basis';")
    assert exact['type'] == 'supports' and exact['conditions'] == 'release replay'
    assert {_record(exact[side]).table for side in ('in', 'out')} == {'knowledge_version'}
    if citation == 'members':
        assert {row['out'] for row in published_basis} == {exact['in'], exact['out']}
    else:
        assert published_basis == [{'out': origin['source_version'], 'locator': {'start_line': 1, 'end_line': 1}}]

    control, repeat = preflight('repeat', 'manual')
    assert repeat['graph_candidates'] == 0 and not repeat['needs_semantic']
    assert memory._rows('semantic') == [edge]
    release(control)

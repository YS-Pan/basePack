import json
from types import SimpleNamespace

import pytest

from basepack.memory import behavior_projection
from basepack.memory.retrieval import (make_delivery_receipt, prepare_retrieval,
                                       render_retrieval_prompt, start_retrieval)
from basepack.project.config import load_project_config
from basepack.project.init import init_project


@pytest.fixture
def config(tmp_path):
    machine = tmp_path / 'machine.toml'
    machine.write_text('schema_version=1\n', encoding='utf-8')
    return load_project_config(init_project(tmp_path / 'project', machine, max_concurrent_subagents=4, concurrency_source='test'))


def test_request_names_are_unique_and_stable_and_prompt_has_executable_pipeline(config):
    a = prepare_retrieval(config, question='one')
    b = prepare_retrieval(config, question='one')
    assert a['task_name'] != b['task_name']
    assert render_retrieval_prompt(config, a['request'])['task_name'] == a['task_name']
    prompt = render_retrieval_prompt(config, a['request'])['prompt']
    assert all(command in prompt for command in ('retrieval-start', 'graph-query', 'read-source', 'retrieval-receipt'))


def test_independent_anchor_is_frozen_before_behavior_and_receipt_uses_it(config, monkeypatch):
    prepared = prepare_retrieval(config, question='find topic')
    memory = SimpleNamespace(config=config)
    memory.config.raw['memory']['search_mode'] = 'hybrid'
    one = {'id': 'member:a', 'knowledge_revision': 'v1', 'rrf_score': 0.4, 'path': 'a.md'}
    two = {'id': 'member:b', 'knowledge_revision': 'v2', 'rrf_score': 0.2, 'path': 'b.md'}
    calls = []
    memory.hybrid_search = lambda *args, **kwargs: {'matches': [one, two], 'vector_coverage': {}}
    memory.knowledge = lambda record_id: {'id': record_id, 'knowledge_revision': 'v3', 'path': 'c.md'}
    memory.access_hints = lambda items: [{**row, 'access_interval': [0.01, 0.2]} for row in items]
    def behavior(mem, anchors, limit, scope, *, allow_private):
        assert not allow_private
        calls.append(anchors)
        assert json.loads((__import__('pathlib').Path(prepared['work']) / 'anchors.json').read_text(encoding='utf-8'))['anchors'] == anchors
        return {'model': 'sigma', 'candidates': [{'id': 'member:c', 'knowledge_revision': 'v3', 'behavior_similarity_interval': [0.8, 0.9]}]}
    monkeypatch.setattr(behavior_projection, 'behavior_candidates', behavior, raising=False)
    result = start_retrieval(memory, prepared['request'])
    assert [a['id'] for a in result['frozen']['anchors']] == ['member:a', 'member:b']
    assert [a['alpha'] for a in result['frozen']['anchors']] == [0.5, 0.5]
    assert result['behavior_candidates']['candidates'][0]['access_interval'] == [0.01, 0.2]
    memory.hybrid_search = lambda *args, **kwargs: pytest.fail('anchors must not be recomputed')
    assert start_retrieval(memory, prepared['request']) == result
    assert len(calls) == 1
    ranked = {'items': [two]}
    candidates = [one, two, {'id': 'member:c', 'knowledge_revision': 'v3'}]
    receipt = make_delivery_receipt(config, prepared['request'], ranked, candidates)
    assert receipt['items'] == [{'id': 'member:b', 'knowledge_revision': 'v2'}]
    assert receipt['context']['anchors'] == result['frozen']['anchors']
    assert receipt['context']['model'] == 'sigma'
    with pytest.raises(ValueError, match='omits observed'):
        make_delivery_receipt(config, prepared['request'], ranked, [two])


def test_empty_base_keeps_unknown_anchor_and_behavior_model(config, monkeypatch):
    prepared = prepare_retrieval(config, question='new topic')
    memory = SimpleNamespace(config=config, vector_search=lambda *a, **k: {'matches': [], 'vector_coverage': {}},
                             hybrid_search=lambda *a, **k: {'matches': [], 'vector_coverage': {}},
                             access_hints=lambda items: items)
    monkeypatch.setattr(behavior_projection, 'behavior_candidates', lambda *args, **kwargs: {'model': None, 'candidates': []})
    result = start_retrieval(memory, prepared['request'])
    assert result['frozen']['anchors'] == []
    assert make_delivery_receipt(config, prepared['request'], {'items': []}, [])['context']['model'] is None




def test_receipt_preserves_candidate_and_each_observed_access_model(config, monkeypatch):
    prepared = prepare_retrieval(config, question='concurrent switch')
    memory = SimpleNamespace(config=config)
    memory.config.raw['memory']['search_mode'] = 'hybrid'
    base = {'id': 'member:a', 'knowledge_revision': 'v1', 'rrf_score': 0.4, 'path': 'a.md',
            'access_model': 'model-before', 'access_compiled_j': 2, 'access_fact_j': 3,
            'access_interval': [0.2, 0.6]}
    memory.hybrid_search = lambda *args, **kwargs: {'matches': [base], 'vector_coverage': {}}
    memory.knowledge = lambda record_id: {'id': record_id, 'knowledge_revision': 'v2', 'path': 'b.md'}
    memory.access_hints = lambda items: [{**row, 'access_model': 'model-B', 'access_compiled_j': 5,
                                        'access_fact_j': 6, 'access_interval': [0.1, 0.4]} for row in items]
    monkeypatch.setattr(behavior_projection, 'behavior_candidates', lambda *a, **k: {
        'model': 'model-A', 'candidates': [{'id': 'member:b', 'knowledge_revision': 'v2',
                                             'behavior_similarity_interval': [0.2, 0.9]}]})
    start_retrieval(memory, prepared['request'])
    later = {'id': 'member:b', 'knowledge_revision': 'v2', 'access_model': 'model-C',
             'access_compiled_j': 7, 'access_fact_j': 7, 'access_interval': [0.3, 0.5]}
    partial = {'id': 'member:b', 'knowledge_revision': 'v2', 'access_compiled_j': 8}
    receipt = make_delivery_receipt(config, prepared['request'], {'items': [later]}, [base, later, partial])
    assert receipt['context']['model'] == 'model-A'
    observations = receipt['context']['access_observations']
    assert {'id': 'member:b', 'knowledge_revision': 'v2', 'source': 'behavior',
            'access_model': 'model-B', 'access_compiled_j': 5, 'access_fact_j': 6,
            'access_interval': [0.1, 0.4]} in observations
    assert {'source': 'followup', **later} in observations
    assert {'source': 'followup', **partial} in observations
    assert any(row.get('access_model') == 'model-before' for row in observations)

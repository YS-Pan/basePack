import json

from basepack.memory.draft import freeze
from basepack.memory.retrieval import start_retrieval
from test_memory_store import batch_for, memory


def test_brief_prioritizes_hot_map_without_changing_facts_or_excluding_cold(memory, tmp_path, monkeypatch):
    draft = batch_for(memory, '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n')
    draft['members'][0]['mandatory'] = False
    draft['members'][2]['mandatory'] = True
    memory.apply(freeze([draft]))
    maps = memory._execute("SELECT id,knowledge_revision,kind FROM member WHERE kind IN ['file','section'];")[0]
    hot = next(row for row in maps if row['kind'] == 'file')
    cold = next(row for row in maps if row['kind'] == 'section')
    request = tmp_path / 'request.json'
    request.write_text(json.dumps({'question': '数据库隔离', 'delivery_id': 'anchor-source'}, ensure_ascii=False), encoding='utf-8')
    started = start_retrieval(memory, request)
    frozen = started['frozen']
    context = {key: frozen[key] for key in ('anchors', 'knowledge_cutoff', 'query', 'episode', 'budget', 'policy')}
    context.update(candidates=[{'id': row['id'], 'knowledge_revision': row['knowledge_revision']}
                               for row in frozen['base']['matches']], model=None)
    pair = [{'id': row['id'], 'knowledge_revision': row['knowledge_revision']} for row in (hot, cold)]
    memory.record_delivery('pair', pair, context=context)
    for tick in range(12):
        memory.record_delivery(f'hot-{tick}', pair[:1], context=context)
    memory.train_behavior(rank=2, epsilon=0.9, strength=0.01)
    before = memory.access_hints(pair)
    assert before[1]['access_interval'][1] < 0.01
    head = memory._execute('SELECT * FROM ONLY meta:delivery;')[0]
    from basepack.memory import vectors
    monkeypatch.setattr(vectors, 'EmbeddingClient', lambda *args: (_ for _ in ()).throw(AssertionError('brief must not embed')))
    brief = memory.brief(limit=6)
    assert len(brief['mandatory']) == 1
    assert brief['mandatory'][0]['text'] == '本地数据库隔离项目。\n'
    assert 'access_interval' not in brief['mandatory'][0]
    ids = [row['id'] for row in brief['clues']]
    assert ids.index(hot['id']) < ids.index(cold['id'])
    cold_clue = next(row for row in brief['clues'] if row['id'] == cold['id'])
    assert cold_clue['access_interval'] == before[1]['access_interval']
    assert cold_clue['access_model'] == before[1]['access_model']
    assert brief['overview_sampling']['candidates'] <= 48
    assert memory._execute('SELECT * FROM ONLY meta:delivery;')[0] == head
    assert memory.access_hints(pair) == before
    assert cold['id'] in {row['id'] for row in memory.search('数据库')}

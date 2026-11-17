import argparse
import json

from basepack.memory import cli
from basepack.memory.draft import freeze
from test_memory_store import memory, batch_for


def test_retrieval_cli_actual_database_pipeline(memory, monkeypatch, tmp_path):
    from basepack.memory import store
    memory.apply(freeze([batch_for(memory, '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n')]))
    parser = argparse.ArgumentParser()
    cli.register_commands(parser.add_subparsers(dest='command', required=True))
    monkeypatch.setattr(store, 'Memory', lambda config: memory)
    def run(*args):
        result, status = cli.dispatch(parser.parse_args(['memory', *map(str, args)]), memory.config)
        assert status == 0
        return result
    request = tmp_path / 'request.json'
    request.write_text(json.dumps({'question': '数据库隔离', 'delivery_id': 'retrieval-test', 'scope': '', 'content_budget': 6000}, ensure_ascii=False), encoding='utf-8')
    start = run('retrieval-start', '--request', request)
    assert start['frozen']['anchors']
    assert start['behavior_candidates']['model'] is None
    assert run('retrieval-start', '--request', request)['frozen']['anchors'] == start['frozen']['anchors']
    items = start['frozen']['base']['matches']
    candidates = tmp_path / 'candidates.json'
    candidates.write_text(json.dumps(items, ensure_ascii=False), encoding='utf-8')
    selected = items[0]
    evidence = memory.read(selected['id'], knowledge_revision=selected['knowledge_revision'])
    row = {**evidence['member'], **evidence['original'], 'score': 90, 'reason': 'Relevant evidence'}
    row['id'] = selected['id']
    row['knowledge_revision'] = selected['knowledge_revision']
    scored = tmp_path / 'scored.json'
    ranked = tmp_path / 'ranked.json'
    receipt = tmp_path / 'delivery.json'
    scored.write_text(json.dumps([row], ensure_ascii=False), encoding='utf-8')
    run('rank', '--input', scored, '--budget', '6000', '--output', ranked)
    run('retrieval-receipt', '--request', request, '--ranked', ranked, '--candidates', candidates, '--output', receipt)
    fact = run('delivery', '--input', receipt)
    assert fact['items'][0]['id'] == selected['id']
    assert fact['context']['anchors'] == start['frozen']['anchors']
    assert fact['context']['model'] is None
    assert fact['context']['access_observations']
    assert all('access_model' in row for row in fact['context']['access_observations'])
    assert run('delivery', '--input', receipt)['duplicate'] is True

    # Train on one real co-delivery, then age the second exact version with repeated
    # first-version deliveries; low access must not remove it from base retrieval.
    assert len(items) >= 2
    other = items[1]
    initial = json.loads(receipt.read_text(encoding='utf-8'))
    pair = [{"id": item["id"], "knowledge_revision": item["knowledge_revision"]} for item in items[:2]]
    initial.update(delivery_id='co-delivery', items=pair)
    receipt.write_text(json.dumps(initial, ensure_ascii=False), encoding='utf-8')
    run('delivery', '--input', receipt)
    for tick in range(12):
        initial.update(delivery_id=f'only-a-{tick}', items=pair[:1])
        receipt.write_text(json.dumps(initial, ensure_ascii=False), encoding='utf-8')
        run('delivery', '--input', receipt)
    trained = run('behavior-train', '--rank', '2', '--epsilon', '0.9', '--strength', '0.01')
    assert trained['model']
    request2 = tmp_path / 'request2.json'
    request2.write_text(json.dumps({'question': '数据库隔离', 'delivery_id': 'find-again', 'scope': '', 'content_budget': 6000}, ensure_ascii=False), encoding='utf-8')
    second = run('retrieval-start', '--request', request2)
    base = second['frozen']['base']['matches']
    old = next(row for row in base if row['id'] == other['id'])
    assert old['access_interval'][1] < 0.01
    assert second['behavior_candidates']['model'] == trained['model']
    assert any(row['id'] == other['id'] and len(row['behavior_similarity_interval']) == 2
               for row in second['behavior_candidates']['candidates'])
    # Deliver the low-weight version and compile the confirmed event.
    candidates.write_text(json.dumps(base + second['behavior_candidates']['candidates'], ensure_ascii=False), encoding='utf-8')
    evidence = memory.read(other['id'], knowledge_revision=other['knowledge_revision'])
    row = {**evidence['member'], **evidence['original'], 'score': 90, 'reason': 'Required evidence',
           'id': other['id'], 'knowledge_revision': other['knowledge_revision']}
    scored.write_text(json.dumps([row], ensure_ascii=False), encoding='utf-8')
    run('rank', '--input', scored, '--budget', '6000', '--output', ranked)
    run('retrieval-receipt', '--request', request2, '--ranked', ranked, '--candidates', candidates, '--output', receipt)
    learned_fact = run('delivery', '--input', receipt)
    assert learned_fact['context']['model'] == trained['model']
    assert any(row.get('access_model') == trained['model'] for row in learned_fact['context']['access_observations'])
    run('behavior-compile')
    refreshed = memory.access_hints([pair[1]])[0]
    assert refreshed['access_interval'] == [1.0, 1.0]
    assert refreshed['access_hits'] == old['access_hits'] + 1

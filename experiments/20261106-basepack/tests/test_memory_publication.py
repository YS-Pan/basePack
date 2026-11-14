"""Publication isolation and task-scoped cancellation regressions."""
from copy import deepcopy
from io import BytesIO
from threading import Event, Thread
from urllib.error import HTTPError

import pytest

from basepack.memory import candidate_vectors
from basepack.memory.draft import freeze
from basepack.memory.maintenance import MaintenanceStopped, stop
from test_memory_store import batch_for, memory


def test_change_detection_cannot_invalidate_a_newer_accept(memory, monkeypatch):
    from basepack.memory import store
    initial = freeze([batch_for(memory, '# 数据库\n旧条件。\n\n# 保留\n资料必须保留。\n')])
    memory.apply(initial)
    storage = initial['members'][2]['id']
    new_batch = freeze([batch_for(memory, '# 数据库\n新条件。\n\n# 保留\n资料必须保留。\n', previous=initial)])
    original = store.detect_changes

    def interleaved(*args, **kwargs):
        detected = original(*args, **kwargs)
        memory.apply(new_batch)
        return detected

    monkeypatch.setattr(store, 'detect_changes', interleaved)
    assert memory.changes(['guide.md'])[0]['kind'] == 'modified'
    current = memory.read(storage)['member']
    assert current['stale'] is False
    assert '新条件' in current['text']


@pytest.mark.parametrize('event', ['stop', 'change'])
def test_candidate_not_published_after_stop_or_source_change(memory, tmp_path, monkeypatch, event):
    initial = freeze([batch_for(memory, '# 数据库\n旧条件。\n\n# 保留\n资料必须保留。\n')])
    memory.apply(initial)
    batch = freeze([batch_for(memory, '# 数据库\n新条件。\n\n# 保留\n资料必须保留。\n', previous=initial)])
    storage = initial['members'][2]['id']
    old = deepcopy(memory.read(storage)['member'])
    ready, release = Event(), Event()
    monkeypatch.setattr(candidate_vectors, 'status', lambda _: {'model': {'embedding_identity': 'same'}})

    class Client:
        def __init__(self, machine): pass
        def embed(self, inputs, *, timeout):
            ready.set()
            assert release.wait(10)
            return {'embedding_identity': 'same', 'vectors': [[1.0, 0.0] for _ in inputs]}

    monkeypatch.setattr(candidate_vectors, 'EmbeddingClient', Client)
    failures = []
    control = str(tmp_path / 'control')

    def publish():
        try:
            memory.apply(batch, control=control)
        except Exception as error:
            failures.append(error)

    worker = Thread(target=publish)
    worker.start()
    assert ready.wait(10)
    assert memory.read(storage)['member'] == old
    if event == 'stop':
        stop(control)
    else:
        (memory.config.root / 'guide.md').write_text('changed during encoding\n', encoding='utf-8')
    release.set()
    worker.join(10)
    assert not worker.is_alive()
    assert len(failures) == 1
    assert isinstance(failures[0], MaintenanceStopped if event == 'stop' else ValueError)
    assert memory.read(storage)['member'] == old


def test_candidate_vectors_are_published_together_and_reused(memory, monkeypatch):
    initial = freeze([batch_for(memory, '# 数据库\n旧条件。\n\n# 保留\n资料必须保留。\n')])
    memory.apply(initial)
    batch = freeze([batch_for(memory, '# 数据库\n新条件。\n\n# 保留\n资料必须保留。\n', previous=initial)])
    calls = []
    monkeypatch.setattr(candidate_vectors, 'status', lambda _: {'model': {'embedding_identity': 'same'}})

    class Client:
        def __init__(self, machine): pass
        def embed(self, inputs, *, timeout):
            calls.append(inputs)
            return {'embedding_identity': 'same', 'vectors': [[1.0, 0.0] for _ in inputs]}

    monkeypatch.setattr(candidate_vectors, 'EmbeddingClient', Client)
    memory.apply(batch)
    rows = memory._execute('SELECT * FROM member WHERE stale=false;')[0]
    assert all(row['embedding_identity'] == 'same' and row['embedded_revision'] == row['input_revision']
               and row['embedding'] == [1.0, 0.0] for row in rows)
    replay = batch_for(memory, '# 数据库\n新条件。\n\n# 保留\n资料必须保留。\n', previous=initial)
    memory.apply(freeze([replay]))
    assert len(calls) == 1


@pytest.mark.parametrize('failed_request', [1, 2])
def test_candidate_http_failure_publishes_no_knowledge_or_vectors(memory, monkeypatch, failed_request):
    initial = freeze([batch_for(memory, '# 数据库\n旧条件。\n\n# 保留\n资料必须保留。\n')])
    memory.apply(initial)
    batch = freeze([batch_for(memory, '# 数据库\n新条件。\n\n# 保留\n资料必须保留。\n', previous=initial)])
    tables = ('source', 'source_version', 'member', 'node', 'semantic', 'change')

    def snapshot():
        return {table: sorted(memory._execute(f'SELECT * FROM {table};')[0], key=lambda row: row['id'])
                for table in tables}

    before = snapshot()
    monkeypatch.setattr(candidate_vectors, 'MAX_REQUEST_INPUTS', 2)
    monkeypatch.setattr(candidate_vectors, 'status', lambda _: {'model': {'embedding_identity': 'new'}})
    calls = []
    original = HTTPError('http://fixture/predict', 422, 'Unprocessable Entity', {},
                         BytesIO(b'{"detail":"input exceeds token limit"}'))

    class Client:
        def __init__(self, machine): pass
        def embed(self, inputs, *, timeout):
            calls.append(inputs)
            if len(calls) == failed_request:
                raise original
            return {'embedding_identity': 'new', 'vectors': [[1.0, 0.0] for _ in inputs]}

    monkeypatch.setattr(candidate_vectors, 'EmbeddingClient', Client)
    with pytest.raises(HTTPError) as failure:
        memory.apply(batch)
    assert failure.value is original
    assert len(calls) == failed_request
    notes = '\n'.join(original.__notes__)
    member_key = batch['members'][2 if failed_request == 2 else 0]['id'].split(':', 1)[1]
    assert 'guide.md' in notes and member_key in notes
    assert snapshot() == before


def test_correction_without_replacement_excludes_known_error(memory):
    initial = freeze([batch_for(memory, '# 数据库\n错误条件。\n\n# 保留\n资料必须保留。\n')])
    memory.apply(initial)
    storage = initial['members'][2]['id']
    expected = memory.prepare(['guide.md'])['expected']
    memory.apply(freeze([{'sources': [], 'expected': expected,
                  'corrections': [{'id': 'known_error', 'target': storage, 'reason': '已知错误'}]}]))
    assert memory.read(storage)['member']['stale'] is True
    assert storage not in {item['id'] for item in memory.search('错误条件', literal=True)}
    assert memory.neighbors('node:local')['record']['stale'] is True
    previous = memory._execute('SELECT * FROM ONLY change:known_error;')[0]['previous']
    assert previous['stale'] is False

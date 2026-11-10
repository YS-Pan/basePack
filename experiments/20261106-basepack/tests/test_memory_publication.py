"""Publication isolation and task-scoped cancellation regressions."""
from copy import deepcopy
from threading import Event, Thread

import pytest

from basepack.memory import candidate_vectors
from basepack.memory.maintenance import MaintenanceStopped, stop
from test_memory_store import batch_for, memory


def test_change_detection_cannot_invalidate_a_newer_accept(memory, monkeypatch):
    from basepack.memory import store
    memory.apply(batch_for(memory, '# 数据库\n旧条件。\n\n# 保留\n资料必须保留。\n'))
    new_batch = batch_for(memory, '# 数据库\n新条件。\n\n# 保留\n资料必须保留。\n')
    original = store.detect_changes

    def interleaved(*args, **kwargs):
        detected = original(*args, **kwargs)
        memory.apply(new_batch)
        return detected

    monkeypatch.setattr(store, 'detect_changes', interleaved)
    assert memory.changes(['guide.md'])[0]['kind'] == 'modified'
    current = memory.read('storage')['member']
    assert current['stale'] is False
    assert '新条件' in current['text']


@pytest.mark.parametrize('event', ['stop', 'change'])
def test_candidate_not_published_after_stop_or_source_change(memory, tmp_path, monkeypatch, event):
    memory.apply(batch_for(memory, '# 数据库\n旧条件。\n\n# 保留\n资料必须保留。\n'))
    batch = batch_for(memory, '# 数据库\n新条件。\n\n# 保留\n资料必须保留。\n')
    old = deepcopy(memory.read('storage')['member'])
    memory.config.raw['memory']['search_mode'] = 'vector'
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
    assert memory.read('storage')['member'] == old
    if event == 'stop':
        stop(control)
    else:
        (memory.config.root / 'guide.md').write_text('changed during encoding\n', encoding='utf-8')
    release.set()
    worker.join(10)
    assert not worker.is_alive()
    assert len(failures) == 1
    assert isinstance(failures[0], MaintenanceStopped if event == 'stop' else ValueError)
    assert memory.read('storage')['member'] == old


def test_candidate_vectors_are_published_together_and_reused(memory, monkeypatch):
    memory.apply(batch_for(memory, '# 数据库\n旧条件。\n\n# 保留\n资料必须保留。\n'))
    batch = batch_for(memory, '# 数据库\n新条件。\n\n# 保留\n资料必须保留。\n')
    memory.config.raw['memory']['search_mode'] = 'vector'
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
    batch['expected'] = memory.prepare(['guide.md'])['expected']
    memory.apply(batch)
    assert len(calls) == 1


def test_correction_without_replacement_excludes_known_error(memory):
    memory.apply(batch_for(memory, '# 数据库\n错误条件。\n\n# 保留\n资料必须保留。\n'))
    expected = memory.prepare(['guide.md'])['expected']
    memory.apply({'sources': [], 'expected': expected,
                  'corrections': [{'id': 'known_error', 'target': 'member:storage', 'reason': '已知错误'}]})
    assert memory.read('storage')['member']['stale'] is True
    assert 'member:storage' not in {item['id'] for item in memory.search('错误条件', literal=True)}
    assert memory.neighbors('node:local')['record']['stale'] is True
    previous = memory._execute('SELECT * FROM ONLY change:known_error;')[0]['previous']
    assert previous['stale'] is False

"""Complete large originals stay atomic, byte-exact, and natively restorable."""

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
from uuid import uuid4

import pytest

from basepack.memory.draft import freeze
from basepack.memory.store import Memory
from test_memory_sql_transactions import trace
from test_memory_store import memory


def large_text(size):
    unit = '数🚀\\"\t'
    prefix, suffix = 'Header\r\n', '\r\nEnd\r\n'
    remaining = size - len((prefix + suffix).encode('utf-8'))
    count, padding = divmod(remaining, len(unit.encode('utf-8')))
    return prefix + unit * count + 'x' * padding + suffix


def source_draft(memory, text):
    (memory.config.root / 'large.json').write_bytes(text.encode('utf-8'))
    prepared = memory.prepare(['large.json'])
    return prepared, {'sources': [{'path': 'large.json', 'revision': prepared['sources'][0]['revision']}],
                      'expected': prepared['expected'],
                      'members': [{'kind': 'chunk', 'path': 'large.json', 'start_line': 1, 'end_line': 1,
                                   'title': 'Header'}]}


@pytest.mark.parametrize('size', [3_901_650, 8_441_182, 8_943_755])
def test_large_original_complete_read_and_native_restore(memory, monkeypatch, tmp_path, size):
    text = large_text(size)
    assert len(text.encode('utf-8')) == size
    prepared, draft = source_draft(memory, text)
    transport = prepared['sources'][0]['snapshot_transport']
    assert transport['original_bytes'] == size
    assert transport['encoded_snapshot_bytes'] > transport['message_limit_bytes']
    assert transport['statement_count'] > 2
    messages = trace(monkeypatch)
    batch = freeze([draft], config=memory.config)
    result = memory.apply(batch)
    assert result['sources'] == result['members'] == 1
    assert memory.apply(batch) == result
    queries = [(message, wire_size) for message, wire_size in messages if message['method'] == 'query']
    assert len(queries) > 1
    assert all(wire_size <= 2112 * 1024 for _, wire_size in queries)
    assert len({message['txn'] for message, _ in queries}) == 1
    identity = batch['members'][0]['id']
    original = memory.read(identity)['original']
    version = original['source_version']
    complete = memory.read(identity, source_version=version, start_line=1, end_line=3)['original']
    assert complete['text'] == text
    assert sha256(complete['text'].encode('utf-8')).hexdigest() == complete['revision']
    assert memory.prepare(['large.json'])['sources'][0]['previous']['revision'] == complete['revision']
    if size != 8_943_755:
        return

    # A new batch accepting the same snapshot resets its transport accumulator.
    draft['expected'] = memory.prepare(['large.json'])['expected']
    draft['members'][0]['id'] = identity
    memory.apply(freeze([draft], config=memory.config))
    assert memory.read(identity, source_version=version, start_line=1, end_line=3)['original']['text'] == text
    environment = os.environ.copy()
    environment.update(SURREAL_USER=memory.connection['username'],
                       SURREAL_PASS=memory.config.memory_password_file.read_text(encoding='utf-8'))
    if 'BASEPACK_MEMORY_TEST_SURREAL' not in os.environ:
        pytest.skip('native restore requires BASEPACK_MEMORY_TEST_SURREAL')
    executable = Path(os.environ['BASEPACK_MEMORY_TEST_SURREAL'])
    export = tmp_path / 'large-source.surql'
    common = ['--endpoint', memory.connection['endpoint'], '--namespace', memory.connection['namespace']]
    subprocess.run([str(executable), 'export', *common, '--database', memory.connection['database'], str(export)],
                   env=environment, check=True, capture_output=True)
    restored_raw = deepcopy(memory.config.raw)
    restored_raw['memory']['database'] += '_restored_' + uuid4().hex
    subprocess.run([str(executable), 'import', *common, '--database', restored_raw['memory']['database'], str(export)],
                   env=environment, check=True, capture_output=True)
    restored = Memory(replace(memory.config, raw=restored_raw))
    assert restored.read(identity, source_version=version, start_line=1, end_line=3)['original'] == complete
    assert restored.apply(batch) == result


def test_large_original_failure_during_append_rolls_back(memory, monkeypatch):
    _, draft = source_draft(memory, large_text(3_901_650))
    publish = memory._publish

    def fail_after_append(statements, **kwargs):
        position = next(index for index, statement in enumerate(statements) if 'SET text +=' in statement)
        statements.insert(position + 1, "THROW 'deliberate original append failure';")
        return publish(statements, **kwargs)

    monkeypatch.setattr(memory, '_publish', fail_after_append)
    with pytest.raises(RuntimeError, match='deliberate original append failure'):
        memory.apply(freeze([draft], config=memory.config))
    for table in ('source', 'source_version', 'member', 'change'):
        assert memory._rows(table) == []


@pytest.mark.parametrize('missing', ['start_line', 'end_line'])
def test_freeze_reports_author_member_and_missing_line_field(missing):
    item = {'id': 'member:' + uuid4().hex, 'kind': 'chunk', 'path': 'source.md',
            'start_line': 1, 'end_line': 2}
    del item[missing]
    with pytest.raises(ValueError, match=rf'drafts\[0\]\.members\[0\].*{item["id"]}.*{missing}'):
        freeze([{'sources': [], 'members': [item]}])


def test_prepare_retains_transport_error_with_path_and_encoded_size(tmp_path, monkeypatch):
    memory = object.__new__(Memory)
    memory.config = SimpleNamespace(root=tmp_path, raw={'memory': {}})
    memory._rows = lambda _: []
    (tmp_path / 'source.md').write_bytes(b'original\r\n')
    original = ValueError('original snapshot capacity error')

    def reject(*args):
        raise original

    monkeypatch.setattr('basepack.memory.store._snapshot_sql', reject)
    with pytest.raises(ValueError) as caught:
        memory.prepare(['source.md'])
    assert caught.value is original
    note = '\n'.join(original.__notes__)
    assert 'source.md' in note and '10 original bytes' in note and 'encoded snapshot bytes' in note

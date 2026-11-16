"""Completed-assignment publication and recovery of its local projection."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from basepack.memory import publish
from basepack.memory.cli import dispatch, register_commands
from basepack.memory.draft import freeze_file
from test_memory_store import memory


def completed_file(tmp_path, draft, *, name='draft.json', assignment='reader-0/assignment-1'):
    path = tmp_path / name
    path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'path': str(path), 'file_sha256': sha256(path.read_bytes()).hexdigest(),
            'assignment': assignment}


def completed_source(memory, tmp_path):
    (memory.config.root / 'one.md').write_bytes(b'line one\nline two\n')
    source = memory.prepare(['one.md'])['sources'][0]
    return [completed_file(tmp_path, {
        'sources': [{'path': source['path'], 'revision': source['revision']}],
        'members': [{'kind': 'chunk', 'path': 'one.md', 'start_line': 1, 'end_line': 1,
                     'title': 'First line'}]})]


def paths(tmp_path):
    return {'output': tmp_path / 'frozen.json', 'result': tmp_path / 'result.json',
            'control': str(tmp_path / 'owner.control')}


@pytest.fixture
def publication_paths(memory, tmp_path):
    from basepack.memory.owner import acquire, release, stop_owned

    files = paths(tmp_path)
    claim = acquire(memory.config.memory_dir, memory.connection['project_id'], 'publish test', files['control'])
    assert claim['acquired']
    yield files
    stop_owned(memory.config.memory_dir, files['control'])
    release(memory.config.memory_dir, files['control'])


def test_completed_drafts_keep_order_scopes_and_receipt_details(tmp_path):
    completed = [completed_file(tmp_path, {'sources': [], 'members': [{'kind': 'chunk', 'start_line': 1, 'end_line': 1}]}, name='a.json'),
                 completed_file(tmp_path, {'sources': [], 'members': [{'kind': 'chunk', 'start_line': 1, 'end_line': 1}],
                     'edges': [{'id': 'edge', 'in': {'draft': 0, 'member': 0}, 'out': {'member': 0},
                                'evidence': [{'draft': 0, 'member': 0}, {'member': 0}]}]}, name='b.json')]
    files = paths(tmp_path)
    applied = {'sources': 0, 'members': 2, 'nodes': 0, 'edges': 1, 'invalidated': ['member:old']}
    calls = []

    def apply(batch, **kwargs):
        assert json.loads(files['output'].read_text(encoding='utf-8')) == batch
        calls.append((batch, kwargs))
        return applied

    summary = publish(SimpleNamespace(apply=apply, config=None), completed=completed, **files, timeout=42)
    batch, kwargs = calls[0]
    a, b = [member['id'] for member in batch['members']]
    assert a != b and batch['edges'][0]['in'] == a and batch['edges'][0]['out'] == b
    assert batch['edges'][0]['evidence'] == [a, b]
    assert kwargs == {'control': files['control'], 'timeout': 42}
    assert summary == {'batch_id': batch['batch_id'], 'frozen': str(files['output']),
                       'result': str(files['result']), 'sources': 0, 'members': 2, 'nodes': 0,
                       'edges': 1, 'invalidated': 1}
    receipt = json.loads(files['result'].read_text(encoding='utf-8'))
    assert receipt['completed'] == completed and receipt['apply'] == applied
    assert receipt['frozen_file_sha256'] == sha256(files['output'].read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        publish(SimpleNamespace(apply=apply, config=None), completed=completed, **files)
    assert len(calls) == 1


def test_hash_mismatch_keeps_affected_position_and_publishes_nothing(tmp_path):
    completed = [completed_file(tmp_path, {'sources': []})]
    Path(completed[0]['path']).write_text('{"sources": [], "members": []}', encoding='utf-8')
    files = paths(tmp_path)
    with pytest.raises(ValueError, match=r'completed\[0\].*SHA256 mismatch.*draft.json'):
        publish(SimpleNamespace(apply=lambda *a, **kw: pytest.fail('applied changed draft')),
                completed=completed, **files)
    assert not files['output'].exists() and not files['result'].exists()


def test_existing_scope_validation_runs_before_save_or_apply(tmp_path):
    completed = [completed_file(tmp_path, {'sources': [], 'members': [
        {'kind': 'chunk', 'start_line': 1, 'end_line': 1, 'evidence': [{'draft': 1, 'member': 0}]}]})]
    files = paths(tmp_path)
    with pytest.raises(ValueError, match='Draft index out of range'):
        publish(SimpleNamespace(config=None, apply=lambda *a, **kw: pytest.fail('applied invalid draft')),
                completed=completed, **files)
    assert not files['output'].exists()


def test_powershell_uppercase_file_hash_is_accepted_and_normalized(tmp_path):
    reference = completed_file(tmp_path, {'sources': []})
    reference['file_sha256'] = reference['file_sha256'].upper()
    files = paths(tmp_path)
    applied = {'sources': 0, 'members': 0, 'nodes': 0, 'edges': 0, 'invalidated': []}
    publish(SimpleNamespace(config=None, apply=lambda *a, **kw: applied), completed=[reference], **files)
    saved = json.loads(files['result'].read_text(encoding='utf-8'))
    assert saved['completed'][0]['file_sha256'] == reference['file_sha256'].lower()


def test_original_apply_error_leaves_fixed_batch_for_explicit_resume(tmp_path):
    completed = [completed_file(tmp_path, {'sources': [], 'members': [{'kind': 'chunk', 'start_line': 1, 'end_line': 1}]})]
    original = RuntimeError('publication result unknown: preserve marker and owner')

    def fail(*a, **kw):
        raise original

    files = paths(tmp_path)
    with pytest.raises(RuntimeError) as raised:
        publish(SimpleNamespace(config=None, apply=fail), completed=completed, **files)
    assert raised.value is original and files['output'].exists() and not files['result'].exists()


def test_result_projection_cannot_overwrite_fixed_batch(tmp_path):
    frozen = tmp_path / 'frozen.json'
    batch = freeze_file([{'sources': []}], frozen)
    with pytest.raises(ValueError, match='different path'):
        publish(SimpleNamespace(apply=lambda *a, **kw: pytest.fail('applied path collision')),
                frozen=frozen, result=frozen, control='owner.control')
    assert json.loads(frozen.read_text(encoding='utf-8')) == batch


def test_same_frozen_resumes_database_receipt_with_original_ids(memory, tmp_path, publication_paths):
    files = publication_paths
    first = publish(memory, completed=completed_source(memory, tmp_path), **files)
    material = files['output'].read_bytes()
    batch = json.loads(material)
    # A committed receipt resolves the original batch, even after its source changes.
    (memory.config.root / 'one.md').write_text('new original\n', encoding='utf-8')
    again = publish(memory, frozen=files['output'], control=files['control'], result=files['result'])
    assert again == first and files['output'].read_bytes() == material
    assert [row['id'] for row in memory._rows('member')] == [batch['members'][0]['id']]
    receipt = json.loads(files['result'].read_text(encoding='utf-8'))
    assert receipt['batch_id'] == batch['batch_id'] and receipt['completed'] is None
    database = memory._execute(f"SELECT * FROM ONLY meta:batch_{batch['batch_id']};")[0]
    assert database['result'] == receipt['apply']
    assert database['batch_hash'] != receipt['frozen_file_sha256']


def test_result_write_failure_recovers_from_same_frozen_without_refreeze(memory, tmp_path, publication_paths):
    files = publication_paths
    blocked = tmp_path / 'result-directory'
    blocked.mkdir()
    with pytest.raises(OSError) as raised:
        publish(memory, completed=completed_source(memory, tmp_path), **dict(files, result=blocked))
    assert 'database receipt is authoritative' in '\n'.join(raised.value.__notes__)
    material = files['output'].read_bytes()
    batch = json.loads(material)
    assert len(memory._rows('member')) == 1
    summary = publish(memory, frozen=files['output'], control=files['control'], result=files['result'])
    assert summary['batch_id'] == batch['batch_id'] and files['output'].read_bytes() == material
    assert [row['id'] for row in memory._rows('member')] == [batch['members'][0]['id']]
    assert json.loads(files['result'].read_text(encoding='utf-8'))['apply']['members'] == 1


def test_cli_uses_the_python_helper_and_returns_compact_summary(tmp_path, monkeypatch):
    import importlib
    publication = importlib.import_module('basepack.memory.publish')
    completed = [completed_file(tmp_path, {'sources': []})]
    manifest = tmp_path / 'completed.json'
    manifest.write_text(json.dumps(completed), encoding='utf-8')
    memory = object()
    monkeypatch.setattr('basepack.memory.store.Memory', lambda config: memory)
    calls = []
    monkeypatch.setattr(publication, 'publish', lambda *args, **kwargs:
                        calls.append((args, kwargs)) or {'batch_id': 'summary'})
    parser = argparse.ArgumentParser()
    register_commands(parser.add_subparsers(dest='command'))
    args = parser.parse_args(['memory', 'publish', '--completed', str(manifest), '--output', 'frozen.json',
                              '--control', 'owner.control', '--result', 'result.json', '--timeout', '17'])
    assert dispatch(args, None) == ({'batch_id': 'summary'}, 0)
    assert calls == [((memory,), {'completed': completed, 'output': 'frozen.json', 'frozen': None,
                                 'control': 'owner.control', 'result': 'result.json', 'timeout': 17})]
    args = parser.parse_args(['memory', 'publish', '--frozen', 'frozen.json', '--control', 'owner.control',
                              '--result', 'result.json'])
    assert dispatch(args, None) == ({'batch_id': 'summary'}, 0)
    assert calls[-1][1]['completed'] is None and calls[-1][1]['output'] is None

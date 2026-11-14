"""UUID draft scopes and publication behavior against a disposable database."""

import os
import re
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from basepack.memory.draft import freeze, validate_batch
from basepack.memory.store import Memory, SqlResponseError
from basepack.project.config import MachineConfig, ProjectConfig
from test_memory_store import DeterministicEmbeddingClient, EMBEDDING_IDENTITY


def test_scoped_drafts_allocate_distinct_ids_and_resolve_references():
    drafts = [
        {'sources': [{'path': 'a', 'revision': 'a'}], 'expected': {}, 'members': [
            {'kind': 'chunk'}, {'kind': 'file', 'parent': {'member': 0}, 'evidence': [{'member': 0}]}]},
        {'sources': [{'path': 'b', 'revision': 'b'}], 'expected': {}, 'members': [{'kind': 'chunk'}],
         'edges': [{'id': 'link', 'in': {'draft': 0, 'member': 0}, 'out': {'member': 0},
                    'evidence': [{'draft': 0, 'member': 0}, {'member': 0}]}]},
    ]
    frozen = freeze(drafts)
    validate_batch(frozen)
    ids = [item['id'] for item in frozen['members']]
    assert len(set(ids)) == 3 and all(re.fullmatch(r'member:[0-9a-f]{32}', value) for value in ids)
    assert frozen['members'][1]['parent'] == ids[0]
    assert frozen['edges'][0]['in'] == ids[0] and frozen['edges'][0]['out'] == ids[2]
    assert frozen['edges'][0]['evidence'] == [ids[0], ids[2]]
    assert 'id' not in drafts[0]['members'][0]
    with pytest.raises(ValueError, match='out of range'):
        freeze([{'sources': [], 'members': [{'evidence': [{'member': 2}]}]}])


def test_old_payload_and_duplicate_updates_are_rejected():
    with pytest.raises(ValueError, match='frozen protocol'):
        validate_batch({'sources': [], 'members': [{'id': 'old'}]})
    draft = {'sources': [], 'expected': {}, 'members': [{'kind': 'chunk'}]}
    frozen = freeze([draft])
    frozen['members'].append(deepcopy(frozen['members'][0]))
    with pytest.raises(ValueError, match='Duplicate'):
        validate_batch(frozen)
    with pytest.raises(ValueError, match='Unknown draft fields'):
        freeze([{'sources': [], 'dispositions': []}])


def test_freeze_command_persists_mapping_once(tmp_path):
    import json
    from basepack.memory.cli import dispatch

    draft = tmp_path / 'draft.json'
    output = tmp_path / 'batch.json'
    draft.write_text(json.dumps({'sources': [], 'members': [{'kind': 'chunk'}]}), encoding='utf-8')
    args = SimpleNamespace(memory_action='freeze', drafts=[str(draft)], output=str(output))
    result, status = dispatch(args, None)
    stored = json.loads(output.read_text(encoding='utf-8'))
    assert status == 0 and result['batch_id'] == stored['batch_id']
    assert stored['member_mapping'] == [{'draft': 0, 'member': 0, 'id': stored['members'][0]['id']}]
    with pytest.raises(FileExistsError):
        dispatch(args, None)
    assert json.loads(output.read_text(encoding='utf-8')) == stored


@pytest.fixture
def memory(tmp_path, monkeypatch):
    if 'BASEPACK_MEMORY_TEST_ENDPOINT' not in os.environ:
        pytest.skip('requires a disposable SurrealDB endpoint')
    from basepack.memory import candidate_vectors
    monkeypatch.setattr(candidate_vectors, 'EmbeddingClient', DeterministicEmbeddingClient)
    monkeypatch.setattr(candidate_vectors, 'status', lambda _: {'model': {'embedding_identity': EMBEDDING_IDENTITY}})
    config = ProjectConfig(tmp_path / 'project.toml', Path(sys.executable), tmp_path,
        {'memory': {'data_dir': '.basepack/memory', 'search_mode': 'vector', 'project_id': uuid4().hex,
                    'endpoint': os.environ['BASEPACK_MEMORY_TEST_ENDPOINT'], 'username': 'root',
                    'password_file': os.environ['BASEPACK_MEMORY_TEST_PASSWORD_FILE'],
                    'namespace': 'identity_tests', 'database': 'i' + uuid4().hex}},
        MachineConfig(tmp_path / 'machine.toml', {}))
    memory = Memory(config)
    memory.install_schema()
    return memory


def test_real_publication_retry_update_conflict_and_schema_gate(memory):
    (memory.config.root / 'one.md').write_bytes(b'line one\nline two\n')
    prepared = memory.prepare(['one.md'])
    draft = {'sources': [{'path': 'one.md', 'revision': prepared['sources'][0]['revision']}],
             'expected': prepared['expected'], 'members': [
                 {'kind': 'file', 'path': 'one.md', 'start_line': 1, 'end_line': 2,
                  'title': 'same', 'text': 'Both lines', 'evidence': [{'member': 1}]},
                 {'kind': 'chunk', 'path': 'one.md', 'start_line': 1, 'end_line': 1,
                  'title': 'same', 'parent': {'member': 0}}]}
    batch = freeze([draft])
    first = memory.apply(batch)
    ids = [entry['id'] for entry in batch['members']]
    assert first == memory.apply(batch)
    assert len(memory._rows('member')) == 2
    assert memory.read(ids[1])['original']['text'] == 'line one\n'
    assert memory.neighbors(ids[1])['parent']['id'] == ids[0]
    prepared = memory.prepare(['one.md'])
    update = deepcopy(draft)
    update['expected'] = prepared['expected']
    update['members'] = [dict(draft['members'][0], id=ids[0], text='Updated', evidence=[ids[1]])]
    a, b = freeze([update]), freeze([update])
    memory.apply(a)
    with pytest.raises((RuntimeError, SqlResponseError), match='revision changed'):
        memory.apply(b)
    assert len(memory._rows('member')) == 2
    with pytest.raises(ValueError, match='different content'):
        changed = deepcopy(batch)
        changed['context'] = {'changed': True}
        memory.apply(changed)
    memory._execute('UPDATE meta:project UNSET member_identity_version;', check_project=False)
    with pytest.raises(SqlResponseError, match='migration required'):
        memory.prepare(['one.md'])
    with pytest.raises(SqlResponseError, match='migration required'):
        memory._execute("CREATE feedback:gate_probe SET issue='must not publish';")
    assert memory._execute('SELECT * FROM ONLY feedback:gate_probe;', check_project=False)[0] is None
    with pytest.raises(RuntimeError, match='migration required'):
        memory._publish(['BEGIN;', "CREATE feedback:gate_probe SET issue='must not publish';", 'COMMIT;'])
    assert memory._execute('SELECT * FROM ONLY feedback:gate_probe;', check_project=False)[0] is None
    with pytest.raises(SqlResponseError, match='migration required'):
        memory.install_schema()
    assert memory._execute('SELECT member_identity_version FROM ONLY meta:project;',
                           check_project=False)[0]['member_identity_version'] is None


def test_real_cross_reader_graph_and_duplicate_update_leave_no_partial_write(memory):
    for name in ('a.md', 'b.md'):
        (memory.config.root / name).write_bytes(b'Identical name and text\n')
    prepared = memory.prepare(['a.md', 'b.md'])
    drafts = []
    for source in prepared['sources']:
        drafts.append({'sources': [{'path': source['path'], 'revision': source['revision']}],
                       'expected': prepared['expected'], 'members': [
                           {'kind': 'chunk', 'path': source['path'], 'title': 'same',
                            'start_line': 1, 'end_line': 1}]})
    drafts[1]['edges'] = [{'id': 'link', 'in': {'draft': 0, 'member': 0}, 'out': {'member': 0},
                           'kind': 'supports', 'text': 'Related',
                           'evidence': [{'draft': 0, 'member': 0}, {'member': 0}]}]
    frozen = freeze(drafts)
    ids = [entry['id'] for entry in frozen['members']]
    assert ids[0] != ids[1]
    memory.apply(frozen)
    edge = memory._rows('semantic')[0]
    assert edge['in'] == ids[0] and edge['out'] == ids[1]
    assert [entry['member'] for entry in edge['basis']] == ids
    assert [edge['endpoint_versions'][side]['id'] for side in ('in', 'out')] == ids
    before = memory._rows('member')
    prepared = memory.prepare(['a.md'])
    update = deepcopy(drafts[0])
    update['expected'] = prepared['expected']
    update['members'][0]['id'] = ids[0]
    update['members'].append(deepcopy(update['members'][0]))
    with pytest.raises(ValueError, match='Duplicate'):
        memory.apply(freeze([update]))
    assert memory._rows('member') == before


def test_same_source_identity_cannot_be_written_twice(memory):
    for name in ('a.md', 'b.md'):
        (memory.config.root / name).write_bytes(b'Same original\n')
    prepared = memory.prepare(['a.md'])
    source = prepared['sources'][0]
    memory.apply(freeze([{'sources': [{'path': 'a.md', 'revision': source['revision']}]}]))
    identity = memory.sources()[0]['id']
    same_id = [{'sources': [{'id': identity, 'path': name, 'revision': source['revision']}]}
               for name in ('a.md', 'b.md')]
    with pytest.raises(ValueError, match='Duplicate source identity'):
        freeze(same_id)
    # One source identifies the same record through its existing path instead.
    batch = freeze([{'sources': [{'path': 'a.md', 'revision': source['revision']}]}, same_id[1]])
    before = memory.sources()
    with pytest.raises(ValueError, match='Duplicate source identity'):
        memory.apply(batch)
    assert memory.sources() == before

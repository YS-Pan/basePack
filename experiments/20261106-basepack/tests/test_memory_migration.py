from basepack.memory.migration import expected


def test_legacy_knowledge_keeps_unknown_entry_and_original_fields():
    original = {'id': 'knowledge_version:a', 'born_event': 0, 'record': {'private': True}}
    result = expected('knowledge_version', original)
    assert result == {**original, 'j_enter': None, 'observed_j': 0, 'age_origin': 'legacy_cutover'}
    assert 'j_enter' not in original


def test_legacy_delivery_preserves_context_and_sequence_without_new_j():
    original = {'event': 7, 'context': {'query': 'known legacy fact'}, 'items': [{'id': 'member:a'}]}
    result = expected('delivery', original)
    assert result == {**original, 'legacy_event': 7, 'legacy_context': original['context'],
                      'context': None, 'j': None, 'legacy': True}


def test_finalize_rejects_nonzero_head_and_existing_marker(tmp_path, monkeypatch):
    import os
    import sys
    from pathlib import Path
    from uuid import uuid4
    import pytest
    from basepack.memory import migration
    from basepack.memory.store import Memory, SqlResponseError, _sql
    from basepack.project.config import MachineConfig, ProjectConfig

    endpoint = os.environ.get('BASEPACK_MEMORY_TEST_ENDPOINT')
    if not endpoint:
        pytest.skip('requires a disposable SurrealDB server')
    database = 'migration_finalize_' + uuid4().hex
    config = ProjectConfig(tmp_path / 'project.toml', Path(sys.executable), tmp_path,
        {'memory': {'data_dir': '.basepack/memory', 'project_id': 'migration_test',
                    'endpoint': endpoint, 'username': 'root',
                    'password_file': os.environ['BASEPACK_MEMORY_TEST_PASSWORD_FILE'],
                    'namespace': os.environ.get('BASEPACK_MEMORY_TEST_NAMESPACE', 'identity_tests'),
                    'database': database}}, MachineConfig(tmp_path / 'machine.toml', {}))
    memory = Memory(config)
    memory._execute(f'DEFINE DATABASE {database}; DEFINE TABLE meta SCHEMALESS; '
                    f'UPSERT meta:project SET project_id={_sql("migration_test")}, member_identity_version=2; '
                    'UPSERT meta:delivery SET j=1;', check_project=False)
    class LegacyConnection:
        def _execute(self, sql):
            return memory._execute(sql, check_project=False)
    target = LegacyConnection()
    monkeypatch.setattr(migration, 'verify', lambda source, dest: {'status': 'verified'})
    try:
        with pytest.raises(SqlResponseError, match='Migration handoff precondition failed'):
            migration.finalize(None, target)
        assert target._execute('SELECT memory_schema_version FROM ONLY meta:project;')[0].get('memory_schema_version') is None
        target._execute('UPDATE meta:delivery SET j=0;')
        assert migration.finalize(None, target)['handoff_marker'] == 3
        with pytest.raises(SqlResponseError, match='Migration handoff precondition failed'):
            migration.finalize(None, target)
    finally:
        memory._execute(f'REMOVE DATABASE {database};', check_project=False)

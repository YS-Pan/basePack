"""One-time schema 3 data bridge for an isolated native restore.

Run with the retained 0.16 client; never point this utility at a live store.
The native import and schema installation are separate cutover steps.
"""
import argparse
from dataclasses import replace
import json
from pathlib import Path
from urllib.parse import urlsplit

from basepack.memory.store import Memory, _record, _sql
from basepack.project.config import load_project_config

TABLES = ('meta', 'source', 'source_version', 'member', 'node', 'semantic',
          'change', 'knowledge_version', 'access_state', 'delivery', 'feedback')


def expected(table, row):
    row = dict(row)
    if table == 'knowledge_version':
        row.update(j_enter=None, observed_j=0, age_origin='legacy_cutover')
    elif table == 'delivery':
        row.update(legacy_event=row['event'], legacy_context=row.get('context'),
                   context=None, j=None, legacy=True)
    return row


def check_pair(source, target):
    a, b = source.connection, target.connection
    if a['endpoint'].rstrip('/') == b['endpoint'].rstrip('/'):
        raise ValueError('Source and destination require independent physical servers')
    if set(source._execute('INFO FOR DB;')[0]['tables']) != set(TABLES):
        raise ValueError('Unexpected source tables; inspect before migration')
    if set(target._execute('INFO FOR DB;')[0]['tables']) != set(TABLES):
        raise ValueError('Unexpected destination tables; inspect before migration')
    project = target._execute('SELECT * FROM ONLY meta:project;')[0]
    if project.get('member_identity_version') != 2:
        raise ValueError('Expected member identity version 2')
    if target._execute('SELECT * FROM ONLY meta:delivery;')[0] is not None:
        raise ValueError('Destination is not an untouched legacy import')
    checks = target._execute("SELECT count() AS n FROM knowledge_version WHERE j_enter != NONE OR observed_j != NONE OR age_origin != NONE GROUP ALL; SELECT count() AS n FROM delivery WHERE j != NONE OR legacy != NONE OR legacy_event != NONE OR legacy_context != NONE GROUP ALL;")
    if any(rows and rows[0]['n'] for rows in checks):
        raise ValueError('Destination contains new migration fields')


def migrate(source, target):
    check_pair(source, target)
    target._execute("""BEGIN;
UPDATE knowledge_version SET j_enter=NULL, observed_j=0, age_origin='legacy_cutover';
UPDATE delivery SET legacy_event=event, legacy_context=context, context=NULL, j=NULL, legacy=true;
CREATE meta:delivery SET j=0;
COMMIT;""")


def verify(source, target):
    if source.connection['endpoint'].rstrip('/') == target.connection['endpoint'].rstrip('/'):
        raise ValueError('Source and destination require independent physical servers')
    source_tables = set(source._execute('INFO FOR DB;')[0]['tables'])
    target_tables = set(target._execute('INFO FOR DB;')[0]['tables'])
    if source_tables != set(TABLES) or target_tables != source_tables:
        raise ValueError('Unexpected table set')
    if source._execute('INFO FOR DB;')[0] != target._execute('INFO FOR DB;')[0]:
        raise ValueError('Database schema differs')
    for table in TABLES:
        if source._execute(f'INFO FOR TABLE {table};')[0] != target._execute(f'INFO FOR TABLE {table};')[0]:
            raise ValueError(f'Table schema differs: {table}')
    if target._execute('SELECT * FROM ONLY meta:delivery;')[0] != {'id': 'meta:delivery', 'j': 0}:
        raise ValueError('Invalid new fact cursor')
    counts = {}
    for table in TABLES:
        def count(m):
            rows = m._execute(f'SELECT count() AS total FROM {table} GROUP ALL;')[0]
            return rows[0]['total'] if rows else 0
        total = count(source)
        if count(target) != total + (table == 'meta'):
            raise ValueError(f'Row count differs: {table}')
        for offset in range(0, total, 50):
            old = source._execute(f'SELECT * FROM {table} ORDER BY id LIMIT 50 START {offset};')[0]
            want = sorted((expected(table, row) for row in old), key=lambda x: x['id'])
            actual = target._execute(f'SELECT * FROM {table} WHERE id IN {_sql([_record(x["id"]) for x in want])};')[0]
            actual.sort(key=lambda x: x['id'])
            if actual != want:
                raise ValueError(f'Unexpected data difference: {table} batch {offset}')
        counts[table] = total
    return {'status': 'verified', 'source_row_counts': counts, 'added_meta': 'delivery',
            'legacy_entry': 'unknown', 'legacy_baseline': 'cutover', 'j': 0}


def finalize(source, target):
    report = verify(source, target)
    target._execute("""BEGIN;
IF meta:project.member_identity_version = NONE OR meta:project.member_identity_version != 2 OR meta:project.memory_schema_version != NONE OR meta:delivery.j = NONE OR meta:delivery.j != 0 { THROW 'Migration handoff precondition failed'; };
UPDATE meta:project SET memory_schema_version=3;
COMMIT;""")
    marker = target._execute("SELECT memory_schema_version FROM ONLY meta:project;")[0]
    if marker.get("memory_schema_version") != 3:
        raise RuntimeError("Migration marker outcome is unknown; inspect the target before retrying")
    report['handoff_marker'] = 3
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=('migrate', 'verify', 'finalize'))
    p.add_argument('config', type=Path)
    p.add_argument('source_endpoint')
    p.add_argument('target_endpoint')
    p.add_argument('--report', type=Path)
    a = p.parse_args()
    config = load_project_config(a.config)
    live = urlsplit(config.raw['memory']['endpoint'])
    endpoints = [urlsplit(a.source_endpoint), urlsplit(a.target_endpoint)]
    if any(e.scheme != 'http' or e.hostname != '127.0.0.1' or not e.port or e.path not in ('', '/') for e in endpoints):
        raise ValueError('Isolated endpoints must be explicit local HTTP ports')
    if len({live.port, *(e.port for e in endpoints)}) != 3:
        raise ValueError('Configured, source and target ports must differ')
    def isolated(endpoint):
        raw = {**config.raw, 'memory': {**config.raw['memory'], 'endpoint': endpoint}}
        return Memory(replace(config, raw=raw))
    source, target = isolated(a.source_endpoint), isolated(a.target_endpoint)
    if a.action == 'migrate':
        migrate(source, target)
    else:
        if a.report is None:
            p.error('verify requires --report')
        if a.report.exists():
            raise ValueError('Report already exists; use a new path')
        result = finalize(source, target) if a.action == 'finalize' else verify(source, target)
        with a.report.open('x', encoding='utf8') as f:
            json.dump(result, f, indent=2)
        print(json.dumps(result))


if __name__ == '__main__':
    main()

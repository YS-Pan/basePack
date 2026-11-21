import json
import os
import sys

import pytest

from basepack.__main__ import main
from basepack.memory.codex import collect_codex
from basepack.memory.freshness import _receipt, inspect_codex
from basepack.memory.prompts import memory_command
from basepack.memory.retrieval import prepare_retrieval, render_retrieval_prompt
from basepack.project.config import load_project_config
from basepack.project.init import init_project
from test_memory_store import batch_for, memory

OLD = '01a1c568-0e63-7a32-94a4-508ffc4e1156'
NEW = '01a1c568-b2e2-7c32-a246-7f631e712b4e'
RELEASE = '01a1c569-aab2-7d41-8bae-82625f8ff263'


def row(id, text):
    return {'turnId': 'turn', 'item': {'type': 'agentMessage', 'id': id, 'text': text}}


class Server:
    def __init__(self, root):
        self.root = str(root)
        self.bodies = {OLD: [row('old', 'Separate repositories and installs are required.')],
                       NEW: [row('new', f'Continue the existing distribution decision; follow codex://threads/{RELEASE}.'),
                             row('later', 'Verify the published result.')],
                       RELEASE: [row('release', 'AIGC was released successfully.')]}

    def call(self, method, params):
        if method == 'thread/list':
            chats = [(RELEASE, 'AIGC release')] if params['archived'] else [(OLD, 'migration'), (NEW, 'distribution')]
            return {'data': [{'id': id, 'cwd': self.root, 'name': name, 'updatedAt': 1}
                             for id, name in chats], 'nextCursor': None}
        id = params['threadId']
        if method == 'thread/read':
            return {'thread': {'id': id, 'cwd': self.root, 'projectId': None}}
        data = self.bodies[id]
        if params['sortDirection'] == 'desc':
            return {'data': data[-1:]}
        start = int(params.get('cursor') or 0)
        return {'data': data[start:start + 1], 'nextCursor': str(start + 1) if start + 1 < len(data) else None}

    def close(self):
        pass


@pytest.mark.parametrize('content', ['', json.dumps({'status': 'ok', 'output': 'command summary'})])
def test_receipt_ignores_newer_custom_codex_output(tmp_path, content):
    maintenance = tmp_path / 'maintenance'
    maintenance.mkdir()
    receipt = maintenance / ('codex-' + 'a' * 32 + '.json')
    data = {'binding': {'project_id': 'project'}, 'capture': {'threads': []}}
    receipt.write_text(json.dumps(data), encoding='utf-8')
    output = maintenance / 'codex-usage-plan-revised-20261115-01a1dd96.json'
    output.write_text(content, encoding='utf-8')
    os.utime(receipt, (1700000000, 1700000000))
    os.utime(output, (1700000001, 1700000001))

    assert _receipt(tmp_path, 'project') == (receipt, data)


def test_receipt_preserves_corrupt_canonical_json_error(tmp_path):
    maintenance = tmp_path / 'maintenance'
    maintenance.mkdir()
    previous = maintenance / ('codex-' + 'a' * 32 + '.json')
    previous.write_text(json.dumps({'binding': {'project_id': 'project'}, 'capture': {'threads': []}}),
                        encoding='utf-8')
    corrupt = maintenance / ('codex-' + 'b' * 32 + '.json')
    corrupt.write_text('', encoding='utf-8')
    os.utime(previous, (1700000000, 1700000000))
    os.utime(corrupt, (1700000001, 1700000001))

    with pytest.raises(json.JSONDecodeError):
        _receipt(tmp_path, 'project')


def test_distribution_capture_check_evidence_flow(tmp_path, monkeypatch, capsys):
    machine = tmp_path / 'machine.toml'
    machine.write_text('schema_version=1\n', encoding='utf-8')
    config = load_project_config(init_project(tmp_path / 'project', machine, max_concurrent_subagents=2,
                                              concurrency_source='test'))
    config.raw['memory']['codex'] = {'project_id': 'project', 'registry_complete': True, 'other_project_roots': []}
    monkeypatch.setattr('basepack.memory.freshness.discover_binding', lambda root, project_id, roots:
                        {'project_id': project_id, 'worktrees': [str(root)], 'other_roots': roots, 'gaps': []})
    server = Server(config.root)
    output = config.memory_dir / 'codex'
    capture = collect_codex('project', [OLD], output, client=server)
    receipt = config.memory_dir / 'maintenance' / ('codex-' + 'a' * 32 + '.json')
    receipt.parent.mkdir(parents=True)
    receipt.write_text(json.dumps({'binding': {'project_id': 'project'}, 'capture': capture}), encoding='utf-8')
    preflight = receipt.parent / ('a' * 32 + '.json')
    preflight.write_text(json.dumps({'codex': {'receipt': str(receipt)},
                                     'semantic': [{'path': 'chat.txt', 'reason': 'no_active_knowledge',
                                                   'uncovered_ranges': [{'start_line': 1, 'end_line': 3, 'text': 'private'}]}]}), encoding='utf-8')
    before = {p: p.read_bytes() for p in config.memory_dir.rglob('*') if p.is_file()}

    prepared = prepare_retrieval(config, question='What is the current distribution status?')
    prompt = render_retrieval_prompt(config, prepared['request'])['prompt']
    assert memory_command(config, 'check-codex-capture') in prompt and 'publication chats' in prompt
    assert 'one Auto Review for that exact invocation' in prompt
    assert 'original arguments upon approval' in prompt and 'reason and the unchecked coverage' in prompt
    inventory = inspect_codex(config, client=server)
    by_id = {item['thread_id']: item for item in inventory['threads']}
    assert by_id[NEW]['archived'] is False and by_id[RELEASE]['archived'] is True
    assert by_id[NEW]['capture_status'] == by_id[RELEASE]['capture_status'] == 'new'
    assert by_id[OLD]['captured_endpoint']['item_id'] == 'old'
    assert by_id[OLD]['capture_status'] == 'unknown'
    assert inventory['inventory']['new'] == [NEW, RELEASE]
    assert OLD in inventory['inventory']['unknown']
    assert inventory['inventory']['covered'] == []
    assert inventory['receipt_written_at'] and 'not a global' in inventory['cutoff_note']
    assert inventory['semantic_preflight']['pending_at_preflight'][0]['uncovered_ranges'] == [{'start_line': 1, 'end_line': 3}]
    assert 'snapshot only' in inventory['semantic_preflight']['note']
    checked = inspect_codex(config, thread_id=OLD, client=server)
    assert checked['inventory']['covered'] == [OLD]
    decision = checked['read']['parts'][0]
    assert decision['capture_status'] == 'captured' and 'Separate repositories' in decision['text']
    new = inspect_codex(config, thread_id=NEW, client=server)['read']['parts'][0]
    assert new['capture_status'] == 'not_captured' and RELEASE in new['text']
    release = inspect_codex(config, thread_id=RELEASE, client=server)['read']['parts'][0]
    assert release['capture_status'] == 'not_captured' and 'released successfully' in release['text']
    server.bodies[OLD].append(row('later', 'new message'))
    assert {v['thread_id']: v for v in inspect_codex(config, client=server)['threads']}[OLD]['capture_status'] == 'possibly_changed'
    server.bodies[OLD].pop()
    server.bodies[OLD][0]['item']['text'] = 'Edited even though endpoint and updatedAt are unchanged.'
    changed = inspect_codex(config, thread_id=OLD, client=server)['read']
    assert changed['parts'][0]['capture_status'] == 'changed_since_capture'
    assert OLD in inspect_codex(config, thread_id=OLD, client=server)['inventory']['possibly_changed']
    assert changed['semantic_coverage'].startswith('unknown')

    registry = tmp_path / 'registry.json'
    registry.write_text(json.dumps(config.raw['memory']['codex']), encoding='utf-8')
    monkeypatch.setattr('basepack.memory.freshness.AppServer', lambda _: server)
    results = []
    for command in ('check-codex-capture', 'freshness'):
        monkeypatch.setattr(sys, 'argv', ['basepack', '--config', str(config.path), 'memory', command,
                                         '--codex-registry', str(registry), '--thread', NEW])
        assert main() == 0
        results.append(json.loads(capsys.readouterr().out))
    assert results[0] == results[1]
    assert [part['item_id'] for part in results[0]['read']['parts']] == ['new', 'later']
    assert before == {p: p.read_bytes() for p in config.memory_dir.rglob('*') if p.is_file()}


def test_file_check_stays_available_after_codex_state_access_is_denied(memory, monkeypatch, capsys):
    from basepack.memory.draft import freeze

    original = '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n'
    config = memory.config
    memory.apply(freeze([batch_for(memory, original)]))
    config.raw['memory']['codex'] = {'project_id': 'project', 'registry_complete': True, 'other_project_roots': []}
    monkeypatch.setattr('basepack.project.config.load_project_config', lambda _: config)

    def blocked(_):
        raise PermissionError('Codex state database denied')

    monkeypatch.setattr('basepack.memory.freshness.AppServer', blocked)
    for command in ('check-codex-capture', 'freshness'):
        monkeypatch.setattr(sys, 'argv', ['basepack', '--config', str(config.path), 'memory', command])
        with pytest.raises(PermissionError, match='Codex state database denied'):
            main()

    path = config.root / 'guide.md'
    previous = path.stat()
    path.write_bytes(original.replace('保留', '缓存').encode('utf-8'))
    os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    (config.root / 'outside.md').write_text('outside scope', encoding='utf-8')
    command_prefix = ['basepack', '--config', str(config.path), 'memory']
    monkeypatch.setattr(sys, 'argv', command_prefix + ['check-file-changes', '--scope', 'guide.md'])
    assert main() == 0
    assert json.loads(capsys.readouterr().out) == []
    results = []
    for command in ('check-file-changes', 'changes'):
        monkeypatch.setattr(sys, 'argv', command_prefix + [command, '--scope', 'guide.md', '--deep'])
        assert main() == 0
        results.append(json.loads(capsys.readouterr().out))
    assert results[0] == results[1]
    assert [(result['path'], result['kind']) for result in results[0]] == [('guide.md', 'modified')]

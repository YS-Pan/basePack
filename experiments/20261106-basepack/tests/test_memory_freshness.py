import json
from types import SimpleNamespace

from basepack.memory.codex import collect_codex
from basepack.memory.freshness import inspect_codex
from basepack.memory.prompts import prepare_retrieval, render_retrieval_prompt
from basepack.project.config import load_project_config
from basepack.project.init import init_project

OLD = '01a1c568-0e63-7a32-94a4-508ffc4e1156'
NEW = '01a1c568-b2e2-7c32-a246-7f631e712b4e'
RELEASE = '01a1c569-aab2-7d41-8bae-82625f8ff263'


def row(id, text):
    return {'turnId': 'turn', 'item': {'type': 'agentMessage', 'id': id, 'text': text}}


class Server:
    def __init__(self, root):
        self.root = str(root)
        self.bodies = {OLD: [row('old', 'Separate repositories and installs are required.')],
                       NEW: [row('new', f'Continue the existing distribution decision; follow codex://threads/{RELEASE}.')],
                       RELEASE: [row('release', 'AIGC was released successfully.')]}

    def call(self, method, params):
        if method == 'thread/list':
            return {'data': [] if params['archived'] else [
                {'id': id, 'cwd': self.root, 'name': name, 'updatedAt': 1}
                for id, name in [(OLD, 'migration'), (NEW, 'distribution'), (RELEASE, 'AIGC release')]], 'nextCursor': None}
        id = params['threadId']
        if method == 'thread/read':
            return {'thread': {'id': id, 'cwd': self.root, 'projectId': None}}
        data = self.bodies[id]
        if params['sortDirection'] == 'desc':
            return {'data': data[-1:]}
        start = int(params.get('cursor') or 0)
        return {'data': data[start:start + 1], 'nextCursor': str(start + 1) if start + 1 < len(data) else None}


def test_distribution_freshness_evidence_flow(tmp_path, monkeypatch):
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
    receipt = config.memory_dir / 'maintenance' / 'codex-test.json'
    receipt.parent.mkdir(parents=True)
    receipt.write_text(json.dumps({'binding': {'project_id': 'project'}, 'capture': capture}), encoding='utf-8')
    preflight = receipt.parent / ('a' * 32 + '.json')
    preflight.write_text(json.dumps({'codex': {'receipt': str(receipt)},
                                     'semantic': [{'path': 'chat.txt', 'reason': 'no_active_knowledge',
                                                   'uncovered_ranges': [{'start_line': 1, 'end_line': 3, 'text': 'private'}]}]}), encoding='utf-8')
    before = {p: p.read_bytes() for p in config.memory_dir.rglob('*') if p.is_file()}

    prepared = prepare_retrieval(config, question='What is the current distribution status?')
    prompt = render_retrieval_prompt(config, prepared['request'])['prompt']
    assert 'freshness' in prompt and 'publication chats' in prompt
    inventory = inspect_codex(config, client=server)
    by_id = {item['thread_id']: item for item in inventory['threads']}
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
    assert before == {p: p.read_bytes() for p in config.memory_dir.rglob('*') if p.is_file()}

import json
import base64
from hashlib import sha256
from pathlib import Path

import pytest

from basepack.memory.codex import SOURCE_KINDS, collect_codex, list_threads
from basepack.memory.maintenance import MaintenanceStopped, stop


THREAD = '01a1c568-0e63-7a32-94a4-508ffc4e1156'


class Server:
    def __init__(self, items, project=None):
        self.items = items
        self.project = project

    def call(self, method, params):
        if method == 'thread/read':
            return {'thread': {'id': params['threadId'], 'projectId': self.project}}
        assert method == 'thread/items/list'
        if params['sortDirection'] == 'desc':
            return {'data': self.items[-1:]}
        start = int(params.get('cursor') or 0)
        return {'data': self.items[start:start + 1],
                'nextCursor': str(start + 1) if start + 1 < len(self.items) else None}


def row(item, turn='turn-1'):
    return {'turnId': turn, 'item': item}


def records(path):
    data = Path(path).read_bytes()
    output = []
    pos = 0
    while pos < len(data):
        end = data.index(b'\n', pos)
        header = json.loads(data[pos:end])
        start = end + 1
        finish = start + header['byte_length']
        output.append((header, data[start:finish].decode('utf-8')))
        assert data[finish:finish + 1] == b'\n'
        pos = finish + 1
    return output


def test_export_pages_and_round_trip_without_text_deduplication(tmp_path):
    text = '中文🙂\n{"byte_length":999}\nno trailing newline'
    client = Server([
        row({'type': 'hookPrompt', 'id': 'hook', 'fragments': []}),
        row({'type': 'userMessage', 'id': 'a', 'content': [
            {'type': 'text', 'text': text}, {'type': 'text', 'text': 'part 2'},
            {'type': 'image', 'fileId': 'unavailable'}]}),
        row({'type': 'userMessage', 'id': 'b', 'content': [{'type': 'text', 'text': text}]}),
        row({'type': 'agentMessage', 'id': 'c', 'text': 'response'}),
    ])
    result = collect_codex('project', [THREAD], tmp_path, client=client)
    thread = result['threads'][0]
    data = records(thread['path'])
    assert [body for _, body in data] == [text, 'part 2', '', text, 'response']
    assert [header['item_id'] for header, _ in data] == ['a', 'a', 'a', 'b', 'c']
    assert data[2][0]['unavailable_part']['fileId'] == 'unavailable'
    assert len(thread['gaps']) == 1
    raw = Path(thread['path']).read_bytes()
    assert all(raw[loc['byte_start']:loc['byte_end']].decode('utf-8') == body
               for loc, (_, body) in zip(thread['locations'], data))
    assert not collect_codex('project', [THREAD], tmp_path, client=client)['threads'][0]['changed']


def test_wrong_project_and_stop_do_not_replace_source(tmp_path):
    client = Server([row({'type': 'agentMessage', 'id': 'a', 'text': 'ok'})], project='other')
    with pytest.raises(ValueError, match='another project'):
        collect_codex('project', [THREAD], tmp_path, client=client)
    assert not list(tmp_path.glob('*.txt'))
    control = tmp_path / 'control'
    stop(control)
    with pytest.raises(MaintenanceStopped):
        collect_codex('project', [THREAD], tmp_path, client=client, control=control)
    assert not list(tmp_path.glob('*.txt'))


def test_missing_captured_endpoint_is_error(tmp_path):
    class Lost(Server):
        def call(self, method, params):
            if method == 'thread/items/list' and params['sortDirection'] == 'asc':
                return {'data': [], 'nextCursor': None}
            return super().call(method, params)

    client = Lost([row({'type': 'agentMessage', 'id': 'a', 'text': 'ok'})])
    with pytest.raises(RuntimeError, match='endpoint disappeared'):
        collect_codex('project', [THREAD], tmp_path, client=client)


def test_empty_history_does_not_replace_an_existing_export(tmp_path):
    path = tmp_path / f'{THREAD}.txt'
    path.write_text('previous', encoding='utf-8')
    with pytest.raises(RuntimeError, match='history became empty'):
        collect_codex('project', [THREAD], tmp_path, client=Server([]))
    assert path.read_text(encoding='utf-8') == 'previous'


def test_empty_history_without_export_is_a_gap(tmp_path):
    result = collect_codex('project', [THREAD], tmp_path, client=Server([]))
    assert result['paths'] == []
    assert result['gaps'] == [{'thread_id': THREAD, 'reason': 'no_exportable_messages', 'item_count': 0}]


def test_tool_only_items_report_referenced_subagent(tmp_path):
    child = '01a1c568-b2e2-7c32-a246-7f631e712b4e'
    client = Server([row({'type': 'collabAgentToolCall', 'id': 'a', 'receiverThreadIds': [child]}),
                     row({'type': 'subAgentActivity', 'id': 'b', 'agentThreadId': child})])
    result = collect_codex('project', [THREAD], tmp_path, client=client)
    assert result['paths'] == []
    assert result['threads'][0]['referenced_threads'] == [child]
    assert result['gaps'] == [
        {'thread_id': THREAD, 'reason': 'no_exportable_messages', 'item_count': 2},
        {'thread_id': THREAD, 'referenced_thread_id': child, 'reason': 'referenced_subagent_parent_mismatch'},
    ]


def test_proven_subagents_are_collected_once_and_cycles_do_not_repeat(tmp_path):
    child = '01a1c568-b2e2-7c32-a246-7f631e712b4e'
    grandchild = '01a1c569-aab2-7d41-8bae-82625f8ff263'
    rows = {
        THREAD: [row({'type': 'collabAgentToolCall', 'id': 'a', 'receiverThreadIds': [child, child]}),
                 row({'type': 'agentMessage', 'id': 'b', 'text': 'root'})],
        child: [row({'type': 'subAgentActivity', 'id': 'c', 'agentThreadId': grandchild}),
                row({'type': 'agentMessage', 'id': 'd', 'text': 'child'})],
        grandchild: [row({'type': 'subAgentActivity', 'id': 'e', 'agentThreadId': THREAD}),
                     row({'type': 'agentMessage', 'id': 'f', 'text': 'grandchild'})],
    }
    parents = {THREAD: None, child: THREAD, grandchild: child}
    reads = []

    class TreeServer:
        def call(self, method, params):
            thread_id = params['threadId']
            if method == 'thread/read':
                reads.append(thread_id)
                return {'thread': {'id': thread_id, 'projectId': None, 'parentThreadId': parents[thread_id]}}
            if params['sortDirection'] == 'desc':
                return {'data': rows[thread_id][-1:]}
            return {'data': rows[thread_id], 'nextCursor': None}

    result = collect_codex('project', [THREAD], tmp_path, client=TreeServer())
    assert reads == [THREAD, child, grandchild]
    assert len(result['paths']) == 3 and not result['gaps']
    assert [item['parent_thread_id'] for item in result['threads']] == [None, THREAD, child]


def test_repeated_page_identity_is_deduplicated_without_removing_same_text(tmp_path):
    one = row({'type': 'userMessage', 'id': 'one', 'content': [{'type': 'text', 'text': 'same'}]})
    two = row({'type': 'userMessage', 'id': 'two', 'content': [{'type': 'text', 'text': 'same'}]})
    result = collect_codex('project', [THREAD], tmp_path, client=Server([one, one, two]))
    assert [header['item_id'] for header, _ in records(result['paths'][0])] == ['one', 'two']


def test_conflicting_repeated_page_identity_is_an_error(tmp_path):
    one = row({'type': 'agentMessage', 'id': 'one', 'text': 'before'})
    changed = row({'type': 'agentMessage', 'id': 'one', 'text': 'after'})
    two = row({'type': 'agentMessage', 'id': 'two', 'text': 'end'})
    with pytest.raises(RuntimeError, match='conflicting item'):
        collect_codex('project', [THREAD], tmp_path, client=Server([one, changed, two]))


def test_local_image_is_content_addressed_and_old_version_is_retained(tmp_path):
    image = tmp_path / 'user image.png'
    old_bytes = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
    new_bytes = old_bytes + b'version-2'
    image.write_bytes(old_bytes)
    output = tmp_path / '.basepack' / 'memory' / 'codex'
    client = Server([row({'type': 'userMessage', 'id': 'a', 'content': [
        {'type': 'localImage', 'path': str(image)}]})])
    first = collect_codex('project', [THREAD], output, client=client)
    assert len(first['paths']) == 2 and not first['gaps']
    old = Path(first['threads'][0]['attachments'][0])
    assert old.name == sha256(old_bytes).hexdigest() + '.png'
    assert old.read_bytes() == old_bytes
    header, _ = records(first['threads'][0]['path'])[0]
    assert header['managed_attachment'] == f'codex-attachments/{old.name}'
    image.write_bytes(new_bytes)
    second = collect_codex('project', [THREAD], output, client=client)
    new = Path(second['threads'][0]['attachments'][0])
    assert new.name == sha256(new_bytes).hexdigest() + '.png'
    assert old.read_bytes() == old_bytes and new.read_bytes() == new_bytes
    image.unlink()
    missing = collect_codex('project', [THREAD], output, client=client)
    assert missing['gaps'][0]['reason'] == 'local_image_unavailable'
    assert len(missing['paths']) == 1 and old.is_file() and new.is_file()


def test_read_rechecks_binding_before_collecting_and_preserves_old_export(tmp_path):
    own = tmp_path / 'project'
    other = own / 'other-project'
    other.mkdir(parents=True)
    output = own / '.basepack' / 'memory' / 'codex'
    output.mkdir(parents=True)
    old = output / f'{THREAD}.txt'
    old.write_text('old export', encoding='utf-8')
    binding = {'project_id': 'project', 'worktrees': [str(own)], 'other_roots': [str(other)], 'gaps': []}

    class MovedServer:
        def call(self, method, params):
            assert method == 'thread/read', 'The changed thread must not expose its items'
            return {'thread': {'id': THREAD, 'projectId': None, 'cwd': str(other)}}

    result = collect_codex('project', [THREAD], output, project_binding=binding, client=MovedServer())
    assert result['paths'] == []
    assert result['gaps'] == [{'thread_id': THREAD, 'reason': 'binding_changed',
                               'classification': 'unresolved', 'binding_reason': 'registered_project_conflict'}]
    assert old.read_text(encoding='utf-8') == 'old export'


def test_list_threads_keeps_metadata_and_pages_both_archive_states():
    class ListServer:
        def call(self, method, params):
            assert method == 'thread/list'
            assert params['sourceKinds'] == SOURCE_KINDS
            assert params['modelProviders'] == [] and params['useStateDbOnly'] is True
            if params['archived']:
                return {'data': [{'id': 'archived', 'projectId': 'p'}], 'nextCursor': None}
            if params['cursor'] is None:
                return {'data': [{'id': 'first', 'cwd': 'root'}], 'nextCursor': 'next'}
            return {'data': [{'id': 'second', 'parentThreadId': 'first'}], 'nextCursor': None}

    assert list_threads(ListServer()) == [
        {'id': 'first', 'cwd': 'root', 'archived': False},
        {'id': 'second', 'parentThreadId': 'first', 'archived': False},
        {'id': 'archived', 'projectId': 'p', 'archived': True},
    ]

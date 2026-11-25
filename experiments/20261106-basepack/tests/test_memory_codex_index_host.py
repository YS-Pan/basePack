from hashlib import sha256

import pytest

from basepack.memory.codex import AppServerError
from basepack.memory.codex_index_host import CodexDialogueError, CodexDialogueHost


OLD = '01a1c568-0e63-7a32-94a4-508ffc4e1156'
NEW = '01a1c568-0e63-7a32-94a4-508ffc4e1157'
TRIAL = '01a1c568-0e63-7a32-94a4-508ffc4e1158'


def item(identity, kind, *, turn='turn-1', **payload):
    return {'turnId': turn, 'item': {'id': identity, 'type': kind, **payload}}


def text_part(text):
    return {'type': 'text', 'text': text}


class Host:
    def __init__(self):
        self.metadata = {OLD: {'id': OLD, 'projectId': 'old'}, NEW: {'id': NEW, 'projectId': 'new'}}
        self.rows = {OLD: [], NEW: []}
        self.calls = []
        self.append_after_cutoff = []

    def call(self, method, params):
        self.calls.append((method, params))
        thread_id = params['threadId']
        if method == 'thread/read':
            assert params['includeTurns'] is False
            if thread_id not in self.metadata:
                raise AppServerError('synthetic missing host thread')
            return {'thread': self.metadata[thread_id]}
        rows = self.rows[thread_id]
        turn = params.get('turnId')
        if turn:
            rows = [row for row in rows if row['turnId'] == turn]
        if method == 'thread/items/read':
            return {'data': [row for row in rows if row['item']['id'] in params['itemIds']]}
        assert method == 'thread/items/list'
        desc = params['sortDirection'] == 'desc'
        if desc and turn is None:
            result = rows[-1:]
            rows.extend(self.append_after_cutoff)
            self.append_after_cutoff.clear()
            return {'data': result}
        cursor = params['cursor']
        if desc:
            rows = list(reversed(rows))
        if isinstance(cursor, dict):
            start = next(i for i, row in enumerate(rows) if row['item']['id'] == cursor['itemId']) + 1
        else:
            start = int(cursor or 0)
        return {'data': rows[start:start + 1], 'nextCursor': str(start + 1) if start + 1 < len(rows) else None}


def reader(client, *, authorized=None, excluded=(), private=()):
    bindings = {key: {'project_id': key, 'worktrees': [], 'other_roots': [], 'gaps': []}
                for key in ('old', 'new')}
    return CodexDialogueHost(client, bindings, {OLD: 'old', NEW: 'new'} if authorized is None else authorized,
                             excluded_thread_ids=excluded, private_thread_ids=private)


def test_capture_preserves_real_roles_parts_cutoff_and_continuation():
    client = Host()
    body = '<environment_context>quoted by the user</environment_context>\n已定🙂'
    client.rows[OLD] = [item('old-user', 'userMessage', content=[text_part(body),
                                                                {'type': 'localImage', 'path': 'discarded'},
                                                                text_part(''), text_part('否'), text_part('　\r\n')]),
                        item('hook', 'hookPrompt', fragments=[{'text': 'host injection'}]),
                        item('comment', 'agentMessage', text='是', phase='commentary'),
                        item('final', 'agentMessage', text='是', phase='final'),
                        item('tool', 'commandExecution', aggregatedOutput='never an assistant message')]
    client.rows[NEW] = [item('new-user', 'userMessage', content=[text_part('ok')])]
    client.append_after_cutoff = [item('continued', 'agentMessage', turn='turn-2', text='末段')]
    host = reader(client)
    old = host.capture(OLD)
    assert old['complete']
    assert old['cutoff'] == {'turn_id': 'turn-1', 'item_id': 'tool'}
    assert [row['text'] for row in old['parts']] == [body, '', '否', '　\r\n', '是', '是']
    assert [row['bookmark']['part'] for row in old['parts']] == [0, 2, 3, 4, 0, 0]
    assert [row['bookmark']['role'] for row in old['parts']] == ['user'] * 4 + ['assistant'] * 2
    empty, whitespace = old['parts'][1]['bookmark'], old['parts'][3]['bookmark']
    assert (empty['byte_start'], empty['byte_end'], empty['part_sha256']) == (0, 0, sha256(b'').hexdigest())
    assert (whitespace['byte_start'], whitespace['byte_end']) == (0, len('　\r\n'.encode('utf-8')))
    assert old['gaps'] == [{'thread_id': OLD, 'turn_id': 'turn-1', 'item_id': 'old-user', 'part': 1,
                            'role': 'user', 'reason': 'non_text_part', 'part_type': 'localImage'}]
    bookmark = old['parts'][0]['bookmark']
    assert bookmark['part_sha256'] == sha256(body.encode('utf-8')).hexdigest()
    assert bookmark['byte_end'] == len(body.encode('utf-8'))
    continuation = host.capture(OLD)
    assert continuation['parts'][-1]['text'] == '末段'
    assert continuation['gaps'] == old['gaps'] and continuation['complete']
    assert continuation['capture_observations'] == [{'kind': 'assistant_only_native_turns',
                                                     'assistant_only_turns': 1, 'native_user_items': 1,
                                                     'native_assistant_items': 3}]
    assert [row['text'] for row in host.capture(NEW)['parts']] == ['ok']


def test_read_checks_bytes_role_revision_and_returns_local_context():
    client = Host()
    client.rows[NEW] = [item('user', 'userMessage', content=[text_part('限制：🙂原话'), text_part('同条第二部分')]),
                        item('tool', 'commandExecution', aggregatedOutput='not a message'),
                        item('assistant', 'agentMessage', text='原答'),
                        item('later', 'agentMessage', turn='turn-2', text='别回整个线程')]
    host = reader(client)
    bookmark = host.capture(NEW)['parts'][0]['bookmark']
    start = len('限制：'.encode('utf-8'))
    selected = {**bookmark, 'byte_start': start, 'byte_end': start + len('🙂'.encode('utf-8'))}
    client.calls.clear()
    exact = host.read(selected)
    assert exact['bookmark'] == selected
    assert exact['text'] == '🙂'
    assert [row['text'] for row in exact['context']] == ['限制：🙂原话', '同条第二部分']
    assert [method for method, _ in client.calls] == ['thread/read', 'thread/items/read', 'thread/items/list']
    assert host.read({**bookmark, 'part': 1, 'part_sha256': sha256('同条第二部分'.encode('utf-8')).hexdigest(),
                      'byte_end': len('同条第二部分'.encode('utf-8'))})['context'][-1]['text'] == '原答'
    with pytest.raises(CodexDialogueError, match='invalid_utf8_boundary'):
        host.read({**selected, 'byte_start': start + 1})
    with pytest.raises(CodexDialogueError, match='host_message_role_changed'):
        host.read({**selected, 'role': 'assistant'})
    client.rows[NEW][0]['item']['content'][0]['text'] += '修订'
    with pytest.raises(CodexDialogueError, match='host_text_revision_mismatch'):
        host.read(selected)
    client.rows[NEW].pop(0)
    with pytest.raises(CodexDialogueError, match='host_item_unavailable'):
        host.read(selected)


def test_no_body_reads_when_thread_or_any_ancestor_fails_authorization():
    client = Host()
    host = reader(client, authorized={NEW: 'new'}, excluded=[TRIAL])
    with pytest.raises(CodexDialogueError, match='thread_not_authorized'):
        host.capture(OLD)
    with pytest.raises(CodexDialogueError, match='registered_codex_trial'):
        host.capture(TRIAL)
    assert client.calls == []
    client.metadata[NEW]['projectId'] = 'other'
    assert host.capture(NEW)['gaps'][0]['binding_reason'] == 'different_project_id'
    client.metadata[NEW] = {'id': NEW, 'projectId': 'new', 'forkedFromId': OLD}
    assert host.capture(NEW)['gaps'][0]['reason'] == 'ancestry_not_authorized'
    host = reader(client, private=[OLD], excluded=[TRIAL])
    assert host.capture(NEW)['gaps'][0]['reason'] == 'private_ancestry'
    client.metadata[NEW]['forkedFromId'] = TRIAL
    assert host.capture(NEW)['gaps'][0]['reason'] == 'registered_codex_trial'
    assert all(method == 'thread/read' and params['threadId'] == NEW for method, params in client.calls)

    client.calls.clear()
    client.metadata[NEW] = {'id': NEW, 'projectId': 'new', 'parentThreadId': OLD}
    client.metadata[OLD]['attachedToThreadId'] = TRIAL
    host = reader(client, excluded=[TRIAL])
    assert host.capture(NEW)['gaps'][0] == {'thread_id': NEW, 'reason': 'registered_codex_trial',
                                           'ancestor_thread_id': TRIAL}
    assert [(method, params['threadId']) for method, params in client.calls] == [('thread/read', NEW), ('thread/read', OLD)]


def test_incomplete_host_history_and_truncation_have_only_locators():
    client = Host()
    client.metadata[OLD]['preview'] = 'never retained'
    host = reader(client)
    empty = host.capture(OLD)
    assert not empty['complete'] and empty['gaps'][0]['reason'] == 'host_history_empty_with_preview'
    assert 'never retained' not in repr(empty)
    client.rows[OLD] = [item('user', 'userMessage', content=[text_part('readable')]),
                        item('end', 'agentMessage', text='never retained', truncated=True)]
    result = host.capture(OLD)
    assert not result['complete'] and len(result['parts']) == 1
    assert result['gaps'][0]['item_id'] == 'end'
    assert result['gaps'][0]['reason'] == 'host_text_incomplete'
    assert 'never retained' not in repr(result)

    class MissingCutoff(Host):
        def call(self, method, params):
            if method == 'thread/items/list' and params['sortDirection'] == 'asc':
                return {'data': [], 'nextCursor': None}
            return super().call(method, params)

    lost = MissingCutoff()
    lost.rows[OLD] = client.rows[OLD]
    result = reader(lost).capture(OLD)
    assert not result['complete'] and result['gaps'][0]['reason'] == 'incomplete_host_history'
    assert result['gaps'][0]['item_id'] == 'end'


def test_assistant_only_turn_keeps_native_roles_and_actual_gaps_distinct():
    client = Host()
    client.rows[NEW] = [item('host', 'mcpToolCall', result={'text': 'delegation payload'}),
                        item('delegate-result', 'functionCallOutput', output='synthetic delegated instructions'),
                        item('commentary', 'agentMessage', text='Commentary', phase='commentary'),
                        item('final', 'agentMessage', text='Final', phase='final')]
    host = reader(client)
    result = host.capture(NEW)
    assert [part['text'] for part in result['parts']] == ['Commentary', 'Final']
    assert [part['bookmark']['role'] for part in result['parts']] == ['assistant'] * 2
    assert result['complete'] and result['gaps'] == []
    assert 'delegation payload' not in repr(result) and 'synthetic delegated instructions' not in repr(result)
    assert result['capture_observations'] == [{'kind': 'assistant_only_native_turns', 'assistant_only_turns': 1,
                                               'native_user_items': 0, 'native_assistant_items': 2}]
    client.rows[NEW][-1]['truncated'] = True
    incomplete = host.capture(NEW)
    assert not incomplete['complete'] and incomplete['gaps'][0]['reason'] == 'host_text_incomplete'
    assert [part['text'] for part in incomplete['parts']] == ['Commentary']
    assert incomplete['capture_observations'] == result['capture_observations']
    del client.metadata[NEW]
    with pytest.raises(CodexDialogueError, match='host_thread_unavailable') as error:
        host.read(result['parts'][0]['bookmark'])
    assert str(error.value.__cause__) == 'synthetic missing host thread'


def test_native_message_census_keeps_content_state_and_partial_readability():
    client = Host()
    client.rows[NEW] = [item('empty', 'userMessage', content=[text_part('')]),
                        item('whitespace', 'agentMessage', text=' \r\n'),
                        item('attachment', 'userMessage', content=[{'type': 'localImage', 'path': 'discarded'}]),
                        item('mixed', 'userMessage', content=[text_part('visible'), {**text_part('hidden'),
                                                                                    'truncated': True}]),
                        item('unavailable', 'agentMessage')]
    host = reader(client)
    observed = host.capture(NEW)
    assert not observed['complete']
    assert [(row['item_id'], row['text_status'], row['readability']) for row in observed['message_census']] == [
        ('empty', 'zero_bytes', 'complete'), ('whitespace', 'whitespace_only', 'complete'),
        ('attachment', 'non_text_only', 'complete'), ('mixed', 'nonempty', 'partial'),
        ('unavailable', 'unknown', 'unreadable')]
    assert 'hidden' not in repr(observed) and 'discarded' not in repr(observed['message_census'])
    bookmark = observed['parts'][-1]['bookmark']
    client.rows[NEW][-2]['item'].pop('content')
    with pytest.raises(CodexDialogueError, match='host_text_unavailable'):
        host.read(bookmark)


def test_legacy_endpoint_failure_is_reported_without_retry_or_hydration():
    class Legacy(Host):
        def call(self, method, params):
            if method == 'thread/items/list':
                self.calls.append((method, params))
                raise AppServerError('thread/items/list is not supported yet', code=-32601)
            return super().call(method, params)

    client = Legacy()
    client.metadata[OLD]['historyMode'] = 'legacy'
    result = reader(client).capture(OLD)
    assert not result['complete'] and result['history_mode'] == 'legacy'
    assert result['gaps'] == [{'thread_id': OLD, 'reason': 'host_items_unavailable',
                               'method': 'thread/items/list', 'rpc_code': -32601}]
    assert [(method, params.get('includeTurns')) for method, params in client.calls] == [
        ('thread/read', False), ('thread/items/list', None)]


def test_authorized_capture_includes_canonical_ancestor_ids():
    attached = '01a1c568-0e63-7a32-94a4-508ffc4e1159'
    client = Host()
    client.metadata[OLD]['attachedToThreadId'] = attached.upper()
    client.metadata[attached] = {'id': attached, 'projectId': 'old'}
    client.metadata[NEW].update(parentThreadId=OLD, forkedFromId=attached)
    client.rows[attached] = []
    client.rows[NEW] = [item('authorized-user', 'userMessage', content=[text_part('continued')])]
    host = reader(client, authorized={OLD: 'old', NEW: 'new', attached: 'old'})

    snapshot = host.capture(NEW)
    assert snapshot['parts'][0]['text'] == 'continued'
    assert snapshot['parent_thread_id'] == OLD and snapshot['forked_from_id'] == attached
    assert snapshot['ancestor_thread_ids'] == sorted([OLD, attached])
    assert host.capture(OLD)['attached_to_thread_id'] == attached
    assert host.capture(attached)['ancestor_thread_ids'] == []

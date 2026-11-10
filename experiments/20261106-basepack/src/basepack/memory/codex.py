"""Export explicitly assigned Codex threads through the App Server read API."""

from collections import deque
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import tempfile
from uuid import UUID

from .maintenance import check
from .images import IMAGE_SUFFIXES

SOURCE_KINDS = ['cli', 'vscode', 'exec', 'appServer', 'subAgent', 'subAgentReview',
                'subAgentCompact', 'subAgentThreadSpawn', 'subAgentOther', 'unknown']


class AppServer:
    def __init__(self, executable='codex'):
        self.errors = tempfile.TemporaryFile()
        self.process = subprocess.Popen(
            [executable, 'app-server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self.errors, text=True, encoding='utf-8', bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
        self.sequence = 0
        try:
            self.call('initialize', {'clientInfo': {'name': 'basepack', 'version': '1'},
                                     'capabilities': {'experimentalApi': True}})
            self._send({'method': 'initialized', 'params': {}})
        except Exception:
            self.close()
            raise

    def _send(self, message):
        self.process.stdin.write(json.dumps(message, ensure_ascii=False) + '\n')
        self.process.stdin.flush()

    def call(self, method, params):
        self.sequence += 1
        request_id = self.sequence
        self._send({'id': request_id, 'method': method, 'params': params})
        while True:
            line = self.process.stdout.readline()
            if not line:
                self.errors.seek(0)
                raise RuntimeError('Codex App Server exited: ' + self.errors.read().decode('utf-8', errors='replace'))
            message = json.loads(line)
            if message.get('id') == request_id:
                if 'error' in message:
                    raise RuntimeError(f"Codex App Server {method}: {message['error']}")
                return message['result']

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
        self.process.wait()
        self.process.stdin.close()
        self.process.stdout.close()
        self.errors.close()


def list_threads(client, *, control=None):
    """List active and archived metadata without the server's repair scan."""
    threads = []
    for archived in (False, True):
        cursor = None
        while True:
            if control:
                check(control)
            page = client.call('thread/list', {'archived': archived, 'cursor': cursor, 'limit': 100,
                                               'sourceKinds': SOURCE_KINDS, 'modelProviders': [],
                                               'useStateDbOnly': True})
            threads.extend({**thread, 'archived': archived} for thread in page['data'])
            cursor = page.get('nextCursor')
            if not cursor:
                break
    return threads


def _items(client, thread_id, control):
    # Capture a persisted endpoint first, so an active conversation cannot keep
    # extending this maintenance run indefinitely.
    last = client.call('thread/items/list', {'threadId': thread_id, 'limit': 1, 'sortDirection': 'desc'})['data']
    if not last:
        return []
    endpoint = (last[0]['turnId'], last[0]['item']['id'])
    cursor = None
    items = []
    seen = {}
    while True:
        if control:
            check(control)
        page = client.call('thread/items/list', {'threadId': thread_id, 'cursor': cursor,
                                                 'limit': 100, 'sortDirection': 'asc'})
        for item in page['data']:
            identity = (item['turnId'], item['item']['id'])
            if identity in seen and seen[identity] != item:
                raise RuntimeError(f'Codex thread {thread_id}: conflicting item {identity}')
            if identity not in seen:
                seen[identity] = item
                items.append(item)
            if identity == endpoint:
                return items
        cursor = page.get('nextCursor')
        if not cursor:
            raise RuntimeError(f'Codex thread {thread_id}: captured endpoint disappeared during pagination')


def _local_image(part, memory_dir, control):
    path = Path(part['path'])
    suffix = path.suffix.lower()
    if suffix not in IMAGE_SUFFIXES:
        return None, 'unsupported_local_image_type'
    try:
        before = path.stat()
        data = path.read_bytes()
        after = path.stat()
    except FileNotFoundError:
        return None, 'local_image_unavailable'
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError(f'Codex local image changed while reading: {path}')
    digest = sha256(data).hexdigest()
    target = memory_dir / 'codex-attachments' / (digest + suffix)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError(f'Codex attachment snapshot revision mismatch: {target}')
    else:
        if control:
            check(control)
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temp:
            temp_path = Path(temp.name)
            try:
                temp.write(data)
                temp.close()
                if control:
                    check(control)
                os.replace(temp_path, target)
            finally:
                temp_path.unlink(missing_ok=True)
    return target, None


def _render(project_id, thread, items, memory_dir, control):
    output = bytearray()
    locations, gaps, attachments = [], [], []
    referenced = set()
    thread_id = thread['id']
    for row in items:
        item = row['item']
        if item['type'] == 'subAgentActivity':
            referenced.add(item['agentThreadId'])
        elif item['type'] == 'collabAgentToolCall':
            referenced.update(item['receiverThreadIds'])
        if item['type'] == 'userMessage':
            role, parts = 'user', item['content']
        elif item['type'] == 'agentMessage':
            role, parts = 'assistant', [{'type': 'text', 'text': item['text']}]
        else:
            continue
        for index, part in enumerate(parts):
            meta = {'project_id': project_id, 'thread_id': thread_id, 'turn_id': row['turnId'],
                    'item_id': item['id'], 'part': index, 'role': role, 'part_type': part['type'],
                    'chat_url': f'codex://threads/{thread_id}',
                    'parent_thread_id': thread.get('parentThreadId'),
                    'forked_from_id': thread.get('forkedFromId')}
            if part['type'] == 'text':
                body = part['text'].encode('utf-8')
            elif part['type'] == 'localImage':
                body = b''
                target, reason = _local_image(part, memory_dir, control)
                if target is None:
                    meta['unavailable_part'] = part
                    gaps.append({**meta, 'reason': reason})
                else:
                    meta['source_part'] = part
                    meta['managed_attachment'] = target.relative_to(memory_dir).as_posix()
                    attachments.append(str(target))
            else:
                body = b''
                meta['unavailable_part'] = part
                gaps.append(meta.copy())
            meta['byte_length'] = len(body)
            output.extend((json.dumps(meta, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8'))
            start = len(output)
            output.extend(body)
            locations.append({**meta, 'byte_start': start, 'byte_end': len(output)})
            output.extend(b'\n')
    return bytes(output), locations, gaps, sorted(referenced), list(dict.fromkeys(attachments))


def collect_codex(project_id, thread_ids, output_dir, *, control=None, executable='codex', client=None,
                  project_binding=None):
    """Export an explicit project-assigned thread manifest; never infer ownership.

    Returns source paths, byte locations and unavailable parts. The caller owns
    discovery, authorization of the manifest and semantic publication.
    """
    if not project_id:
        raise ValueError('A Codex project ID is required')
    ids = list(dict.fromkeys(str(UUID(thread_id)) for thread_id in thread_ids))
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    owned_client = client is None
    if owned_client:
        client = AppServer(executable)
    results = []
    by_id = {}
    pending = deque((thread_id, None) for thread_id in ids)
    attempted = set()
    try:
        while pending:
            thread_id, referrer = pending.popleft()
            if thread_id in by_id or (thread_id, referrer) in attempted:
                continue
            attempted.add((thread_id, referrer))
            if control:
                check(control)
            thread = client.call('thread/read', {'threadId': thread_id, 'includeTurns': False})['thread']
            if thread['id'] != thread_id:
                raise ValueError(f'Codex returned a different thread for {thread_id}')
            if referrer is None and project_binding is not None:
                from .codex_binding import classify_threads
                classification = classify_threads(project_binding, [thread])
                if not classification['matched']:
                    category = 'unresolved' if classification['unresolved'] else 'excluded'
                    result = {'thread_id': thread_id, 'path': None, 'changed': False,
                              'parent_thread_id': thread.get('parentThreadId'),
                              'forked_from_id': thread.get('forkedFromId'), 'locations': [],
                              'referenced_threads': [], 'attachments': [],
                              'gaps': [{'thread_id': thread_id, 'reason': 'binding_changed',
                                        'classification': category,
                                        'binding_reason': classification[category][0]['reason']}]}
                    results.append(result)
                    by_id[thread_id] = result
                    continue
            if referrer is not None and thread.get('parentThreadId') != referrer:
                by_id[referrer]['gaps'].append({'thread_id': referrer, 'referenced_thread_id': thread_id,
                                                 'reason': 'referenced_subagent_parent_mismatch'})
                continue
            if thread.get('projectId') not in (None, project_id):
                raise ValueError(f'Codex thread {thread_id} belongs to another project')
            items = _items(client, thread_id, control)
            content, locations, gaps, referenced, attachments = _render(project_id, thread, items,
                                                                         output_dir.parent, control)
            for child in referenced:
                pending.append((str(UUID(child)), thread_id))
            path = output_dir / f'{thread_id}.txt'
            if not content and path.exists() and path.stat().st_size:
                raise RuntimeError(f'Codex thread {thread_id}: message history became empty; existing export retained')
            if not content:
                result = {'thread_id': thread_id, 'path': None, 'changed': False,
                          'parent_thread_id': thread.get('parentThreadId'),
                          'forked_from_id': thread.get('forkedFromId'), 'locations': [],
                          'referenced_threads': referenced,
                          'attachments': attachments,
                          'gaps': [*gaps, {'thread_id': thread_id, 'reason': 'no_exportable_messages',
                                           'item_count': len(items)}]}
                results.append(result)
                by_id[thread_id] = result
                continue
            changed = not path.exists() or path.read_bytes() != content
            if changed:
                if control:
                    check(control)
                with tempfile.NamedTemporaryFile(dir=output_dir, delete=False) as temp:
                    temp_path = Path(temp.name)
                    try:
                        temp.write(content)
                        temp.close()
                        os.replace(temp_path, path)
                    finally:
                        temp_path.unlink(missing_ok=True)
            result = {'thread_id': thread_id, 'path': str(path), 'changed': changed,
                      'parent_thread_id': thread.get('parentThreadId'),
                      'forked_from_id': thread.get('forkedFromId'),
                      'locations': locations, 'referenced_threads': referenced,
                      'attachments': attachments, 'gaps': gaps}
            results.append(result)
            by_id[thread_id] = result
    finally:
        if owned_client:
            client.close()
    return {'project_id': project_id, 'threads': results,
            'paths': list(dict.fromkeys(path for item in results
                                       for path in ([item['path']] if item['path'] is not None else [])
                                       + item['attachments'])),
            'gaps': [gap for item in results for gap in item['gaps']]}

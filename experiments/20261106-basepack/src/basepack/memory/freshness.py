"""Read-only Codex inventory and targeted original comparison for retrieval."""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from .codex import AppServer, _items, list_threads
from .codex_binding import classify_threads, discover_binding


def _records(path, project_id, thread_id):
    records = {}
    if not path.exists():
        return records
    with path.open('rb') as stream:
        while header := stream.readline():
            meta = json.loads(header)
            if meta['project_id'] != project_id or meta['thread_id'] != thread_id:
                raise ValueError(f'Codex capture ownership mismatch: {path}')
            body = stream.read(meta['byte_length'])
            if len(body) != meta['byte_length'] or stream.read(1) != b'\n':
                raise ValueError(f'Truncated Codex capture: {path}')
            records[(meta['turn_id'], meta['item_id'], meta['part'])] = (meta, body.decode('utf-8'))
    return records


def _receipt(memory_dir, project_id):
    receipts = sorted((memory_dir / 'maintenance').glob('codex-*.json'),
                      key=lambda path: path.stat().st_mtime_ns, reverse=True)
    for path in receipts:
        data = json.loads(path.read_text(encoding='utf-8'))
        if data['binding']['project_id'] == project_id:
            return path, data
    return None, None



def _semantic_snapshot(memory_dir, receipt_path):
    if receipt_path is None:
        return None
    for path in sorted((memory_dir / 'maintenance').glob('*.json'),
                       key=lambda value: value.stat().st_mtime_ns, reverse=True):
        if not re.fullmatch(r'[0-9a-f]{32}\.json', path.name):
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('codex', {}).get('receipt') != str(receipt_path):
            continue
        return {'receipt': str(path), 'pending_at_preflight': [
            {'path': item['path'], 'reason': item.get('reason'),
             'uncovered_ranges': [{key: part[key] for key in ('start_line', 'end_line')}
                                  for part in item.get('uncovered_ranges', [])]}
            for item in data['semantic']],
            'note': 'Preflight snapshot only; later publication may have changed these pending ranges.'}
    return None

def inspect_codex(config, *, registry_path=None, thread_id=None, client=None):
    binding = (json.loads(Path(registry_path).read_text(encoding='utf-8')) if registry_path
               else config.raw['memory'].get('codex', {}))
    if not binding.get('project_id') or not binding.get('registry_complete'):
        return {'status': 'binding_unavailable', 'unknown': 'Host project ID and complete registered roots required.'}
    resolved = discover_binding(config.root, binding['project_id'], binding['other_project_roots'])
    receipt_path, receipt = _receipt(config.memory_dir, binding['project_id'])
    receipt_threads = {row['thread_id']: row for row in receipt['capture']['threads']} if receipt else {}
    owned = client is None
    if owned:
        client = AppServer(os.environ.get('CODEX_APP_RUNTIME_CLI_PATH', 'codex'))
    try:
        discovery = classify_threads(resolved, list_threads(client))
        result = {'status': 'ok', 'project_id': binding['project_id'],
                  'capture_receipt': str(receipt_path) if receipt_path else None,
                  'semantic_preflight': _semantic_snapshot(config.memory_dir, receipt_path),
                  'receipt_written_at': datetime.fromtimestamp(receipt_path.stat().st_mtime, timezone.utc).isoformat() if receipt_path else None,
                  'cutoff_note': 'Receipt time is not a global message cutoff; each captured thread has its own saved locations.',
                  'unknown': {'binding_gaps': discovery['gaps'],
                              'unresolved': [{'thread_id': row['thread']['id'], 'reason': row['reason']} for row in discovery['unresolved']],
                              'semantic_coverage': 'unknown; capture is not semantic acceptance'},
                  'threads': []}
        for row in discovery['matched']:
            old = receipt_threads.get(row['id'])
            locations = old['locations'] if old else []
            endpoint = client.call('thread/items/list', {'threadId': row['id'], 'limit': 1, 'sortDirection': 'desc'})['data']
            last = endpoint[0] if endpoint else None
            captured_endpoint = ({'turn_id': locations[-1]['turn_id'], 'item_id': locations[-1]['item_id'],
                                  'part': locations[-1]['part']} if locations else None)
            current_endpoint = ({'turn_id': last['turnId'], 'item_id': last['item']['id']} if last else None)
            source = config.memory_dir / 'codex' / f"{row['id']}.txt"
            updated = row.get('updatedAt')
            if old is None:
                status = 'unknown' if source.exists() else 'new'
            elif old['gaps'] or not source.is_file() or not captured_endpoint or not current_endpoint:
                status = 'unknown'
            elif (captured_endpoint['turn_id'], captured_endpoint['item_id']) != (current_endpoint['turn_id'], current_endpoint['item_id']):
                status = 'possibly_changed'
            elif not isinstance(updated, (int, float)):
                status = 'unknown'
            elif updated > receipt_path.stat().st_mtime:
                status = 'possibly_changed'
            else:
                status = 'unknown'
            result['threads'].append({'thread_id': row['id'], 'title': row.get('name') or row.get('preview'),
                                      'created_at': row.get('createdAt'), 'updated_at': row.get('updatedAt'),
                                      'archived': row.get('archived'), 'captured_endpoint': captured_endpoint,
                                      'current_endpoint': current_endpoint,
                                      'capture_status': status,
                                      'status_note': 'Endpoint and updatedAt are clues; text and semantic coverage require verification.',
                                      'capture_gaps': old['gaps'] if old else []})
        if thread_id:
            thread_id = str(UUID(thread_id))
            if not any(row['thread_id'] == thread_id for row in result['threads']):
                raise ValueError(f'Codex thread {thread_id} is not proven to belong to this project')
            thread = client.call('thread/read', {'threadId': thread_id, 'includeTurns': False})['thread']
            if thread['id'] != thread_id or not classify_threads(resolved, [thread])['matched']:
                raise ValueError(f'Codex thread {thread_id} binding changed during retrieval')
            old = _records(config.memory_dir / 'codex' / f'{thread_id}.txt', binding['project_id'], thread_id)
            parts, seen = [], set()
            for row in _items(client, thread_id, None):
                item = row['item']
                if item['type'] == 'userMessage':
                    role, contents = 'user', item['content']
                elif item['type'] == 'agentMessage':
                    role, contents = 'assistant', [{'type': 'text', 'text': item['text']}]
                else:
                    continue
                for index, part in enumerate(contents):
                    key = (row['turnId'], item['id'], index)
                    seen.add(key)
                    prior = old.get(key)
                    text = part.get('text') if part['type'] == 'text' else None
                    status = ('not_captured' if prior is None else
                              'unknown_non_text' if text is None else
                              'captured' if prior[0]['part_type'] == 'text' and prior[1] == text else 'changed_since_capture')
                    parts.append({'turn_id': key[0], 'item_id': key[1], 'part': index, 'role': role,
                                  'part_type': part['type'], 'text': text, 'capture_status': status,
                                  **({'source_part': part} if text is None else {})})
            matched = next(row for row in result['threads'] if row['thread_id'] == thread_id)
            statuses = {part['capture_status'] for part in parts}
            missing = old.keys() - seen
            if statuses & {'not_captured', 'changed_since_capture'} or missing:
                matched['capture_status'] = 'possibly_changed' if old else 'new'
            elif parts and statuses == {'captured'} and not matched['capture_gaps']:
                matched['capture_status'] = 'covered'
            else:
                matched['capture_status'] = 'unknown'
            result['read'] = {'thread_id': thread_id, 'chat_url': f'codex://threads/{thread_id}',
                              'parts': parts, 'captured_only': [list(key) for key in old.keys() - seen],
                              'semantic_coverage': 'unknown; compare published evidence separately'}
        result['inventory'] = {status: [row['thread_id'] for row in result['threads']
                                      if row['capture_status'] == status]
                               for status in ('new', 'possibly_changed', 'covered', 'unknown')}
        return result
    finally:
        if owned:
            client.close()

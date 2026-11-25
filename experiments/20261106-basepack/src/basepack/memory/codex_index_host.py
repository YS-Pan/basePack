"""Read authorized Codex messages for indexing without exporting a transcript."""

from hashlib import sha256
from uuid import UUID

from .codex import AppServerError, CodexHistoryError, _items, message_parts, thread_parent
from .codex_binding import classify_threads


_MESSAGE_ROLES = {'userMessage': 'user', 'agentMessage': 'assistant'}


class CodexDialogueError(ValueError):
    """An original cannot be verified at the specified Codex location."""

    def __init__(self, reason, *, thread_id, **details):
        self.reason = reason
        self.gap = {'thread_id': thread_id, 'reason': reason, **details}
        super().__init__(f'Codex dialogue {thread_id}: {reason} {details}')


def _item_position(row):
    return {'turn_id': row['turnId'], 'item_id': row['item']['id']}


def _parts(thread_id, row, *, include_empty=False):
    item = row['item']
    role = _MESSAGE_ROLES.get(item['type'])
    if role is None:
        return [], []
    incomplete = row.get('outputDeferred') or row.get('truncated') or item.get('truncated')
    location = {'thread_id': thread_id, **_item_position(row), 'role': role}
    if item.get('content' if role == 'user' else 'text') is None:
        reason = 'host_text_incomplete' if incomplete else 'host_text_unavailable'
        return [], [{**location, 'reason': reason}]
    _, contents = message_parts(item)
    parts, gaps = [], []
    for index, part in enumerate(contents):
        locator = {**location, 'part': index}
        part_type = part['type']
        if part_type != 'text':
            gaps.append({**locator, 'part_type': part_type, 'reason': 'non_text_part'})
            continue
        if incomplete or part.get('truncated') or part.get('text') is None:
            reason = 'host_text_incomplete' if incomplete or part.get('truncated') else 'host_text_unavailable'
            gaps.append({**locator, 'part_type': part_type, 'reason': reason})
            continue
        body = part['text']
        if body or include_empty:
            encoded = body.encode('utf-8')
            bookmark = {**locator, 'part_sha256': sha256(encoded).hexdigest(),
                        'byte_start': 0, 'byte_end': len(encoded)}
            parts.append({'bookmark': bookmark, 'text': body})
    if incomplete and all(gap['reason'] == 'non_text_part' for gap in gaps):
        gaps.append({**location, 'reason': 'host_text_incomplete'})
    return parts, gaps


def _message_observation(row, role, parts, gaps):
    non_text = sum(gap['reason'] == 'non_text_part' for gap in gaps)
    unknown = len(gaps) > non_text
    if any(part['text'].strip() for part in parts):
        status = 'nonempty'
    elif unknown:
        status = 'unknown'
    elif any(part['text'] for part in parts):
        status = 'whitespace_only'
    elif non_text and not parts:
        status = 'non_text_only'
    else:
        status = 'zero_bytes'
    readability = ('partial' if parts or non_text else 'unreadable') if unknown else 'complete'
    return {**_item_position(row), 'role': role, 'readability': readability,
            'text_status': status, 'non_text_parts': non_text}


class CodexDialogueHost:
    """Use the same App Server read path for every explicitly authorized binding.

    The caller owns the App Server and supplies the authorized thread-to-binding
    mapping. Capture and read return text for immediate in-memory use only.
    """

    def __init__(self, client, bindings, authorized, *, excluded_thread_ids=(), private_thread_ids=(),
                 checkpoint=None):
        self.client = client
        self.bindings = bindings
        self.authorized = {str(UUID(thread_id)): binding for thread_id, binding in authorized.items()}
        self.excluded = {str(UUID(thread_id)) for thread_id in excluded_thread_ids}
        self.private = {str(UUID(thread_id)) for thread_id in private_thread_ids}
        self.checkpoint = checkpoint

    def _call(self, method, **params):
        if self.checkpoint is not None:
            self.checkpoint()
        return self.client.call(method, params)

    def _authorize(self, thread_id):
        if thread_id in self.excluded:
            raise CodexDialogueError('registered_codex_trial', thread_id=thread_id)
        if thread_id not in self.authorized:
            raise CodexDialogueError('thread_not_authorized', thread_id=thread_id)

    def verify_registration(self, thread_id):
        """Verify one ordinary project-rooted dialogue using only host metadata."""
        self._authorized_thread(str(UUID(thread_id)), registration=True)

    def _authorized_thread(self, thread_id, *, registration=False):
        checked, active = {}, set()

        def visit(identity):
            if identity in checked:
                return checked[identity]
            if identity in active:
                raise CodexDialogueError('ancestry_cycle', thread_id=thread_id, ancestor_thread_id=identity)
            self._authorize(identity)
            active.add(identity)
            try:
                thread = self._call('thread/read', threadId=identity, includeTurns=False)['thread']
            except AppServerError as error:
                raise CodexDialogueError('host_thread_unavailable', thread_id=thread_id,
                                         source_thread_id=identity, method='thread/read', rpc_code=error.code) from error
            if thread['id'] != identity:
                raise CodexDialogueError('host_thread_mismatch', thread_id=thread_id, source_thread_id=identity)
            binding = self.bindings[self.authorized[identity]]
            classification = classify_threads(binding, [thread])
            if not classification['matched']:
                problem = (classification['excluded'] or classification['unresolved'])[0]
                raise CodexDialogueError('thread_binding_unverified', thread_id=thread_id,
                                         source_thread_id=identity, binding_reason=problem['reason'])
            if registration and not classify_threads(binding, [dict(thread, projectId=None)])['matched']:
                raise CodexDialogueError('registration_cwd_unverified', thread_id=thread_id)
            try:
                parent = thread_parent(thread)
            except ValueError as error:
                raise CodexDialogueError('conflicting_ancestry', thread_id=thread_id,
                                         source_thread_id=identity) from error
            source = thread.get('source')
            if isinstance(source, dict) and 'subAgent' in source and not parent:
                raise CodexDialogueError('ancestry_unavailable', thread_id=thread_id, source_thread_id=identity)
            direct = {'parent_thread_id': parent, 'forked_from_id': thread.get('forkedFromId'),
                      'attached_to_thread_id': thread.get('attachedToThreadId')}
            ancestry = set()
            for relation, ancestor in direct.items():
                if not ancestor:
                    continue
                direct[relation] = ancestor = str(UUID(ancestor))
                if ancestor in self.excluded:
                    raise CodexDialogueError('registered_codex_trial', thread_id=thread_id,
                                             ancestor_thread_id=ancestor)
                if registration:
                    raise CodexDialogueError('registration_requires_top_level_thread', thread_id=thread_id)
                if ancestor not in self.authorized:
                    raise CodexDialogueError('ancestry_not_authorized', thread_id=thread_id,
                                             ancestor_thread_id=ancestor)
                if ancestor in self.private and thread_id not in self.private:
                    raise CodexDialogueError('private_ancestry', thread_id=thread_id, ancestor_thread_id=ancestor)
                ancestry.add(ancestor)
                ancestry.update(visit(ancestor)['ancestor_thread_ids'])
            if registration and (source not in ('cli', 'vscode', 'appServer') or thread.get('ephemeral')):
                raise CodexDialogueError('registration_requires_ordinary_thread', thread_id=thread_id)
            active.remove(identity)
            checked[identity] = {**direct, 'ancestor_thread_ids': sorted(ancestry),
                                 'history_mode': thread.get('historyMode'),
                                 'has_preview': bool(thread.get('preview'))}
            return checked[identity]

        return visit(thread_id)

    def capture(self, thread_id):
        """Return each complete native text part through the persisted listing cutoff."""
        thread_id = str(UUID(thread_id))
        self._authorize(thread_id)
        result = {'thread_id': thread_id, 'chat_url': f'codex://threads/{thread_id}',
                  'parent_thread_id': None, 'forked_from_id': None, 'attached_to_thread_id': None,
                  'history_mode': None,
                  'cutoff': None, 'parts': [], 'gaps': [], 'capture_observations': [], 'complete': False,
                  'coverage_source': 'persisted_app_server_items', 'original_length': 'unreported'}
        try:
            metadata = self._authorized_thread(thread_id)
            has_preview = metadata.pop('has_preview')
            result.update(metadata)
            items = _items(self.client, thread_id, None, self.checkpoint)
        except CodexDialogueError as error:
            result['gaps'].append(error.gap)
            return result
        except AppServerError as error:
            result['gaps'].append({'thread_id': thread_id, 'reason': 'host_items_unavailable',
                                   'method': 'thread/items/list', 'rpc_code': error.code})
            return result
        except CodexHistoryError as error:
            turn_id, item_id = error.identity
            result['gaps'].append({'thread_id': thread_id, 'turn_id': turn_id, 'item_id': item_id,
                                   'reason': 'incomplete_host_history', 'detail': error.reason})
            return result
        if items:
            result['cutoff'] = _item_position(items[-1])
        elif has_preview:
            result['gaps'].append({'thread_id': thread_id, 'reason': 'host_history_empty_with_preview'})
            return result
        user_turns = {row['turnId'] for row in items if row['item']['type'] == 'userMessage'}
        assistant_only_turns = set()
        result['message_census'] = []
        for row in items:
            role = _MESSAGE_ROLES.get(row['item']['type'])
            if role is None:
                continue
            parts, gaps = _parts(thread_id, row, include_empty=True)
            result['parts'].extend(parts)
            result['gaps'].extend(gaps)
            result['message_census'].append(_message_observation(row, role, parts, gaps))
            turn_id = row['turnId']
            if (any(part['text'] for part in parts) and row['item']['type'] == 'agentMessage'
                    and turn_id not in user_turns and turn_id not in assistant_only_turns):
                assistant_only_turns.add(turn_id)
        if assistant_only_turns:
            result['capture_observations'].append({
                'kind': 'assistant_only_native_turns', 'assistant_only_turns': len(assistant_only_turns),
                'native_user_items': sum(row['item']['type'] == 'userMessage' for row in items),
                'native_assistant_items': sum(row['item']['type'] == 'agentMessage' for row in items),
            })
        result['complete'] = all(gap['reason'] == 'non_text_part' for gap in result['gaps'])
        return result

    def _neighbors(self, thread_id, turn_id, item_id, direction, count):
        cursor = {'type': 'item', 'itemId': item_id}
        neighbors, gaps = [], []
        cursors = set()
        while cursor is not None and len(neighbors) < count:
            page = self._call('thread/items/list', threadId=thread_id, turnId=turn_id, cursor=cursor,
                              sortDirection=direction, limit=32,
                              deferOutput={'commandExecution': True, 'mcpToolCall': True})
            for row in page['data']:
                if row['turnId'] != turn_id:
                    raise CodexDialogueError('host_turn_mismatch', thread_id=thread_id, turn_id=turn_id)
                parts, missing = _parts(thread_id, row)
                neighbors.extend(reversed(parts) if direction == 'desc' else parts)
                gaps.extend(missing)
                if len(neighbors) >= count:
                    break
            next_cursor = page.get('nextCursor')
            if next_cursor in cursors:
                raise CodexDialogueError('context_cursor_repeated', thread_id=thread_id, turn_id=turn_id)
            if next_cursor:
                cursors.add(next_cursor)
            cursor = next_cursor
        return neighbors[:count], gaps

    def read(self, bookmark, *, context=1):
        """Read a saved UTF-8 range and neighboring original parts in its turn."""
        thread_id = str(UUID(bookmark['thread_id']))
        turn_id, item_id, part = (bookmark[key] for key in ('turn_id', 'item_id', 'part'))
        location = {'thread_id': thread_id, 'turn_id': turn_id, 'item_id': item_id, 'part': part}
        if type(part) is not int or part < 0 or type(context) is not int or context < 0:
            raise CodexDialogueError('invalid_bookmark_or_context', **location)
        self._authorized_thread(thread_id)
        try:
            rows = self._call('thread/items/read', threadId=thread_id, turnId=turn_id, itemIds=[item_id])['data']
        except AppServerError as error:
            raise CodexDialogueError('host_item_unavailable', **location,
                                     method='thread/items/read', rpc_code=error.code) from error
        if not rows:
            raise CodexDialogueError('host_item_unavailable', **location)
        if len(rows) != 1 or _item_position(rows[0]) != {'turn_id': turn_id, 'item_id': item_id}:
            raise CodexDialogueError('host_item_mismatch', **location)
        role = _MESSAGE_ROLES.get(rows[0]['item']['type'])
        if role != bookmark['role']:
            raise CodexDialogueError('host_message_role_changed', **location, actual_role=role)
        parts, gaps = _parts(thread_id, rows[0])
        target = next((row for row in parts if row['bookmark']['part'] == part), None)
        if target is None:
            gap = next((gap for gap in gaps if gap.get('part', part) == part), None)
            raise CodexDialogueError(gap['reason'] if gap else 'host_text_part_unavailable', **location)
        actual = target['bookmark']['part_sha256']
        expected = bookmark['part_sha256']
        if actual != expected:
            raise CodexDialogueError('host_text_revision_mismatch', **location,
                                     expected_part_sha256=expected, actual_part_sha256=actual)
        start, end = bookmark['byte_start'], bookmark['byte_end']
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= target['bookmark']['byte_end']:
            raise CodexDialogueError('invalid_byte_range', **location, byte_start=start, byte_end=end)
        try:
            text = target['text'].encode('utf-8')[start:end].decode('utf-8')
        except UnicodeDecodeError as error:
            raise CodexDialogueError('invalid_utf8_boundary', **location, byte_start=start, byte_end=end) from error
        result = {'bookmark': {**target['bookmark'], 'byte_start': start, 'byte_end': end},
                  'text': text, 'context': [], 'gaps': gaps}
        if not context:
            return result
        index = parts.index(target)
        before, after = list(reversed(parts[:index])), parts[index + 1:]
        for direction, neighbors in (('desc', before), ('asc', after)):
            try:
                if len(neighbors) < context:
                    extra, missing = self._neighbors(thread_id, turn_id, item_id, direction, context - len(neighbors))
                    neighbors.extend(extra)
                    gaps.extend(missing)
            except AppServerError as error:
                gaps.append({**location, 'reason': 'host_context_unavailable', 'direction': direction,
                             'method': 'thread/items/list', 'rpc_code': error.code})
            except CodexDialogueError as error:
                gaps.append({**error.gap, 'direction': direction})
        result['context'] = [*reversed(before[:context]), target, *after[:context]]
        return result

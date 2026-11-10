"""Resolve Codex message evidence from its saved, length-framed source snapshot."""

import json


def message_locations(snapshot: str, start_line: int, end_line: int) -> list[dict]:
    """Return message-body intersections with a 1-based inclusive source range.

    Offsets are zero-based, half-open UTF-8 byte offsets, both within the
    snapshot and within the individual message part. Generated frame headers
    and separators are never returned as message text.
    """
    lines = snapshot.splitlines(keepends=True)
    if not 1 <= start_line <= end_line <= len(lines):
        raise ValueError(f"Invalid line range {start_line}:{end_line}")
    selected_start = len(''.join(lines[:start_line - 1]).encode('utf-8'))
    selected_end = selected_start + len(''.join(lines[start_line - 1:end_line]).encode('utf-8'))
    data = snapshot.encode('utf-8')
    offset = 0
    locations = []
    while offset < len(data):
        header_end = data.index(b'\n', offset)
        meta = json.loads(data[offset:header_end])
        body_start = header_end + 1
        body_end = body_start + meta['byte_length']
        if body_end >= len(data) or data[body_end:body_end + 1] != b'\n':
            raise ValueError('Invalid Codex source frame boundary')
        start, end = max(selected_start, body_start), min(selected_end, body_end)
        if start < end:
            locations.append({
                'chat_url': meta['chat_url'], 'thread_id': meta['thread_id'],
                'turn_id': meta['turn_id'], 'item_id': meta['item_id'],
                'part': meta['part'], 'role': meta['role'], 'part_type': meta['part_type'],
                'parent_thread_id': meta.get('parent_thread_id'), 'forked_from_id': meta.get('forked_from_id'),
                'snapshot_byte_start': start, 'snapshot_byte_end': end,
                'part_byte_start': start - body_start, 'part_byte_end': end - body_start,
                'text': data[start:end].decode('utf-8'),
            })
        offset = body_end + 1
    return locations

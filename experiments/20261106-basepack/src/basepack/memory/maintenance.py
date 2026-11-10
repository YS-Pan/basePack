"""Task-scoped stop and publication arbitration shared by host and worker."""

from contextlib import contextmanager
import errno
import os
from pathlib import Path
import time


class MaintenanceStopped(RuntimeError):
    pass


@contextmanager
def _locked(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as file:
        deadline = time.monotonic() + 0.5
        while True:
            try:
                file.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as error:
                if error.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise
                if time.monotonic() >= deadline:
                    raise TimeoutError(f'Maintenance control is busy: {path}')
                time.sleep(0.01)
        try:
            yield file
        finally:
            file.seek(0)
            if os.name == 'nt':
                msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(file, fcntl.LOCK_UN)


def stop(path):
    """Stop this task's future work without waiting for active encoding or commit."""
    with _locked(path) as file:
        file.seek(0)
        file.write(b'S')
        file.flush()


def begin_commit(path):
    """Claim commit under the stop lock; a later stop leaves this commit alone."""
    with _locked(path) as file:
        file.seek(0)
        if file.read(1) == b'S':
            raise MaintenanceStopped('Maintenance stopped before publication')


def check(path):
    begin_commit(path)


def maintain(memory, scope, *, control=None, timeout=600):
    """Refresh mechanically equivalent originals and retain a semantic handoff.

    This is an explicit maintenance action. Query actions never call it.
    Source snapshots, member versions and stale state remain authoritative.
    """
    from dataclasses import asdict
    from hashlib import sha256
    import json
    import re
    from uuid import uuid4

    from .content import comparison_text, line_changes, locate_lines, mapped_line_range
    from .images import ImageSource
    from .store import _record, _sql

    if control:
        check(control)
    known = memory._rows('source')
    by_path = {row['path']: row for row in known if not row.get('deleted')}
    changes = memory._check_changes(known, list(dict.fromkeys([*scope, *by_path])), deep=True)
    members = memory._rows('member')
    nodes = memory._rows('node')
    edges = memory._rows('semantic')
    snapshots = {}

    def snapshot(version):
        if version not in snapshots:
            row = memory._execute(f'SELECT * FROM ONLY {_sql(_record(version))};')[0]
            if row is None:
                raise ValueError(f'Source snapshot not found: {version}')
            if row['kind'] == 'text' and sha256(row['text'].encode('utf-8')).hexdigest() != row['revision']:
                raise ValueError(f'Text snapshot revision mismatch: {version}')
            snapshots[version] = row
        return snapshots[version]

    normalize = comparison_text
    receipts = []
    reused_chunks = []
    change_by_path = {row['path']: row for row in changes}
    for path, change in change_by_path.items():
        if control:
            check(control)
        if change['kind'] != 'modified':
            continue
        previous = by_path[path]
        current = memory._load_source(path, previous.get('kind'))
        if current.revision == previous['revision']:
            receipts.append(memory.apply({'sources': [{'id': previous['id'], 'path': path,
                                                       'revision': current.revision}]}, control=control, timeout=timeout))
            continue
        active = [row for row in members if row['path'] == path and not row['retired']]
        if isinstance(current, ImageSource) or not active:
            continue
        # Never treat a newer accepted source as proof that an older member was
        # accepted: compare every active member's own version.
        equivalent = not any(row['stale'] for row in active) and all(
            snapshot(row['source_version'])['kind'] == 'text' and
            normalize(snapshot(row['source_version'])['text']) == normalize(current.text) for row in active)
        if not equivalent:
            by_id = {row['id']: row for row in members}
            accepted = []
            for row in active:
                if row['kind'] != 'chunk' or row['stale'] or row.get('basis'):
                    continue
                old = snapshot(row['source_version'])
                if old['kind'] != 'text':
                    continue
                opcodes = line_changes(old['text'], current.text)
                mapped = mapped_line_range(opcodes, row['start_line'], row['end_line'])
                anchors = locate_lines(old['text'], current.text, row['start_line'], row['end_line'])
                if mapped is None or len(anchors) != 1:
                    continue
                before = normalize(old['text']).splitlines(keepends=True)
                after = normalize(current.text).splitlines(keepends=True)
                parent = by_id.get(row.get('parent'))
                if parent and parent['kind'] == 'section' and parent['source_version'] == row['source_version']:
                    start, end = parent['start_line'] - 1, parent['end_line']
                    if (mapped_line_range(opcodes, start + 1, end) is None or
                            any(tag == 'insert' and start <= i <= end for tag, i, _, _, _ in opcodes)):
                        continue
                else:
                    heading = re.compile(r'^ {0,3}#{1,6}(?:[ \t]+|$)')
                    old_heading = next((i for i in range(row['start_line'] - 1, -1, -1) if heading.match(before[i])), None)
                    new_heading = next((i for i in range(mapped[0] - 1, -1, -1) if heading.match(after[i])), None)
                    head_map = (mapped_line_range(opcodes, old_heading + 1, old_heading + 1)
                                if old_heading is not None else None)
                    if not ((old_heading is None and new_heading is None) or
                            (head_map is not None and new_heading == head_map[0] - 1)):
                        continue
                accepted.append({**{key: row[key] for key in ('id', 'kind', 'path', 'parent', 'title',
                                                               'mandatory', 'coverage_gaps')},
                                 'start_line': mapped[0], 'end_line': mapped[1]})
            if accepted:
                receipts.append(memory.apply({'sources': [{'id': previous['id'], 'path': path,
                                                           'revision': current.revision}],
                                              'expected': {row['id']: row['knowledge_revision'] for row in members},
                                              'members': accepted}, control=control, timeout=timeout))
                reused_chunks.extend(item['id'] for item in accepted)
            continue
        active_ids = {row['id'] for row in active}
        by_id = {row['id']: row for row in members}
        if any(by_id[basis['member']]['stale'] or by_id[basis['member']]['retired']
               for row in active for basis in row.get('basis', []) if basis['member'] not in active_ids):
            continue
        accepted = []
        for row in active:
            item = {key: row[key] for key in ('id', 'kind', 'path', 'parent', 'title', 'start_line',
                                               'end_line', 'mandatory', 'coverage_gaps')}
            item['evidence'] = [basis['member'] for basis in row.get('basis', [])]
            if row['kind'] != 'chunk':
                item['text'] = row['text']
            accepted.append(item)
        receipts.append(memory.apply({'sources': [{'id': previous['id'], 'path': path, 'revision': current.revision}],
                                      'expected': {row['id']: row['knowledge_revision'] for row in members},
                                      'members': accepted},
                                     control=control, timeout=timeout))
    if receipts:
        known = memory._rows('source')
        by_path = {row['path']: row for row in known if not row.get('deleted')}
        members = memory._rows('member')

    semantic = {}
    for change in changes:
        if change['kind'] in {'added', 'deleted'}:
            semantic[change['path']] = {'path': change['path'], 'reason': change['kind'], 'members': [], 'versions': []}
    current_sources = {}
    member_by_id = {row['id']: row for row in members}
    for row in members:
        if row['retired']:
            continue
        path = row['path']
        reasons = []
        if row['stale']:
            reasons.append('stale')
        if row.get('coverage_gaps'):
            reasons.append('coverage_gaps')
        if path not in current_sources:
            try:
                current_sources[path] = memory._load_source(path, row['kind'])
            except FileNotFoundError:
                current_sources[path] = None
        current = current_sources[path]
        if current is None:
            reasons.append('missing')
        if current is not None and current.revision != row['source_revision']:
            old = snapshot(row['source_version'])
            if isinstance(current, ImageSource) or old['kind'] != 'text':
                reasons.append('changed')
            elif normalize(old['text']) != normalize(current.text):
                before, after = normalize(old['text']).splitlines(keepends=True), normalize(current.text).splitlines(keepends=True)
                opcodes = line_changes(old['text'], current.text)
                start, end = row['start_line'] - 1, row['end_line']
                mapped = mapped_line_range(opcodes, row['start_line'], row['end_line'])
                anchors = locate_lines(old['text'], current.text, row['start_line'], row['end_line'])
                equal = mapped is not None and len(anchors) == 1
                insertion = any(tag == 'insert' and start <= i <= end for tag, i, _, _, _ in opcodes)
                if equal and row['kind'] == 'chunk':
                    parent = member_by_id.get(row.get('parent'))
                    if parent and parent['kind'] == 'section' and parent['source_version'] == row['source_version']:
                        pstart, pend = parent['start_line'] - 1, parent['end_line']
                        if (mapped_line_range(opcodes, pstart + 1, pend) is None or
                                any(tag == 'insert' and pstart <= i <= pend for tag, i, _, _, _ in opcodes)):
                            reasons.append('parent_context_changed')
                    else:
                        heading = re.compile(r'^ {0,3}#{1,6}(?:[ \t]+|$)')
                        old_heading = next((i for i in range(start, -1, -1) if heading.match(before[i])), None)
                        new_heading = next((i for i in range(mapped[0] - 1, -1, -1) if heading.match(after[i])), None)
                        if old_heading is None:
                            same_heading = new_heading is None
                        else:
                            head_map = mapped_line_range(opcodes, old_heading + 1, old_heading + 1)
                            same_heading = head_map is not None and new_heading == head_map[0] - 1
                        if not same_heading:
                            reasons.append('parent_context_changed')
                if row['kind'] == 'file' or not equal or (row['kind'] == 'section' and insertion):
                    reasons.append('ambiguous' if len(anchors) > 1 else 'changed')
                item = semantic.setdefault(path, {'path': path, 'members': [], 'versions': [], 'line_mappings': []})
                if equal and row['kind'] == 'chunk':
                    item.setdefault('line_mappings', []).append({'id': row['id'], 'old_lines': [start + 1, end],
                                                                 'new_lines': list(mapped), 'candidates': [asdict(anchor) for anchor in anchors]})
                if row['source_version'] not in {version['source_version'] for version in item['versions']}:
                    item['versions'].append({'source_version': row['source_version'], 'changes': [
                        {'operation': tag, 'old_lines': [i + 1, j], 'new_lines': [k + 1, l],
                         'old_text': ''.join(before[i:j]), 'new_text': ''.join(after[k:l])}
                        for tag, i, j, k, l in opcodes if tag != 'equal']})
        if reasons:
            item = semantic.setdefault(path, {'path': path, 'members': [], 'versions': []})
            item['members'].append({'id': row['id'], 'kind': row['kind'], 'reasons': reasons,
                                    'source_version': row['source_version'], 'start_line': row['start_line'],
                                    'end_line': row['end_line']})
    # A source version is not an acceptance marker. Compute uncovered original
    # ranges from current fresh members and independently proved old chunks;
    # old summaries never prove acceptance of the new source's context.
    for path in by_path:
        active = [row for row in members if row['path'] == path and not row['retired']]
        if not active:
            semantic.setdefault(path, {'path': path, 'members': [], 'versions': []})['reason'] = 'no_active_knowledge'
            continue
        current = current_sources[path]
        if current is None or isinstance(current, ImageSource):
            continue
        item = semantic.get(path)
        current_lines = current.text.splitlines(keepends=True)
        line_count = len(current_lines)
        covered = set()
        for row in active:
            if row['stale']:
                continue
            if row['source_revision'] == current.revision:
                mapped = (row['start_line'], row['end_line'])
            else:
                if row['kind'] != 'chunk':
                    continue
                old = snapshot(row['source_version'])
                if old['kind'] != 'text':
                    continue
                opcodes = line_changes(old['text'], current.text)
                mapped = mapped_line_range(opcodes, row['start_line'], row['end_line'])
                if mapped is None or len(locate_lines(old['text'], current.text, row['start_line'], row['end_line'])) != 1:
                    continue
            covered.update(range(mapped[0], mapped[1] + 1))
        # Independent current ranges retain gaps across arbitrarily many source
        # versions, including a first partial acceptance without a predecessor.
        missing = []
        start = None
        for number in range(1, line_count + 2):
            if number <= line_count and number not in covered:
                if start is None:
                    start = number
            elif start is not None:
                text = ''.join(current_lines[start - 1:number - 1])
                missing.append({'start_line': start, 'end_line': number - 1, 'text': text})
                start = None
        if missing:
            item = semantic.setdefault(path, {'path': path, 'members': [], 'versions': []})
            item['uncovered_ranges'] = missing
    # Remove entries created only to inspect unchanged sibling snapshots.
    semantic = {path: item for path, item in semantic.items()
                if item.get('reason') or item['members'] or item.get('uncovered_ranges')}
    for item in semantic.values():
        ids = {member['id'] for member in item['members']}
        related_nodes = [row for row in nodes if not row['retired'] and any(
            basis['member'] in ids for basis in row.get('basis', []))]
        node_ids = {row['id'] for row in related_nodes}
        item['related_nodes'] = related_nodes
        item['related_edges'] = [row for row in edges if not row['retired'] and (
            row['in'] in ids | node_ids or row['out'] in ids | node_ids or
            any(basis['member'] in ids for basis in row.get('basis', [])))]
    pending_relations = [{'id': row['id'], 'basis': row.get('basis', [])}
                         for row in [*nodes, *edges] if row['stale'] and not row['retired']]
    material = {'changes': changes, 'mechanical': receipts, 'reused_chunks': reused_chunks,
                'semantic': list(semantic.values()),
                'pending_relations': pending_relations}
    destination = memory.config.memory_dir / 'maintenance'
    destination.mkdir(parents=True, exist_ok=True)
    receipt = destination / f'{uuid4().hex}.json'
    receipt.write_text(json.dumps(material, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'mechanical_batches': len(receipts), 'reused_chunks': len(reused_chunks), 'semantic_sources': len(semantic),
            'pending_relations': len(pending_relations), 'needs_semantic': bool(semantic or pending_relations),
            'receipt': str(receipt)}

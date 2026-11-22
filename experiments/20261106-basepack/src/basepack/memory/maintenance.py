"""Task-scoped stop and publication arbitration shared by host and worker."""

from contextlib import contextmanager
import errno
import os
from pathlib import Path
import time


class MaintenanceStopped(RuntimeError):
    pass


@contextmanager
def _locked(path, timeout=0.5):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as file:
        deadline = time.monotonic() + timeout
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


def maintain(memory, scope, *, include_registered=False, control=None, timeout=600,
             expected_snapshots=None, discover_graph=False):
    """Refresh mechanically equivalent originals and retain a semantic handoff.

    This is an explicit maintenance action. Query actions never call it.
    Source snapshots, member versions and stale state remain authoritative.
    """
    from dataclasses import asdict
    from hashlib import sha256
    import json
    import re
    from uuid import uuid4

    from .content import SourceContent, comparison_text, line_changes, locate_lines, mapped_line_range, original_text
    from . import feedback
    from .images import ImageSource
    from .privacy import privacy_rules, source_private
    from .store import _record, _sql

    if control:
        check(control)
    known = memory._rows('source')
    all_by_path = {row['path']: row for row in known if not row.get('deleted')}
    root = memory.config.root.resolve()
    selected = [(root / path).resolve() for path in scope]
    def in_scope(path):
        candidate = (root / path).resolve()
        return any(candidate == prefix or candidate.is_relative_to(prefix) for prefix in selected)
    by_path = {path: row for path, row in all_by_path.items() if include_registered or in_scope(path)}
    included = list(dict.fromkeys([*scope, *by_path]))
    expected_snapshots = expected_snapshots or {}
    changes = memory._check_changes(list(by_path.values()), included, deep=True, expected_snapshots=expected_snapshots)
    members = memory._rows('member')
    nodes = memory._rows('node')
    edges = memory._rows('semantic')
    snapshots = {}

    def load_source(path, kind):
        return memory._load_source(path, kind, expected_revision=expected_snapshots.get(path))

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

    def same_locator(row, old, current):
        if not row.get('locator'):
            return True
        previous = original_text(SourceContent(row['path'], '', 0, 0, old), row['start_line'],
                                 row['end_line'], row['locator'])
        try:
            return previous == original_text(current, row['start_line'], row['end_line'], row['locator'])
        except ValueError:
            # A changed source can move or remove the old location; reread it.
            return False
    receipts = []
    accepted_scope = []
    reused_chunks = []
    candidates = {}
    mechanical_dependency_pending = set()
    completed_empty = set()
    refreshed_privacy = set()
    unavailable_privacy_review = set()
    change_by_path = {row['path']: row for row in changes}
    for path, change in change_by_path.items():
        if control:
            check(control)
        if change['kind'] not in {'added', 'modified'}:
            continue
        previous = by_path.get(path)
        current = load_source(path, previous.get('kind') if previous else None)
        if (previous and change.get('privacy_changed') and previous['revision'] == current.revision
                and not source_private(path, privacy_rules(memory.config)['private_scope'])
                and snapshot(previous['version']).get('private') is not False
                and snapshot(previous['version']).get('unavailable_gaps')):
            unavailable_privacy_review.add(path)
            continue
        source = {'path': path, 'revision': current.revision}
        if previous:
            source['id'] = previous['id']
        active = [row for row in members if row['path'] == path and not row['retired']]
        if not isinstance(current, ImageSource) and not current.text and not active:
            candidates[path] = {'source': source, 'members': [], 'reused': []}
            completed_empty.add(path)
            continue
        if change['kind'] == 'added':
            continue
        if current.revision == previous['revision'] and not change.get('privacy_changed'):
            candidates[path] = {'source': source, 'members': [], 'reused': []}
            continue
        if isinstance(current, ImageSource) or not active:
            continue
        # Never treat a newer accepted source as proof that an older member was
        # accepted: compare every active member's own version.
        equivalent = not any(row['stale'] for row in active) and all(
            snapshot(row['source_version'])['kind'] == 'text' and
            normalize(snapshot(row['source_version'])['text']) == normalize(current.text) and
            same_locator(row, snapshot(row['source_version'])['text'], current) for row in active)
        if not equivalent:
            by_id = {row['id']: row for row in members}
            accepted = []
            for row in active:
                if row['kind'] != 'chunk' or row['stale'] or row.get('basis') or row.get('locator'):
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
                candidates[path] = {'source': source, 'members': accepted,
                                    'reused': [item['id'] for item in accepted]}
            continue
        accepted = []
        for row in active:
            item = {key: row[key] for key in ('id', 'kind', 'path', 'parent', 'title', 'start_line',
                                               'end_line', 'mandatory', 'coverage_gaps')}
            if row.get('locator'):
                item['locator'] = row['locator']
            item['evidence'] = [basis['member'] for basis in row.get('basis', [])]
            if row['kind'] != 'chunk':
                item['text'] = row['text']
            accepted.append(item)
        candidates[path] = {'source': source, 'members': accepted, 'reused': []}

    # Evidence members accepted by this run must publish together with their
    # dependents, so both the basis and expected versions describe one state.
    candidate_paths = {item['id']: path for path, candidate in candidates.items()
                       for item in candidate['members']}
    linked = {path: set() for path in candidates}
    for path, candidate in candidates.items():
        for item in candidate['members']:
            for dependency in item.get('evidence', []):
                other = candidate_paths.get(dependency)
                if other is not None:
                    linked[path].add(other)
                    linked[other].add(path)
    remaining = set(candidates)
    while remaining:
        group, pending = set(), [min(remaining)]
        while pending:
            path = pending.pop()
            if path not in group:
                group.add(path)
                pending.extend(linked[path] - group)
        remaining -= group
        accepted = [item for path in sorted(group) for item in candidates[path]['members']]
        accepted_ids = {item['id'] for item in accepted}
        by_id = {row['id']: row for row in members}
        closed = True
        for item in accepted:
            for dependency in item.get('evidence', []):
                if dependency in accepted_ids:
                    continue
                evidence = by_id[dependency]
                if evidence['stale'] or evidence['retired']:
                    closed = False
                    continue
                try:
                    original = load_source(evidence['path'], evidence['kind'])
                except FileNotFoundError:
                    closed = False
                    continue
                if original.revision != evidence['source_revision']:
                    closed = False
        if not closed:
            mechanical_dependency_pending.update(accepted_ids)
            continue
        from .draft import freeze
        batch = freeze([{'sources': [candidates[path]['source'] for path in sorted(group)],
                         'expected': {row['id']: row['knowledge_revision'] for row in members},
                         'members': accepted}], config=memory.config)
        batch['expected_status'] = {row['id']: not (row['stale'] or row['retired']) for row in members}
        receipts.append(memory.apply(batch, control=control, timeout=timeout))
        accepted_scope.extend({'path': path, 'revision': candidates[path]['source']['revision']} for path in sorted(group))
        refreshed_privacy.update(group)
        reused_chunks.extend(member for path in sorted(group) for member in candidates[path]['reused'])
        known = memory._rows('source')
        by_path = {row['path']: row for row in known if not row.get('deleted')
                   and (include_registered or in_scope(row['path']))}
        members = memory._rows('member')

    if receipts:
        nodes, edges = memory._rows('node'), memory._rows('semantic')
    semantic = {}
    for change in changes:
        if change['kind'] in {'added', 'deleted'} and change['path'] not in completed_empty:
            semantic[change['path']] = {'path': change['path'], 'reason': change['kind'], 'members': [], 'versions': []}
        elif change['path'] in unavailable_privacy_review:
            semantic[change['path']] = {'path': change['path'], 'reason': 'unavailable_gaps_privacy_review',
                                        'members': [], 'versions': []}
        elif change.get('privacy_changed') and change['path'] not in refreshed_privacy:
            semantic[change['path']] = {'path': change['path'], 'reason': 'privacy_changed', 'members': [], 'versions': []}
    current_sources = {}

    def current_source(path, kind):
        if path not in current_sources:
            try:
                current_sources[path] = load_source(path, kind)
            except FileNotFoundError:
                current_sources[path] = None
        return current_sources[path]

    member_by_id = {row['id']: row for row in members}
    records_by_id = {row['id']: row for row in [*members, *nodes, *edges]}

    def current_reference(ref):
        record = records_by_id.get(ref['id'])
        if (record is None or record['stale'] or record['retired']
                or record['knowledge_revision'] != ref['knowledge_revision']):
            return False
        relevant = [record] if record['id'] in member_by_id else [
            member_by_id.get(basis['member']) for basis in record.get('basis', [])]
        for member in relevant:
            if member is None or member['stale'] or member['retired']:
                return False
            original = current_source(member['path'], member['kind'])
            if original is None or original.revision != member['source_revision']:
                return False
        return True

    def reviewed(path, current):
        """Return current-version dispositions whose referenced knowledge remains valid."""
        source = by_path.get(path)
        if source is None or current is None or source['revision'] != current.revision:
            return [], [], []
        version = snapshot(source['version'])
        dispositions = []
        for item in version.get('dispositions', []):
            if item['kind'] == 'duplicate' and not all(current_reference(ref)
                                                        for ref in item['representations']):
                continue
            dispositions.append(item)
        coarse = [row for row in members if row['path'] == path and not row['retired']
                  and not row['stale'] and row['source_revision'] == current.revision]
        if isinstance(current, ImageSource):
            deferred = [entry for entry in version.get('deferred_refinement', [])
                        if entry.get('whole_image') and any(row['kind'] == 'image' for row in coarse)]
        else:
            deferred = [entry for entry in version.get('deferred_refinement', []) if any(
                row['kind'] in {'file', 'section'} and row['start_line'] <= entry['start_line']
                and entry['end_line'] <= row['end_line'] for row in coarse)]
        return dispositions, deferred, version.get('unavailable_gaps', [])

    for row in members:
        if row['retired'] or row['path'] not in by_path:
            continue
        path = row['path']
        reasons = []
        if row['stale']:
            reasons.append('stale')
        if row['id'] in mechanical_dependency_pending:
            reasons.append('mechanical_dependency_pending')
        current = current_source(path, row['kind'])
        _, deferred, unavailable = reviewed(path, current)
        reviewed_gaps = {(gap['member'], gap['knowledge_revision'], gap['gap'])
                         for item in deferred for gap in item.get('gaps', [])}
        if (row.get('stale') is False and row.get('retired') is False and current is not None
                and row['source_revision'] == current.revision):
            reviewed_gaps.update((gap['member'], gap['knowledge_revision'], gap['gap']) for gap in unavailable)
        if any((row['id'], row['knowledge_revision'], gap) not in reviewed_gaps
               for gap in row.get('coverage_gaps', [])):
            reasons.append('coverage_gaps')
        if current is None:
            reasons.append('missing')
        if current is not None and current.revision != row['source_revision']:
            old = snapshot(row['source_version'])
            if isinstance(current, ImageSource) or old['kind'] != 'text':
                reasons.append('changed')
            elif not same_locator(row, old['text'], current):
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
        current = current_source(path, by_path[path].get('kind'))
        dispositions, deferred, _ = reviewed(path, current)
        if not active:
            if current is not None and not isinstance(current, ImageSource) and not current.text:
                continue
            if isinstance(current, ImageSource):
                if not any(item.get('whole_image') for item in dispositions):
                    semantic.setdefault(path, {'path': path, 'members': [], 'versions': []})['reason'] = 'no_active_knowledge'
                continue
            if current is None:
                semantic.setdefault(path, {'path': path, 'members': [], 'versions': []})['reason'] = 'no_active_knowledge'
                continue
        if current is None or isinstance(current, ImageSource):
            continue
        item = semantic.get(path)
        current_lines = current.text.splitlines(keepends=True)
        line_count = len(current_lines)
        covered = set()
        partial = {}
        for entry in [*dispositions, *deferred]:
            covered.update(range(entry['start_line'], entry['end_line'] + 1))
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
            locator = row.get('locator')
            if locator:
                for number in range(mapped[0], mapped[1] + 1):
                    start_col = locator['start_col'] if number == mapped[0] else 0
                    end_col = locator['end_col'] if number == mapped[1] else len(current_lines[number - 1])
                    partial.setdefault(number, []).append((start_col, end_col))
            else:
                covered.update(range(mapped[0], mapped[1] + 1))
        # A partial line is covered only when its actual characters are covered.
        partial_missing = []
        for number, intervals in partial.items():
            if number in covered:
                continue
            line = current_lines[number - 1]
            position = 0
            for left, right in sorted(intervals):
                if left > position and line[position:left].strip():
                    partial_missing.append({'start_line': number, 'end_line': number,
                                            'locator': {'start_col': position, 'end_col': left},
                                            'text': line[position:left]})
                position = max(position, right)
            if position < len(line) and line[position:].strip():
                partial_missing.append({'start_line': number, 'end_line': number,
                                        'locator': {'start_col': position, 'end_col': len(line)},
                                        'text': line[position:]})
            covered.add(number)
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
                if text.strip():
                    missing.append({'start_line': start, 'end_line': number - 1, 'text': text})
                start = None
        missing.extend(partial_missing)
        if missing:
            item = semantic.setdefault(path, {'path': path, 'members': [], 'versions': []})
            if not active:
                item['reason'] = 'no_active_knowledge'
            item['uncovered_ranges'] = missing
    # Remove entries created only to inspect unchanged sibling snapshots.
    semantic = {path: item for path, item in semantic.items()
                if item.get('reason') or item['members'] or item.get('uncovered_ranges')}
    for item in semantic.values():
        original = current_source(item['path'], by_path.get(item['path'], {}).get('kind'))
        item['current_revision'] = original.revision if original is not None else None
        item['accepted_source_version'] = by_path.get(item['path'], {}).get('version')
        item['category'] = ('existing_change' if any(row['path'] == item['path'] for row in members)
                            or item.get('reason') == 'deleted' else 'initial')
        ids = {member['id'] for member in item['members']}
        related_nodes = [row for row in nodes if not row['retired'] and any(
            basis['member'] in ids for basis in row.get('basis', []))]
        node_ids = {row['id'] for row in related_nodes}
        item['related_nodes'] = related_nodes
        item['related_edges'] = [row for row in edges if not row['retired'] and (
            row['in'] in ids | node_ids or row['out'] in ids | node_ids or
            item['path'] in row.get('scope_paths', ()) or
            any(basis['member'] in ids for basis in row.get('basis', [])))]
    selected_ids = {row['id'] for row in members if row['path'] in by_path}
    relevant_graph = {row['id'] for row in nodes if any(
        basis['member'] in selected_ids for basis in row.get('basis', []))}
    relevant_graph.update(row['id'] for row in edges if (
        row['in'] in selected_ids | relevant_graph or row['out'] in selected_ids | relevant_graph or
        any(path in by_path for path in row.get('scope_paths', ())) or
        any(basis['member'] in selected_ids for basis in row.get('basis', []))))
    pending_relations = [{'id': row['id'], 'basis': row.get('basis', []), 'scope_paths': row.get('scope_paths', [])}
                         for row in [*nodes, *edges] if row['stale'] and not row['retired']
                         and (include_registered or row['id'] in relevant_graph)]
    reports = feedback.pending(memory)
    pending_feedback = [row for row in reports if include_registered or
                        row.get('target') in selected_ids | relevant_graph or
                        (row.get('source') and in_scope(row['source']))]
    material = {'workset': {'discovered': list(scope), 'included': included,
                            'accepted': accepted_scope},
                'changes': changes, 'mechanical': receipts, 'reused_chunks': reused_chunks,
                'semantic': list(semantic.values()),
                'pending_relations': pending_relations, 'feedback': pending_feedback,
                'acceptance_scope': {'kind': 'fixed_candidate_set', 'priority_owner': 'host_agent',
                                     'current_revision': 'discovery_observation',
                                     'candidate_versions': 'prepare_current_and_report_accepted_revision',
                                     'new_candidates': 'outside_this_receipt'}}
    graph_candidates = []
    if discover_graph:
        from .graph_maintenance import nominate
        from .graph_review import reviewed_pairs

        if control:
            check(control)
        eligible = {path: row for path, row in by_path.items()
                    if path not in change_by_path and path not in semantic}
        graph_candidates = nominate(memory, members=members, eligible_sources=eligible,
                                    reviewed=reviewed_pairs(memory.config.memory_dir))
        material['graph_candidates'] = graph_candidates
    destination = memory.config.memory_dir / 'maintenance'
    destination.mkdir(parents=True, exist_ok=True)
    receipt = destination / f'{uuid4().hex}.json'
    receipt.write_text(json.dumps(material, ensure_ascii=False, indent=2), encoding='utf-8')
    result = {'mechanical_batches': len(receipts), 'reused_chunks': len(reused_chunks), 'semantic_sources': len(semantic),
              'pending_relations': len(pending_relations), 'feedback': len(pending_feedback),
              'needs_semantic': bool(semantic or pending_relations or pending_feedback or graph_candidates),
              'receipt': str(receipt)}
    if discover_graph:
        result['graph_candidates'] = len(graph_candidates)
    return result

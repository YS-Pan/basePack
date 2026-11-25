"""Index authorized native text in memory, retaining vectors and evidence locators."""

from collections import Counter, defaultdict, deque
from datetime import UTC, datetime
from hashlib import sha256
from ipaddress import ip_address
import json
from math import isfinite
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import urlsplit
from uuid import UUID

from basepack.embedding.admin import status
from basepack.embedding.client import EmbeddingClient
from basepack.embedding.qwen3_vl import MAX_REQUEST_INPUTS
from basepack.runtime.recovery import RuntimeStartRequired

from . import codex_segments
from .graph_write import Vertex, fact, knowledge_ids, set_state, state_ref, supersede
from .owner import check_owned
from .privacy import privacy_rules, source_private
from .query import normalize_scope
from .store import _Record, _query_wire_size, _record, _sql


_SCHEMA_VERSION = 1
_SEGMENT_VERSION = 3
_PART_FIELDS = ('thread_id', 'turn_id', 'item_id', 'part', 'role', 'part_sha256', 'byte_start', 'byte_end')
_TOKEN_LIMIT = re.compile(r"Request input indices exceeding the limit \(0-based\): (\[[0-9, ]+\]);")
_SAFE_GAP_FIELDS = {'reason', 'thread_id', 'turn_id', 'item_id', 'part', 'role', 'part_type',
                    'source_thread_id', 'ancestor_thread_id', 'binding_reason', 'method', 'rpc_code'}
_ROLE_OBSERVATION_COUNTS = ('assistant_only_turns', 'native_user_items', 'native_assistant_items')
_UNAVAILABLE_CAPTURE_REASONS = {'host_thread_unavailable', 'ancestry_unavailable', 'host_items_unavailable',
                                'incomplete_host_history', 'host_history_empty_with_preview'}


def _hash(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def _digest(text):
    return sha256(text.encode('utf-8')).hexdigest()


def _identity(thread_id):
    return _Record('codex_thread', _digest(str(UUID(thread_id))))


def _authorized_parts(snapshot, thread_id):
    seen = set()
    parts = []
    for part in snapshot['parts']:
        text = part['text']
        raw = text.encode('utf-8')
        bookmark = {key: part['bookmark'][key] for key in _PART_FIELDS}
        if (str(UUID(bookmark['thread_id'])) != thread_id or bookmark['role'] not in {'user', 'assistant'}
                or any(not isinstance(bookmark[key], str) or not bookmark[key] for key in ('turn_id', 'item_id'))
                or type(bookmark['part']) is not int or bookmark['part'] < 0
                or type(bookmark['byte_start']) is not int or type(bookmark['byte_end']) is not int
                or bookmark['byte_start'] != 0 or bookmark['byte_end'] != len(raw)
                or bookmark['part_sha256'] != sha256(raw).hexdigest()):
            raise ValueError('Native dialogue part bookmark does not match the authorized bytes')
        bookmark['thread_id'] = thread_id
        part_id = _Record('codex_part', _hash([thread_id, bookmark['turn_id'], bookmark['item_id'], bookmark['part']]))
        if part_id in seen:
            raise ValueError('Native dialogue capture repeated a part locator')
        seen.add(part_id)
        parts.append((part_id, bookmark, text, raw))
    return parts


def _safe_gaps(gaps):
    return [{key: value for key, value in gap.items() if key in _SAFE_GAP_FIELDS
             and isinstance(value, (str, int))} for gap in gaps]


def _safe_observations(observations):
    return [{'kind': 'assistant_only_native_turns', **{key: item[key] for key in _ROLE_OBSERVATION_COUNTS}}
            for item in observations if item.get('kind') == 'assistant_only_native_turns'
            and all(type(item.get(key)) is int and item[key] >= 0 for key in _ROLE_OBSERVATION_COUNTS)]


def _message_accounting(census):
    keys = ('host_message_count', 'known_nonempty_messages', 'unknown_messages',
            'partial_messages', 'unreadable_messages')
    if census is None:
        return dict.fromkeys(keys) | {'items': []}
    fields = ('turn_id', 'item_id', 'role', 'readability', 'text_status', 'non_text_parts')
    items = [{key: item[key] for key in fields} for item in census]
    readability = Counter(item['readability'] for item in items)
    counts = (len(items), sum(item['text_status'] == 'nonempty' for item in items),
              len(items) - readability['complete'], readability['partial'], readability['unreadable'])
    return dict(zip(keys, counts)) | {'items': items}


def _ancestors(snapshot, thread_id):
    identities = snapshot.get('ancestor_thread_ids')
    if not isinstance(identities, list) or any(not isinstance(value, str) for value in identities):
        raise ValueError('Native dialogue ancestry must be an explicit authorized UUID list')
    ancestors = sorted({str(UUID(value)) for value in identities})
    if thread_id in ancestors:
        raise ValueError('Native dialogue ancestry includes its own thread')
    return ancestors


def _schema_version(memory):
    return memory._execute('SELECT VALUE version FROM ONLY meta:codex_index;')[0]


def _ensure_schema(memory, publish, *, create):
    installed = _schema_version(memory)
    if installed is None:
        if not create:
            return False
        schema = Path(__file__).with_suffix('.surql').read_text(encoding='utf-8').splitlines()
        publish(['BEGIN;', *schema, f'CREATE meta:codex_index SET version={_SCHEMA_VERSION};', 'COMMIT;'])
    elif installed != _SCHEMA_VERSION:
        raise ValueError('Unsupported Codex index schema')
    return True


def _loopback_embedding(memory):
    endpoint = urlsplit(memory.config.machine.raw['embedding']['endpoint'])
    if (endpoint.scheme not in {'http', 'https'} or endpoint.username is not None
            or not ip_address(endpoint.hostname or '').is_loopback):
        raise ValueError('Native dialogue embedding requires an explicit loopback IP endpoint')


def _oversized(error, size):
    if error.code == 422:
        body = error.read(4096).decode('utf-8', errors='replace')
        match = _TOKEN_LIMIT.search(body)
        if match and 'actual tokens' in body and 'supported_context_tokens=' in body:
            indices = set(json.loads(match[1]))
            if indices and all(0 <= index < size for index in indices):
                return indices
    return set()


def _encode(memory, segments, vectors, identity, unavailable, control, timeout, check_access):
    """Fill gaps in batches, splitting only verified token-limit failures."""
    pending = deque(segments)
    failures = {}
    splits = set()
    dimension = None
    client = EmbeddingClient(memory.config.machine) if unavailable is None else None
    while pending:
        batch = {}
        while pending and len(batch) < MAX_REQUEST_INPUTS:
            piece = pending.popleft()
            digest = _digest(piece.text)
            if digest in splits:
                pending.extendleft(reversed(codex_segments.split(piece)))
            elif digest not in vectors and digest not in failures:
                if piece.text.strip():
                    batch.setdefault(digest, piece)
                else:
                    failures[digest] = 'blank_segment'
        if not batch:
            continue
        if unavailable:
            failures.update(dict.fromkeys(batch, unavailable))
            continue
        check_owned(memory.config.memory_dir, control)
        check_access()
        try:
            reply = client.embed([piece.text for piece in batch.values()], timeout=timeout)
        except HTTPError as error:
            with error:
                indices = _oversized(error, len(batch))
            if not indices:
                failures.update(dict.fromkeys(batch, f'encoding_http_{error.code}'))
                continue
            for index, (digest, piece) in enumerate(batch.items()):
                if index not in indices:
                    pending.append(piece)
                elif leaves := codex_segments.split(piece):
                    splits.add(digest)
                    pending.extend(leaves)
                else:
                    failures[digest] = 'token_limit'
            continue
        except (OSError, RuntimeStartRequired) as error:
            unavailable = type(error).__name__
            failures.update(dict.fromkeys(batch, unavailable))
            continue
        if reply['embedding_identity'] != identity:
            raise ValueError('Embedding service identity changed during native dialogue indexing')
        for digest, vector in zip(batch, reply['vectors'], strict=True):
            if not any(vector) or any(type(value) not in (int, float) or not isfinite(value) for value in vector):
                raise ValueError('Invalid native dialogue embedding vector')
            if dimension is not None and dimension != len(vector):
                raise ValueError('Native dialogue encoder returned inconsistent vector dimensions')
            dimension = len(vector)
            vectors[digest] = vector
    return splits, failures, dimension


def _leaves(piece, splits):
    if _digest(piece.text) in splits:
        for child in codex_segments.split(piece):
            yield from _leaves(child, splits)
    else:
        yield piece


def _part_segments(bookmark, text, raw, previous):
    if previous and previous['bookmark'] == bookmark:
        version, segments = previous['segment_version'], previous['segments']
        legacy_usable = version in (1, 2) and all(item.get('failure') != 'blank_segment' for item in segments)
        if version == _SEGMENT_VERSION or legacy_usable:
            return [codex_segments.Segment(item['byte_start'], item['byte_end'], item['kind'],
                                           raw[item['byte_start']:item['byte_end']].decode('utf-8'))
                    for item in segments]
    return codex_segments.segment(text)


def _part_complete(row):
    endpoint = 0
    for segment in row['segments']:
        if not segment['indexed'] or segment['byte_start'] != endpoint or segment['byte_end'] <= endpoint:
            return False
        endpoint = segment['byte_end']
    return row['nonempty'] and endpoint == row['bookmark']['byte_end'] and endpoint > 0


def _part_text_class(row):
    return ('nonempty' if row['nonempty'] else 'whitespace_only' if row['bookmark']['byte_end'] else 'zero_bytes')


def _counts(parts, gaps):
    messages = defaultdict(list)
    zero_bytes = whitespace_parts = whitespace_bytes = content_bytes = indexed_bytes = 0
    for row in parts:
        bookmark = row['bookmark']
        length = bookmark['byte_end'] - bookmark['byte_start']
        if row['nonempty']:
            messages[(bookmark['turn_id'], bookmark['item_id'])].append(row['complete'])
            content_bytes += length
            indexed_bytes += sum(segment['byte_end'] - segment['byte_start']
                                 for segment in row['segments'] if segment['indexed'])
        elif length:
            whitespace_parts += 1
            whitespace_bytes += length
        else:
            zero_bytes += 1
    unread = {(gap.get('turn_id'), gap.get('item_id')) for gap in gaps if gap.get('reason') != 'non_text_part'}
    return {'observed_parts': len(parts), 'zero_byte_parts': zero_bytes, 'whitespace_only_parts': whitespace_parts,
            'nonempty_parts': len(parts) - zero_bytes - whitespace_parts,
            'covered_parts': sum(row['complete'] for row in parts),
            'indexed_chunks': sum(segment['indexed'] for row in parts for segment in row['segments']),
            'nonempty_messages': len(messages),
            'covered_messages': sum(all(found) and key not in unread for key, found in messages.items()),
            'byte_coverage': {'observed': content_bytes + whitespace_bytes, 'nonempty': content_bytes,
                              'indexed': indexed_bytes, 'unindexed_content': content_bytes - indexed_bytes,
                              'whitespace_not_applicable': whitespace_bytes}}


def _publication_metrics(statements):
    envelope = _query_wire_size('')
    return {'index_statements': len(statements),
            'index_sql_payload_bytes': sum(_query_wire_size(statement) - envelope for statement in statements)}


def _apply_dimensions(report, dimensions, expected):
    if len(dimensions) > 1:
        state = 'mixed'
    elif not dimensions:
        state = 'no_vectors'
    elif expected is None:
        state = 'model_dimension_unknown'
    else:
        state = 'verified' if expected in dimensions else 'mismatch'
    if state in {'mixed', 'mismatch'} and report['status'] == 'ready':
        report['status'] = 'gaps'
    report['vector_dimension_validation'] = {
        'status': state, 'model_dimension': expected,
        'model_dimension_source': 'encoder_response' if expected is not None else 'unknown',
        'observed': [{'dimension': size, 'chunks': count} for size, count in sorted(dimensions.items())],
        'stored_values': 'not_independently_verified',
        'dimension_complete': report['status'] == 'ready' and state == 'verified',
    }


def _thread_node(memory, node, thread_id, path, private, ancestors, previous):
    revision = _hash([thread_id, path, private, ancestors])
    if previous and previous['node_revision'] == revision:
        return revision, []
    row = {'kind': 'codex_thread', 'text': '', 'basis': [], 'path': path, 'private': private,
           'stale': False, 'retired': False, 'knowledge_revision': revision, 'codex_thread_id': thread_id,
           'ancestor_thread_ids': ancestors}
    pins = [(node, revision)]
    if previous:
        pins.append((node, previous['node_revision']))
    versions = knowledge_ids(memory, pins)
    exact = versions[(node, revision)]
    statements = []
    if previous:
        statements.append(supersede(versions[(node, previous['node_revision'])]))
    statements.extend([
        f"IF {_sql(node)}.id != NONE AND {_sql(node)}.codex_thread_id != {_sql(thread_id)} "
        "{ THROW 'Native dialogue node conflicts with an existing record'; };",
        f'UPSERT {_sql(node)} CONTENT {_sql(row)} RETURN NONE;',
        set_state(exact, 'current'),
        f'UPDATE {_sql(exact)} SET private={_sql(private)},scope_paths={_sql([path])}, '
        f'codex_thread_id={_sql(thread_id)},ancestor_thread_ids={_sql(ancestors)},'
        f'state={state_ref(exact)} RETURN NONE;',
        fact(Vertex(exact, private, (path,)), Vertex(node, private, (path,)), 'version_of'),
    ])
    return revision, statements


def _upsert(record, row, vector=None):
    if vector is None:
        return f'UPSERT {_sql(record)} CONTENT {_sql(row)} RETURN NONE;'
    value = f'{_sql(vector)}.embedding' if isinstance(vector, _Record) else _sql(vector)
    return f'UPSERT {_sql(record)} CONTENT {_sql(row)[:-1]},embedding:{value}}} RETURN NONE;'


def _capture_guard(thread, previous):
    ref = _sql(thread)
    revision = _sql(previous['revision']) if previous else 'NONE'
    observed_at = previous.get('capture_failure', {}).get('observed_at', '') if previous else ''
    return (f"IF {ref}.revision != {revision} OR ({ref}.capture_failure.observed_at ?? '') != {_sql(observed_at)} "
            "{ THROW 'Native dialogue index changed'; };")


def _successful_cutoff(metadata):
    return metadata.get('last_successful_cutoff', metadata.get('cutoff') if metadata.get('capture_complete') else None)


def _unavailable_capture(thread_id, gaps):
    return {'thread_id': thread_id, 'status': 'capture_unavailable', 'cutoff': None,
            'capture_complete': False, 'capture_gaps': gaps, 'capture_observations': [], 'parts': [],
            'message_census': _message_accounting(None)}


def _record_capture_failure(memory, thread, thread_id, path, private, gaps, ancestors, *, checkpoint, publish):
    result = dict(_unavailable_capture(thread_id, gaps), publication=_publication_metrics(()))
    if (not gaps or (ancestors is None and any(gap['reason'] not in _UNAVAILABLE_CAPTURE_REASONS for gap in gaps))
            or not _ensure_schema(memory, publish, create=False)):
        return result
    if checkpoint is not None:
        checkpoint()
    previous = memory._execute(f'SELECT * FROM ONLY {_sql(thread)};')[0]
    if (previous is None or previous['path'] != path or previous['private'] != private
            or 'ancestor_thread_ids' not in previous):
        return result
    prior_ancestors = _ancestors(previous, thread_id)
    if ancestors is not None and ancestors != prior_ancestors:
        return result
    if checkpoint is not None:
        from .dialogue_query import authorized_ancestry

        authorized = authorized_ancestry(memory.config, thread_id, prior_ancestors)
        checkpoint()
        if not authorized:
            return result
    visible_ids = {thread_id, *prior_ancestors}
    safe_gaps = [{key: value for key, value in gap.items()
                  if key not in {'source_thread_id', 'ancestor_thread_id'} or value in visible_ids} for gap in gaps]
    failure = {'observed_at': datetime.now(UTC).isoformat(), 'gaps': safe_gaps}
    writes = [_capture_guard(thread, previous), f'UPDATE {_sql(thread)} SET capture_failure={_sql(failure)} RETURN NONE;']
    publish(['BEGIN;', *writes, 'COMMIT;'])
    return dict(result, capture_failure=failure, last_successful_cutoff=_successful_cutoff(previous['coverage']),
                publication=_publication_metrics(writes))


def index_thread(memory, snapshot, *, control, timeout=600, private=True, path, checkpoint=None):
    """Index an in-memory snapshot returned by an authorized native reader."""
    def check_access():
        if checkpoint is not None:
            checkpoint()

    def publish(statements):
        check_access()
        kwargs = {"checkpoint": checkpoint} if checkpoint is not None else {}
        memory._publish(statements, control=control, **kwargs)

    check_owned(memory.config.memory_dir, control)
    check_access()
    thread_id = str(UUID(snapshot['thread_id']))
    thread = _identity(thread_id)
    node = _Record('node', f'codex-{thread.key}')
    path = normalize_scope(path).rstrip('/')
    if not path or type(private) is not bool or type(snapshot['complete']) is not bool:
        raise ValueError('Native dialogue requires a logical path, privacy marker and capture completeness')
    private = private or source_private(path, privacy_rules(memory.config)['private_scope'])
    parts = _authorized_parts(snapshot, thread_id)
    gaps = _safe_gaps(snapshot['gaps'])
    capture_observations = _safe_observations(snapshot.get('capture_observations', ()))
    census = _message_accounting(snapshot.get('message_census'))
    cutoff = snapshot.get('cutoff')
    cutoff = {key: cutoff[key] for key in ('turn_id', 'item_id')} if cutoff is not None else None
    observed = bool(parts) or snapshot['complete'] or census['host_message_count'] is not None
    if not observed:
        ancestors = _ancestors(snapshot, thread_id) if 'ancestor_thread_ids' in snapshot else None
        return _record_capture_failure(memory, thread, thread_id, path, private, gaps, ancestors,
                                       checkpoint=checkpoint, publish=publish)
    ancestors = _ancestors(snapshot, thread_id)
    _ensure_schema(memory, publish, create=True)
    check_access()
    previous, part_rows, chunk_rows = memory._execute(
        f'BEGIN; SELECT * FROM ONLY {_sql(thread)}; '
        f'SELECT * FROM codex_part WHERE thread_id={_sql(thread_id)}; '
        f'SELECT *, array::len(embedding) AS dimensions OMIT embedding '
        f'FROM codex_chunk WHERE thread_id={_sql(thread_id)}; COMMIT;')[1:4]
    if (previous and not snapshot['complete'] and (previous['path'] != path or previous['private'] != private)):
        raise ValueError('A complete native capture is required to change thread path or visibility')
    prior_parts = {_record(row['id']): {key: value for key, value in row.items() if key != 'id'} for row in part_rows}
    prior_chunks = {_record(row['id']): {key: value for key, value in row.items() if key not in {'id', 'dimensions'}}
                    for row in chunk_rows}
    valid_vectors = {_record(row['id']): row['dimensions'] for row in chunk_rows if row['dimensions']}
    prepared = [(part_id, bookmark, bool(text.strip()), _part_segments(bookmark, text, raw, prior_parts.get(part_id)))
                for part_id, bookmark, text, raw in parts]
    pending = [piece for _, _, _, pieces in prepared for piece in pieces]
    unavailable = None
    identity = previous['embedding_identity'] if previous else None
    if pending:
        check_access()
        _loopback_embedding(memory)
        try:
            identity = status(memory.config.machine)['model']['embedding_identity']
        except (OSError, RuntimeStartRequired) as error:
            unavailable = type(error).__name__
    vectors = {row['chunk_sha256']: record for record, row in prior_chunks.items()
               if record in valid_vectors and row['embedding_identity'] == identity}
    splits, failures, measured = (_encode(memory, pending, vectors, identity, unavailable, control, timeout, check_access)
                                  if pending else (set(), {}, None))
    expected_dimension = None
    if previous and previous['embedding_identity'] == identity:
        expected_dimension = previous['coverage'].get('vector_dimension_validation', {}).get('model_dimension')
    if measured is not None:
        if expected_dimension is not None and expected_dimension != measured:
            raise ValueError('Native dialogue encoder dimension changed for the same embedding identity')
        expected_dimension = measured

    parts_to_write, chunks_to_write, parts_seen, chunks_seen = {}, {}, set(), set()
    observations = []
    dimensions = Counter()
    ordinal = 0
    for part_order, (part_id, bookmark, nonempty, pieces) in enumerate(prepared):
        segments = []
        for order, piece in enumerate(leaf for item in pieces for leaf in _leaves(item, splits)):
            digest = _digest(piece.text)
            indexed = digest in vectors
            coverage = {'byte_start': piece.byte_start, 'byte_end': piece.byte_end, 'kind': piece.kind, 'indexed': indexed}
            if not indexed:
                coverage['failure'] = failures[digest]
            segments.append(coverage)
            if indexed:
                vector = vectors[digest]
                dimensions[valid_vectors[vector] if isinstance(vector, _Record) else len(vector)] += 1
                locator = dict(bookmark, byte_start=piece.byte_start, byte_end=piece.byte_end)
                logical_id = _hash([part_id.key, order])
                revision = _hash([logical_id, locator, digest])
                record = _Record('codex_chunk', revision)
                row = {'thread_id': thread_id, 'node': _record(node), 'path': path, 'private': private,
                       'bookmark': locator, 'kind': piece.kind, 'chunk_sha256': digest, 'revision': revision,
                       'logical_id': logical_id, 'ordinal': ordinal, 'part_order': part_order,
                       'segment_order': order, 'embedding_identity': identity}
                previous_chunk = prior_chunks.get(record)
                if previous_chunk and _record(previous_chunk['node']) == node:
                    previous_chunk = dict(previous_chunk, node=node)
                if row != previous_chunk or record not in valid_vectors:
                    chunks_to_write[record] = (row, vector)
                chunks_seen.add(record)
            ordinal += 1
        part_row = {'thread_id': thread_id, 'bookmark': bookmark, 'part_order': part_order, 'nonempty': nonempty,
                    'segment_version': _SEGMENT_VERSION, 'segments': segments}
        part_row['complete'] = _part_complete(part_row)
        part_row['text_class'] = _part_text_class(part_row)
        if not nonempty:
            part_row['encoding_status'] = 'not_applicable'
        observations.append(part_row)
        if part_row != prior_parts.get(part_id):
            parts_to_write[part_id] = part_row
        parts_seen.add(part_id)

    part_deletes = set(prior_parts) - parts_seen if snapshot['complete'] else set()
    observed_bookmarks = {(bookmark['turn_id'], bookmark['item_id'], bookmark['part']) for _, bookmark, _, _ in prepared}
    chunk_deletes = {record for record, row in prior_chunks.items() if record not in chunks_seen and (snapshot['complete'] or (
        row['bookmark']['turn_id'], row['bookmark']['item_id'], row['bookmark']['part']) in observed_bookmarks)}
    check_access()
    node_revision, node_writes = _thread_node(memory, node, thread_id, path, private, ancestors, previous)
    counts = _counts(observations, gaps)
    complete = (snapshot['complete'] and counts['covered_parts'] == counts['nonempty_parts'] and unavailable is None
                and all(gap.get('reason') == 'non_text_part' for gap in gaps))
    last_successful_cutoff = _successful_cutoff(previous['coverage']) if previous else None
    if snapshot['complete']:
        last_successful_cutoff = cutoff
    result = {'thread_id': thread_id, 'node': f'node:{node.key}', 'path': path, 'private': private,
              'ancestor_thread_ids': ancestors,
              'cutoff': cutoff, 'capture_complete': snapshot['complete'], 'capture_gaps': gaps,
              'last_successful_cutoff': last_successful_cutoff,
              'capture_observations': capture_observations, 'message_census': census,
              'part_accounting': 'all_observed_native_text_parts',
              'embedding_identity': identity, 'encoding_status': unavailable or 'available', **counts,
              'status': 'ready' if complete else 'gaps'}
    if snapshot.get('coverage_source') == 'persisted_app_server_items':
        result.update(coverage_source='persisted_app_server_items', original_length='unreported')
    _apply_dimensions(result, dimensions, expected_dimension)
    thread_row = {'thread_id': thread_id, 'node': node, 'path': path, 'private': private,
                  'node_revision': node_revision, 'embedding_identity': identity,
                  'ancestor_thread_ids': ancestors,
                  'observed_parts': sorted(record.key for record in parts_seen), 'coverage': result}
    revision = _hash([result, identity, observations])
    thread_row['revision'] = revision
    if (previous and previous['revision'] == revision and 'capture_failure' not in previous
            and not any((node_writes, parts_to_write, chunks_to_write, part_deletes, chunk_deletes))):
        return dict(result, publication=_publication_metrics(()))
    writes = ['BEGIN;', _capture_guard(thread, previous), *node_writes]
    writes.extend(_upsert(record, row, vector) for record, (row, vector) in chunks_to_write.items())
    writes.extend(_upsert(record, row) for record, row in parts_to_write.items())
    writes.extend(f'DELETE {_sql(record)} RETURN NONE;' for record in sorted(chunk_deletes | part_deletes, key=_sql))
    writes.extend([_upsert(thread, thread_row), 'COMMIT;'])
    metrics = _publication_metrics(writes[1:-1])
    publish(writes)
    return dict(result, publication=metrics)


def coverage(memory, thread_ids):
    """Return only metadata of the caller's already authorized thread set."""
    if not thread_ids:
        return {'threads': []}
    ids = list(dict.fromkeys(str(UUID(value)) for value in thread_ids))
    installed = _schema_version(memory)
    if installed is None:
        return {'threads': [{'thread_id': value, 'status': 'not_indexed'} for value in ids]}
    if installed != _SCHEMA_VERSION:
        raise ValueError('Unsupported Codex index schema')
    refs = _sql([_identity(value) for value in ids])
    selection = _sql(ids)
    threads, parts, chunks = memory._execute(
        f'BEGIN; SELECT * FROM {refs}; SELECT * FROM codex_part WHERE thread_id IN {selection}; '
        'SELECT thread_id,bookmark,embedding_identity,array::len(embedding) AS dimensions '
        f'FROM codex_chunk WHERE thread_id IN {selection}; COMMIT;')[1:4]
    by_thread = {row['thread_id']: row for row in threads}
    indexed = {tuple(row['bookmark'][key] for key in _PART_FIELDS): row['dimensions'] for row in chunks
               if row['dimensions'] and row['embedding_identity'] == by_thread[row['thread_id']]['embedding_identity']}
    part_map = defaultdict(list)
    dimensions = defaultdict(Counter)
    for row in parts:
        current = by_thread[row['thread_id']]['observed_parts']
        if _record(row['id']).key in current:
            for segment in row['segments']:
                bookmark = dict(row['bookmark'], byte_start=segment['byte_start'], byte_end=segment['byte_end'])
                if segment['indexed']:
                    width = indexed.get(tuple(bookmark[key] for key in _PART_FIELDS))
                    if width:
                        dimensions[row['thread_id']][width] += 1
                    else:
                        segment.update(indexed=False, failure='index_vector_missing_or_incompatible')
            row['complete'] = _part_complete(row)
            row.setdefault('text_class', _part_text_class(row))
            if not row['nonempty']:
                row.setdefault('encoding_status', 'not_applicable')
            part_map[row['thread_id']].append({key: value for key, value in row.items() if key != 'id'})

    reports = []
    for value in ids:
        if value not in by_thread:
            reports.append({'thread_id': value, 'status': 'not_indexed'})
            continue
        metadata = by_thread[value]['coverage']
        observed = sorted(part_map[value], key=lambda row: row['part_order'])
        counts = _counts(observed, metadata['capture_gaps'])
        result = dict(metadata, parts=observed, **counts)
        result.setdefault('last_successful_cutoff', _successful_cutoff(metadata))
        result.setdefault('message_census', _message_accounting(None))
        result.setdefault('part_accounting', 'retained_v1_parts_only')
        if result['status'] == 'ready' and result['covered_parts'] != result['nonempty_parts']:
            result['status'] = 'gaps'
        expected = metadata.get('vector_dimension_validation', {}).get('model_dimension')
        _apply_dimensions(result, dimensions[value], expected)
        if (failure := by_thread[value].get('capture_failure')):
            access = {key: result[key] for key in ('path', 'private', 'ancestor_thread_ids')}
            result = dict(_unavailable_capture(value, failure['gaps']), **access, capture_failure=failure,
                          last_successful_cutoff=result['last_successful_cutoff'], retained_index_coverage=result)
        reports.append(result)
    return {'threads': reports}

"""Synthetic native capture, actual database transactions and local encoder boundary."""

from hashlib import sha256
from io import BytesIO
import json
from urllib.error import HTTPError
from uuid import uuid4

import pytest

from basepack.memory import codex_index, codex_segments, owner
from test_memory_store import memory


def part(thread_id, item, role, text, turn='turn'):
    raw = text.encode('utf-8')
    return {'text': text, 'bookmark': {'thread_id': thread_id, 'turn_id': turn, 'item_id': item, 'part': 0,
                                      'role': role, 'part_sha256': sha256(raw).hexdigest(),
                                      'byte_start': 0, 'byte_end': len(raw)}}


def capture(thread, *parts, complete=True, gaps=(), ancestors=()):
    return {'thread_id': thread, 'parts': parts, 'complete': complete, 'gaps': gaps,
            'ancestor_thread_ids': list(ancestors),
            'cutoff': {key: parts[-1]['bookmark'][key] for key in ('turn_id', 'item_id')} if parts else None}


class Encoder:
    def __init__(self):
        self.calls = []
        self.limit = None
        self.failure = None

    def embed(self, inputs, *, timeout):
        self.calls.extend(inputs)
        if self.failure:
            raise self.failure
        if self.limit:
            over = [index for index, text in enumerate(inputs) if len(text) > self.limit]
            if over:
                body = json.dumps({'detail': 'actual tokens exceed supported_context_tokens=32768; '
                                    f'Request input indices exceeding the limit (0-based): {over};'})
                raise HTTPError('http://127.0.0.1/predict', 422, 'token limit', {}, BytesIO(body.encode()))
        return {'embedding_identity': 'local-model', 'vectors': [[float(len(text)), 1.] for text in inputs]}


@pytest.fixture
def writer(memory, monkeypatch):
    encoder = Encoder()
    memory.config.machine.raw['embedding'] = {'endpoint': 'http://127.0.0.1:4000'}
    monkeypatch.setattr(codex_index, 'EmbeddingClient', lambda _: encoder)
    monkeypatch.setattr(codex_index, 'status', lambda _: {'model': {'embedding_identity': 'local-model'}})
    control = str(memory.config.memory_dir / 'test-codex-index.control')
    claim = owner.acquire(memory.config.memory_dir, memory.connection['project_id'], 'synthetic index', control)
    assert claim['acquired']
    try:
        yield encoder, lambda snapshot: codex_index.index_thread(memory, snapshot, control=control, private=False,
                                                                path='codex/synthetic')
    finally:
        owner.stop_owned(memory.config.memory_dir, control)
        owner.release(memory.config.memory_dir, control)


def test_segments_preserve_original_unicode_whitespace_code_and_tail():
    assert codex_segments.segment('否。\r\n')[0].text == '否。\r\n'
    assert codex_segments.segment(' \n ') == []
    text = 'prelude😀\r\n\r\n```python\r\n' + '钮🧪' * 6000 + '\n```\r\nlast phrase\r\n'
    raw = text.encode('utf-8')
    pieces = codex_segments.segment(text)
    assert {piece.kind for piece in pieces} == {'text', 'code'}
    assert b''.join(piece.text.encode('utf-8') for piece in pieces) == raw
    assert all(raw[piece.byte_start:piece.byte_end] == piece.text.encode('utf-8') for piece in pieces)
    assert max(piece.byte_end - piece.byte_start for piece in pieces) <= codex_segments.SEGMENT_BYTES
    assert pieces[-1].text == 'last phrase\r\n'


def test_segment_boundary_keeps_short_whitespace_tail_with_text():
    limit = codex_segments.SEGMENT_BYTES
    for character in ('x', '🧪'):
        width = len(character.encode('utf-8'))
        text = character * (limit // width) + '\n'
        head, tail = codex_segments.segment(text)
        assert head.text + tail.text == text and tail.text == character + '\n'
        assert head.byte_end == tail.byte_start == limit - width and tail.byte_end == limit + 1


def test_soft_boundary_keeps_original_blank_tail_with_sole_nonblank_codepoint():
    limit = codex_segments.SEGMENT_BYTES
    for mark, newline in (('x', '\n'), ('x', '\r\n'), ('🧪', '\n'), ('🧪', '\r\n')):
        for offset in (-1, 0, 1):
            body = mark + ' ' * (limit + offset - len(mark.encode('utf-8'))) + newline
            (piece,) = codex_segments.segment(body)
            assert piece.text == body and (piece.byte_start, piece.byte_end) == (0, len(body.encode('utf-8')))


def test_soft_partition_coalesces_blank_ranges_and_keeps_neighboring_original():
    limit = codex_segments.SEGMENT_BYTES
    prefix, blank, terminal = 'x' * limit, ' ' * (limit * 2), ' 🧪\r\n'
    raw = (prefix + blank + terminal).encode('utf-8')
    back, front = codex_segments.segment(raw.decode('utf-8'))
    assert back.text == prefix + blank and front.text == terminal
    assert back.byte_start == 0 and back.byte_end == front.byte_start == len(prefix + blank)
    assert front.byte_end == len(raw)


def test_confirmed_422_splits_soft_tail_without_retrying_original(writer):
    encoder, index = writer
    limit = codex_segments.SEGMENT_BYTES
    encoder.limit = limit
    thread = str(uuid4())
    body = 'x' + ' ' * (limit * 3 - 1) + '\n'
    snapshot = capture(thread, part(thread, 'soft-tail', 'user', body))
    result = index(snapshot)
    assert encoder.calls == [body, body[:len(body) // 2], body[:len(body) // 4]]
    assert result['status'] == 'gaps' and result['byte_coverage']['observed'] == len(body)
    assert result['byte_coverage']['unindexed_content'] == len(body) - len(body) // 4
    assert index(snapshot)['publication']['index_statements'] == 0
    assert len(encoder.calls) == 3


def test_index_tail_split_preserves_422_progress_and_extreme_blank_gap(memory, writer):
    encoder, index = writer
    encoder.limit = 550
    thread = str(uuid4())
    text = 'x' * 150 + '\t' * 400 + '\n'
    snapshot = capture(thread, part(thread, 'token-split', 'user', text))
    ready = index(snapshot)
    assert encoder.calls == [text, 'x' * 149, 'x' + '\t' * 400 + '\n']
    assert ready['status'] == 'ready' and ready['byte_coverage']['indexed'] == len(text)
    memory._execute('UPDATE codex_part SET segment_version=2;')
    assert index(snapshot)['status'] == 'ready' and len(encoder.calls) == 3

    limit = codex_segments.SEGMENT_BYTES
    encoder.limit = limit
    text = 'x' * limit + ' ' * limit
    result = index(capture(thread, part(thread, 'extreme-blank', 'user', text)))
    assert result['status'] == 'gaps' and result['byte_coverage']['unindexed_content'] == limit
    coverage, = codex_index.coverage(memory, [thread])['threads']
    tail = coverage['parts'][0]['segments'][-1]
    assert (tail['byte_start'], tail['byte_end'], tail['failure']) == (limit, 2 * limit, 'blank_segment')


def test_index_repairs_retained_legacy_blank_segment(writer, monkeypatch):
    encoder, index = writer
    thread = str(uuid4())
    limit = codex_segments.SEGMENT_BYTES
    text = 'x' * limit + '\n'
    snapshot = capture(thread, part(thread, 'legacy-blank', 'user', text))
    with monkeypatch.context() as scoped:
        scoped.setattr(codex_index, '_SEGMENT_VERSION', 1)
        scoped.setattr(codex_segments, 'segment', lambda original: [
            codex_segments.Segment(0, limit, 'text', original[:-1]),
            codex_segments.Segment(limit, limit + 1, 'text', original[-1:])])
        legacy = index(snapshot)
    assert legacy['status'] == 'gaps' and legacy['byte_coverage']['unindexed_content'] == 1
    ready = index(snapshot)
    assert ready['status'] == 'ready' and ready['byte_coverage']['indexed'] == len(text)
    assert encoder.calls == [text[:-1], text[:-2], 'x\n']


def test_index_repairs_dev4_soft_tail_blank_segment(memory, writer, monkeypatch):
    encoder, index = writer
    thread = str(uuid4())
    limit = codex_segments.SEGMENT_BYTES
    prefix = 'y' * limit
    body = prefix + 'x' + ' ' * (limit * 2 - 1) + '\n'
    snapshot = capture(thread, part(thread, 'legacy-soft-tail', 'user', body))
    with monkeypatch.context() as scoped:
        scoped.setattr(codex_index, '_SEGMENT_VERSION', 2)
        scoped.setattr(codex_segments, 'segment', lambda original: [
            codex_segments.Segment(0, limit, 'text', original[:limit]),
            codex_segments.Segment(limit, limit * 2, 'text', original[limit:limit * 2]),
            codex_segments.Segment(limit * 2, len(original), 'text', original[limit * 2:])])
        legacy = index(snapshot)
    assert legacy['status'] == 'gaps' and legacy['byte_coverage']['unindexed_content'] == limit + 1
    original_chunk = memory._execute('SELECT id,embedding FROM codex_chunk WHERE ordinal=0;')[0]
    assert index(snapshot)['byte_coverage']['indexed'] == len(body)
    assert encoder.calls == [prefix, body[limit:limit * 2], body[limit:]]
    assert memory._execute('SELECT id,embedding FROM codex_chunk WHERE ordinal=0;')[0] == original_chunk


def test_native_index_append_edit_stable_graph_and_no_durable_body(memory, writer):
    encoder, index = writer
    thread = str(uuid4())
    first = part(thread, 'first', 'user', '否。')
    repeated = part(thread, 'repeated', 'assistant', '否。')
    paragraph = 'Unchanged synthetic paragraph ' * 170 + '\n\n'
    old_tail = 'Repeated old synthetic phrase ' * 170 + '\r\n'
    longer = part(thread, 'longer', 'assistant', paragraph + old_tail)

    before_schema = codex_index.coverage(memory, [thread])
    assert before_schema['threads'][0]['status'] == 'not_indexed'
    assert index(capture(thread, complete=False, gaps=[{'reason': 'unreadable'}]))['status'] == 'capture_unavailable'
    assert codex_index.coverage(memory, [thread]) == before_schema
    initial = index(capture(thread, first, repeated, longer))
    assert initial['status'] == 'ready' and initial['nonempty_messages'] == initial['covered_messages'] == 3
    assert encoder.calls.count('否。') == 1
    chunks, graph = memory._execute('SELECT * FROM codex_chunk; SELECT * FROM node;')
    assert len(chunks) == 4 and len(graph) == 1 and graph[0]['codex_thread_id'] == thread
    assert len({row['id'] for row in chunks if row['bookmark']['item_id'] in {'first', 'repeated'}}) == 2
    assert all(row['embedding_identity'] == 'local-model' for row in chunks)

    appended = part(thread, 'tail', 'user', 'Synthetic last actual question.')
    count = len(encoder.calls)
    after = index(capture(thread, first, repeated, longer, appended))
    assert after['node'] == initial['node'] and encoder.calls[count:] == [appended['text']]
    again = index(capture(thread, first, repeated, longer, appended))
    assert after['publication']['index_sql_payload_bytes'] > 0
    assert again == dict(after, publication={'index_statements': 0, 'index_sql_payload_bytes': 0})
    assert encoder.calls[count:] == [appended['text']]
    edited_tail = 'Revised synthetic phrase' * 180 + '\r\n'
    edited = part(thread, 'longer', 'assistant', paragraph + edited_tail)
    count = len(encoder.calls)
    result = index(capture(thread, first, repeated, edited, appended))
    assert result['status'] == 'ready' and encoder.calls[count:] == [edited_tail]
    versions, chunks, parts, threads = memory._execute('SELECT * FROM knowledge_version; SELECT * FROM codex_chunk; '
                                                       'SELECT * FROM codex_part; SELECT * FROM codex_thread;')
    assert len(versions) == 1 and versions[0]['codex_thread_id'] == thread
    assert len(chunks) == 5 and [row['bookmark']['part_sha256'] for row in chunks
                                if row['bookmark']['item_id'] == 'longer'] == [edited['bookmark']['part_sha256']] * 2
    assert not any(text in json.dumps([versions, chunks, parts, threads], ensure_ascii=False)
                   for text in [paragraph.strip(), old_tail.strip(), edited_tail.strip(), appended['text'], first['text']])
    report = codex_index.coverage(memory, [thread])['threads'][0]
    assert report['covered_parts'] == 4 and len(report['parts']) == 4
    memory._execute("UPDATE codex_chunk SET embedding=[] WHERE bookmark.item_id='tail';")
    report = codex_index.coverage(memory, [thread])['threads'][0]
    assert report['status'] == 'gaps' and report['covered_parts'] == 3
    assert report['parts'][-1]['segments'][0]['failure'] == 'index_vector_missing_or_incompatible'
    count = len(encoder.calls)
    assert index(capture(thread, first, repeated, edited, appended))['status'] == 'ready'
    assert encoder.calls[count:] == [appended['text']]
    assert codex_index.coverage(memory, [thread])['threads'][0]['covered_parts'] == 4


def test_native_index_exact_token_split_and_incremental_gap_retry(memory, writer):
    encoder, index = writer
    thread = str(uuid4())
    encoder.limit = 3
    message = part(thread, 'part', 'assistant', '一二三四五六七尾')
    result = index(capture(thread, message))
    assert result['status'] == 'ready' and result['indexed_chunks'] == 4
    spans = sorted(memory._execute('SELECT bookmark FROM codex_chunk;')[0], key=lambda row: row['bookmark']['byte_start'])
    raw = message['text'].encode('utf-8')
    assert b''.join(raw[row['bookmark']['byte_start']:row['bookmark']['byte_end']] for row in spans) == raw
    count = len(encoder.calls)
    index(capture(thread, message))
    assert len(encoder.calls) == count
    new = part(thread, 'new', 'user', '尾句。')
    encoder.failure = TimeoutError('synthetic response unavailable')
    result = index(capture(thread, message, new))
    assert result['status'] == 'gaps' and result['covered_parts'] == 1
    assert codex_index.coverage(memory, [thread])['threads'][0]['parts'][1]['segments'][0]['failure'] == 'TimeoutError'
    encoder.failure = None
    count = len(encoder.calls)
    result = index(capture(thread, message, new))
    assert result['status'] == 'ready' and encoder.calls[count:] == [new['text']]


def test_failed_write_keeps_prior_index_and_incomplete_capture_retains_other_parts(memory, writer, monkeypatch):
    _, index = writer
    thread = str(uuid4())
    one = part(thread, 'one', 'user', 'plain first')
    two = part(thread, 'two', 'assistant', 'plain second')
    index(capture(thread, one, two))
    result = index(capture(thread, one, complete=False, gaps=[{'reason': 'host_unreadable', 'text': 'do not store'}]))
    assert result['status'] == 'gaps' and result['capture_gaps'] == [{'reason': 'host_unreadable'}]
    assert len(memory._execute('SELECT id FROM codex_chunk;')[0]) == 2
    blocked = index(capture(thread, complete=False, gaps=[{'reason': 'unavailable'}]))
    assert blocked['status'] == 'capture_unavailable'
    assert codex_index.coverage(memory, [thread])['threads'][0]['parts'] == []
    prior = codex_index.coverage(memory, [thread])
    publish = memory._publish

    def rejected(statements, **kwargs):
        return publish([*statements[:-1], "THROW 'synthetic publication rollback';", statements[-1]], **kwargs)

    with monkeypatch.context() as ctx:
        ctx.setattr(memory, '_publish', rejected)
        with pytest.raises(RuntimeError, match='synthetic publication rollback'):
            index(capture(thread, one, part(thread, 'a-new-id', 'user', 'different synthetic text')))
    assert codex_index.coverage(memory, [thread]) == prior
    assert len(memory._execute('SELECT id FROM codex_chunk;')[0]) == 2


def test_index_requires_ancestry_and_persists_current_and_exact_visibility(memory, writer):
    encoder, index = writer
    thread, parent, ancestor, new_ancestor = (str(uuid4()) for _ in range(4))
    original = part(thread, 'one', 'assistant', 'synthetic authorized thread')
    unproven = capture(thread, original)
    del unproven['ancestor_thread_ids']
    with pytest.raises(ValueError, match='explicit authorized UUID list'):
        index(unproven)
    with pytest.raises(ValueError, match='own thread'):
        index(capture(thread, original, ancestors=[thread]))
    denied = capture(thread, complete=False, gaps=[{'reason': 'ancestor_not_authorized'}])
    del denied['ancestor_thread_ids']
    assert index(denied)['status'] == 'capture_unavailable'
    assert codex_index.coverage(memory, [thread])['threads'][0]['status'] == 'not_indexed'

    result = index(capture(thread, original, ancestors=[parent, ancestor]))
    expected = sorted([parent, ancestor])
    old_node, old_exact, stored = memory._execute('SELECT ancestor_thread_ids,knowledge_revision FROM node; '
                                                  'SELECT ancestor_thread_ids,knowledge_revision FROM knowledge_version; '
                                                  'SELECT ancestor_thread_ids FROM codex_thread;')
    assert old_node[0]['ancestor_thread_ids'] == old_exact[0]['ancestor_thread_ids'] == expected
    assert stored[0]['ancestor_thread_ids'] == expected and result['ancestor_thread_ids'] == expected

    count = len(encoder.calls)
    changed = index(capture(thread, original, complete=False, ancestors=[parent, ancestor, new_ancestor]))
    assert changed['node'] == result['node'] and len(encoder.calls) == count and changed['status'] == 'gaps'
    nodes, versions = memory._execute('SELECT ancestor_thread_ids,knowledge_revision FROM node; '
                                      'SELECT ancestor_thread_ids,knowledge_revision FROM knowledge_version;')
    assert len(nodes) == 1 and nodes[0]['knowledge_revision'] != old_node[0]['knowledge_revision']
    assert nodes[0]['ancestor_thread_ids'] == sorted([parent, ancestor, new_ancestor])
    assert {row['knowledge_revision'] for row in versions} == {old_node[0]['knowledge_revision'], nodes[0]['knowledge_revision']}


def test_index_audits_zero_whitespace_and_all_nonempty_part_bytes(memory, writer):
    encoder, index = writer
    thread = str(uuid4())
    whitespace = '　\r\n\t '
    body = '   分段🙂\r\n' + 'Text with paragraph spaces. ' * 1300 + '\n\n尾部\t \r\n'
    snapshot = capture(thread, part(thread, 'zero', 'user', ''), part(thread, 'blank', 'user', whitespace),
                       part(thread, 'content', 'assistant', body))
    result = index(snapshot)
    observed = codex_index.coverage(memory, [thread])['threads'][0]
    blank_bytes, body_bytes = len(whitespace.encode('utf-8')), len(body.encode('utf-8'))
    for report in (result, observed):
        assert report['status'] == 'ready'
        assert (report['observed_parts'], report['zero_byte_parts'], report['whitespace_only_parts'],
                report['nonempty_parts'], report['covered_parts']) == (3, 1, 1, 1, 1)
        assert report['byte_coverage'] == {'observed': blank_bytes + body_bytes, 'nonempty': body_bytes,
                                           'indexed': body_bytes, 'unindexed_content': 0,
                                           'whitespace_not_applicable': blank_bytes}
    assert [row['text_class'] for row in observed['parts']] == ['zero_bytes', 'whitespace_only', 'nonempty']
    assert [row['encoding_status'] for row in observed['parts'][:2]] == ['not_applicable'] * 2
    assert [row['segments'] for row in observed['parts'][:2]] == [[], []]
    assert b''.join(value.encode('utf-8') for value in encoder.calls) == body.encode('utf-8')
    assert result['publication']['index_sql_payload_bytes'] > 0
    # Retained v1 rows can be read as observed metadata without claiming a fresh host census.
    memory._execute('UPDATE codex_thread UNSET coverage.part_accounting; UPDATE codex_part UNSET text_class,encoding_status;')
    legacy = codex_index.coverage(memory, [thread])['threads'][0]
    assert legacy['part_accounting'] == 'retained_v1_parts_only'
    assert legacy['byte_coverage'] == observed['byte_coverage']


def test_index_checks_encoder_width_and_distinguishes_stored_dimension_evidence(memory, writer, monkeypatch):
    encoder, index = writer
    thread = str(uuid4())
    snapshot = capture(thread, *(part(thread, f'item-{i}', 'user', f'synthetic content {i}') for i in range(3)))
    with monkeypatch.context() as patch:
        patch.setattr(encoder, 'embed', lambda inputs, **kw: {
            'embedding_identity': 'local-model', 'vectors': [[1., 2.], [1., 2., 3.], [2., 2.]],
        })
        with pytest.raises(ValueError, match='inconsistent vector dimensions'):
            index(snapshot)
    assert codex_index.coverage(memory, [thread])['threads'][0]['status'] == 'not_indexed'

    fresh = index(snapshot)['vector_dimension_validation']
    assert fresh == {'status': 'verified', 'model_dimension': 2, 'model_dimension_source': 'encoder_response',
                     'observed': [{'dimension': 2, 'chunks': 3}],
                     'stored_values': 'not_independently_verified', 'dimension_complete': True}
    assert codex_index.coverage(memory, [thread])['threads'][0]['vector_dimension_validation'] == fresh

    memory._execute("UPDATE codex_chunk SET embedding=[1.0,2.0,3.0] WHERE bookmark.item_id='item-1'; "
                    "UPDATE codex_chunk SET embedding=[] WHERE bookmark.item_id='item-2';")
    verified = codex_index.coverage(memory, [thread])['threads'][0]
    assert verified['status'] == 'gaps' and verified['indexed_chunks'] == 2
    assert verified['vector_dimension_validation']['status'] == 'mixed'
    assert verified['vector_dimension_validation']['observed'] == [{'dimension': 2, 'chunks': 1},
                                                                  {'dimension': 3, 'chunks': 1}]
    assert not verified['vector_dimension_validation']['dimension_complete']

    memory._execute("UPDATE codex_thread UNSET coverage.vector_dimension_validation; "
                    "UPDATE codex_chunk SET embedding=[1.0,2.0] WHERE bookmark.item_id IN ['item-1','item-2'];")
    old = codex_index.coverage(memory, [thread])['threads'][0]
    assert old['status'] == 'ready' and old['indexed_chunks'] == 3
    legacy = old['vector_dimension_validation']
    assert legacy['status'] == 'model_dimension_unknown' and legacy['model_dimension'] is None
    assert legacy['observed'] == [{'dimension': 2, 'chunks': 3}] and not legacy['dimension_complete']


def test_index_persists_role_observations_without_reclassifying_retained_gaps(memory, writer):
    _, index = writer
    thread = str(uuid4())
    assistant = part(thread, 'assistant-item', 'assistant', 'observed original only')
    observation = {'kind': 'assistant_only_native_turns', 'assistant_only_turns': 1,
                   'native_user_items': 0, 'native_assistant_items': 1}
    result = index(dict(capture(thread, assistant), capture_observations=[dict(observation, text='not metadata')]))
    assert result['status'] == 'ready' and result['capture_complete'] and result['capture_gaps'] == []
    assert result['capture_observations'] == [observation]
    stored = codex_index.coverage(memory, [thread])['threads'][0]
    assert stored['covered_messages'] == 1 and stored['capture_observations'] == [observation]
    assert stored['parts'][0]['bookmark']['role'] == 'assistant'

    memory._execute("UPDATE codex_thread SET coverage.status='gaps',coverage.capture_complete=false,"
                    "coverage.capture_gaps=[{reason:'host_user_message_unobserved'}]; "
                    "UPDATE codex_thread UNSET coverage.capture_observations;")
    retained = codex_index.coverage(memory, [thread])['threads'][0]
    assert not retained['capture_complete'] and retained['status'] == 'gaps'
    assert retained['capture_gaps'] == [{'reason': 'host_user_message_unobserved'}]
    assert 'capture_observations' not in retained

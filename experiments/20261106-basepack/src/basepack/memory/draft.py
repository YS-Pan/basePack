"""Freeze scoped author drafts into one immutable publication batch."""

from copy import deepcopy
from uuid import uuid4


def freeze(drafts):
    if not drafts:
        raise ValueError('At least one draft is required')
    from .store import _record

    merged = {'protocol': 2, 'batch_id': uuid4().hex, 'new_members': [], 'member_mapping': [],
              'sources': [], 'expected': {}, 'members': []}
    drafts = deepcopy(drafts)
    scopes = []
    for scope, draft in enumerate(drafts):
        if any(key in draft for key in ('protocol', 'batch_id', 'new_members', 'member_mapping')):
            raise ValueError('Expected an author draft, not a frozen batch')
        allowed = {'sources', 'expected', 'members', 'nodes', 'edges', 'delete_members',
                   'delete_nodes', 'delete_edges', 'corrections', 'context'}
        unknown = draft.keys() - allowed
        if unknown:
            raise ValueError(f'Unknown draft fields: {sorted(unknown)}')
        ids = []
        for index, item in enumerate(draft.get('members', [])):
            if 'id' in item:
                ids.append(item['id'])
            else:
                identity = 'member:' + uuid4().hex
                ids.append(identity)
                merged['new_members'].append(identity)
                merged['member_mapping'].append({'draft': scope, 'member': index, 'id': identity})
        scopes.append(ids)

    for scope, draft in enumerate(drafts):
        members = draft.get('members', [])
        ids = scopes[scope]
        def ref(value):
            if isinstance(value, dict):
                if set(value) not in ({'member'}, {'draft', 'member'}) or type(value['member']) is not int:
                    raise ValueError('Member reference must name a draft and member position')
                selected = value.get('draft', scope)
                index = value['member']
                if type(selected) is not int or selected < 0 or selected >= len(scopes):
                    raise ValueError(f'Draft index out of range: {selected}')
                if index < 0 or index >= len(scopes[selected]):
                    raise ValueError(f'Member index out of range: {index}')
                return scopes[selected][index]
            if not isinstance(value, str):
                raise ValueError('Reference must be a record ID or local member position')
            return value

        for item, identity in zip(members, ids):
            item['id'] = identity
            if item.get('parent') is not None:
                item['parent'] = ref(item['parent'])
            item['evidence'] = [ref(value) for value in item.get('evidence', [])]
        for key in ('nodes', 'edges'):
            for item in draft.get(key, []):
                item['evidence'] = [ref(value) for value in item.get('evidence', [])]
                if key == 'edges':
                    for endpoint in ('in', 'out'):
                        item[endpoint] = ref(item[endpoint])
        for source in draft['sources']:
            if 'path' in source and any(old.get('path') == source['path'] for old in merged['sources']):
                raise ValueError(f"Duplicate source across drafts: {source.get('path')}")
            if 'id' in source and any('id' in old and _record(old['id'], 'source') == _record(source['id'], 'source')
                                      for old in merged['sources']):
                raise ValueError(f"Duplicate source identity across drafts: {source['id']}")
            merged['sources'].append(source)
        for key, revision in draft.get('expected', {}).items():
            if key in merged['expected'] and merged['expected'][key] != revision:
                raise ValueError(f'Conflicting expected revisions: {key}')
            merged['expected'][key] = revision
        merged['members'].extend(members)
        for key in ('nodes', 'edges', 'delete_members', 'delete_nodes', 'delete_edges', 'corrections'):
            if key in draft:
                merged.setdefault(key, []).extend(draft[key])
        if 'context' in draft:
            if 'context' in merged and merged['context'] != draft['context']:
                raise ValueError('Conflicting draft contexts')
            merged['context'] = draft['context']
    return merged


def validate_batch(batch):
    """Reject old protocols, ambiguous writes and non-UUID member references."""
    import re
    from .store import _record

    if batch.get('protocol') != 2 or not re.fullmatch(r'[0-9a-f]{32}', batch.get('batch_id', '')):
        raise ValueError('Expected a frozen protocol 2 batch; run memory freeze on author drafts')

    paths = [source['path'] for source in batch['sources'] if 'path' in source]
    source_ids = [_record(source['id'], 'source') for source in batch['sources'] if 'id' in source]
    if len(paths) != len(set(paths)) or len(source_ids) != len(set(source_ids)):
        raise ValueError('Duplicate source path or identity')

    def member(value):
        record = _record(value)
        if record.table == 'member' and (not isinstance(record.key, str) or
                                         not re.fullmatch(r'[0-9a-f]{32}', record.key)):
            raise ValueError(f'Member reference must be a UUID: {value}')
        return record

    expected = {}
    for key, revision in batch['expected'].items():
        identity = member(key)
        if identity in expected:
            raise ValueError(f'Duplicate expected identity: {key}')
        expected[identity] = revision
    new = [member(value) for value in batch['new_members']]
    if len(new) != len(set(new)) or any(value.table != 'member' for value in new):
        raise ValueError('Invalid or duplicate new member identity')
    mapping = batch['member_mapping']
    positions = [(entry['draft'], entry['member']) for entry in mapping]
    if (len(set(positions)) != len(positions) or
            [member(entry['id']) for entry in mapping] != new):
        raise ValueError('Invalid frozen member mapping')
    writes = [member(item['id']) for item in batch.get('members', [])]
    if any(value.table != 'member' for value in writes) or len(writes) != len(set(writes)):
        raise ValueError('Duplicate or invalid member update')
    if not set(new) <= set(writes):
        raise ValueError('New member mapping does not match batch members')
    if set(new) & set(expected):
        raise ValueError('New members cannot have expected revisions')
    if any(value not in expected and value not in new for value in writes):
        raise ValueError('Existing member updates require prepare UUID and expected revision')
    for table, field, deleted in (('member', 'members', 'delete_members'),
                                   ('node', 'nodes', 'delete_nodes'),
                                   ('semantic', 'edges', 'delete_edges')):
        written = [_record(item['id'], table) for item in batch.get(field, [])]
        removed = [_record(value, table) for value in batch.get(deleted, [])]
        if (any(value.table != table for value in written + removed) or
                len(written + removed) != len(set(written + removed))):
            raise ValueError(f'Duplicate or conflicting {table} update')
        for value in removed:
            if value.table == 'member':
                member(value.table + ':' + str(value.key))
    for field in ('members', 'nodes', 'edges'):
        for item in batch.get(field, []):
            for value in item.get('evidence', []):
                if member(value).table != 'member':
                    raise ValueError('Evidence must reference a member')
            if field == 'members' and item.get('parent'):
                member(item['parent'])
            if field == 'edges':
                for endpoint in ('in', 'out'):
                    member(item[endpoint])
                    if endpoint in item.get('endpoint_versions', {}):
                        member(item['endpoint_versions'][endpoint]['id'])
    corrections = [member(item['target']) for item in batch.get('corrections', [])]
    if len(corrections) != len(set(corrections)):
        raise ValueError('Duplicate correction target')
    for source in batch['sources']:
        for decision in source.get('dispositions', []):
            for ref in decision.get('representations', []):
                member(ref['id'])
        for decision in source.get('deferred_refinement', []):
            for ref in decision.get('gaps', []):
                member(ref['member'])

"""Freeze scoped author drafts into one immutable publication batch."""

from copy import deepcopy
import json
from pathlib import Path
from uuid import uuid4


def freeze(drafts, *, config=None):
    if not drafts:
        raise ValueError('At least one draft is required')
    from .store import _record
    from .privacy import privacy_rules, rules_revision, source_private

    rules = privacy_rules(config)
    merged = {'protocol': 2, 'batch_id': uuid4().hex, 'new_members': [], 'member_mapping': [],
              'sources': [], 'expected': {}, 'members': [],
              'privacy_rules': rules, 'privacy_rules_revision': rules_revision(rules)}
    drafts = deepcopy(drafts)
    scopes = []
    node_scopes = []
    for scope, draft in enumerate(drafts):
        if any(key in draft for key in ('protocol', 'batch_id', 'new_members', 'member_mapping')):
            raise ValueError('Expected an author draft, not a frozen batch')
        allowed = {'sources', 'expected', 'members', 'nodes', 'edges', 'delete_members',
                   'delete_nodes', 'delete_edges', 'corrections', 'context'}
        unknown = draft.keys() - allowed
        if unknown:
            raise ValueError(f'Unknown draft fields: {sorted(unknown)}')
        for field, required in (('nodes', ()), ('edges', ('in', 'out'))):
            for index, item in enumerate(draft.get(field, [])):
                missing = [key for key in required if key not in item]
                if missing:
                    raise ValueError(f"drafts[{scope}].{field}[{index}] missing required fields: "
                                     f"{', '.join(missing)}")
        ids = []
        for index, item in enumerate(draft.get('members', [])):
            if item.get('kind') in {'file', 'section', 'chunk'}:
                missing = [field for field in ('start_line', 'end_line') if field not in item]
                if missing:
                    raise ValueError(f"drafts[{scope}].members[{index}] ({item.get('id', 'new member')}) "
                                     f"missing required fields: {', '.join(missing)}")
            if 'id' in item:
                ids.append(item['id'])
            else:
                identity = 'member:' + uuid4().hex
                ids.append(identity)
                merged['new_members'].append(identity)
                merged['member_mapping'].append({'draft': scope, 'member': index, 'id': identity})
        scopes.append(ids)
        node_scopes.append([item.setdefault('id', 'node:' + uuid4().hex)
                            for item in draft.get('nodes', [])])
        for item in draft.get('edges', []):
            item.setdefault('id', 'semantic:' + uuid4().hex)

    for scope, draft in enumerate(drafts):
        members = draft.get('members', [])
        ids = scopes[scope]
        def ref(value):
            if isinstance(value, dict):
                kind = 'member' if 'member' in value else 'node'
                if set(value) not in ({kind}, {'draft', kind}) or type(value.get(kind)) is not int:
                    raise ValueError('Reference must name a draft and member or node position')
                selected = value.get('draft', scope)
                index = value[kind]
                if type(selected) is not int or selected < 0 or selected >= len(scopes):
                    raise ValueError(f'Draft index out of range: {selected}')
                group = scopes[selected] if kind == 'member' else node_scopes[selected]
                if index < 0 or index >= len(group):
                    raise ValueError(f'{kind.title()} index out of range: {index}')
                return group[index]
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
            if not source.get('deleted'):
                source['private'] = source_private(source['path'], rules['private_scope'])
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


def compile_proposals(proposals, *, config=None):
    """Compile author choices against the exact, hash-pinned reading packages.

    Prepare supplies mechanical identities and versions; it never supplies a
    semantic choice. The caller must save a new frozen file for every revision.
    """
    from hashlib import sha256
    from .store import _record
    from .privacy import privacy_rules, rules_revision

    proposals = [deepcopy(proposal) for proposal in proposals]
    packages = []
    package_refs = []
    known = {}
    identity_text = {}
    records = {}
    historical = {}
    for index, proposal in enumerate(proposals):
        reference = proposal.pop('prepare')
        path = Path(reference['path']).resolve()
        material = path.read_bytes()
        digest = sha256(material).hexdigest()
        if digest != reference['file_sha256'].lower():
            raise ValueError(f'proposals[{index}].prepare SHA256 mismatch for {path}')
        package_refs.append({'path': str(path), 'file_sha256': digest})
        prepared = json.loads(material.decode('utf-8'))
        rules = privacy_rules(config)
        if prepared['privacy_rules'] != rules or prepared['privacy_rules_revision'] != rules_revision(rules):
            raise ValueError(f'proposals[{index}].prepare privacy rules changed: {path}')
        if 'expected' in proposal:
            raise ValueError(f'proposals[{index}].expected is generated from prepare')
        for identity, revision in prepared['expected'].items():
            record = _record(identity)
            if record in known and known[record] != revision:
                raise ValueError(f'Conflicting prepare revisions for {identity}')
            known[record] = revision
            identity_text[record] = identity
        for source in prepared['sources']:
            for row in source.get('members', []):
                records[_record(row['id'])] = row
        for field in ('members', 'nodes', 'edges'):
            for row in prepared['neighborhood'][field]:
                records[_record(row['id'])] = row
        for row in prepared.get('historical_versions', []):
            key = (_record(row['id']), row['knowledge_revision'])
            if key in historical and historical[key] != row:
                raise ValueError(f'Conflicting historical prepare version: {row["id"]}@{row["knowledge_revision"]}')
            historical[key] = row
        packages.append(prepared)

    for index, (proposal, prepared) in enumerate(zip(proposals, packages)):
        sources = {source['path']: source for source in prepared['sources']}
        selected = []
        for position, decision in enumerate(proposal.get('sources', [])):
            if isinstance(decision, str):
                decision = {'path': decision}
            extra = decision.keys() - {'path', 'dispositions', 'deferred_refinement'}
            if extra:
                raise ValueError(f'proposals[{index}].sources[{position}] has generated fields: {sorted(extra)}')
            path = decision['path']
            if path not in sources:
                raise ValueError(f'proposals[{index}].sources[{position}] not in prepare: {path}')
            source = sources[path]
            compiled = {'path': path}
            if source.get('deleted'):
                compiled.update({'deleted': True, 'revision': source['previous']['revision']})
            else:
                compiled['revision'] = source['revision']
                if source['kind'] == 'image':
                    compiled['kind'] = 'image'
            if 'id' in source:
                compiled['id'] = source['id']
            for field in ('dispositions', 'deferred_refinement'):
                if field in decision:
                    compiled[field] = decision[field]
            for decision_item in compiled.get('dispositions', []):
                for ref in decision_item.get('representations', []):
                    ref['knowledge_revision'] = known[_record(ref['id'])]
            for decision_item in compiled.get('deferred_refinement', []):
                for ref in decision_item.get('gaps', []):
                    ref['knowledge_revision'] = known[_record(ref['member'])]
            selected.append(compiled)
        proposal['sources'] = selected
        # IDs supplied for writes or retirements must be observed in prepare.
        for table, field in (('member', 'members'), ('node', 'nodes'), ('semantic', 'edges')):
            for position, item in enumerate(proposal.get(field, [])):
                if 'id' in item and _record(item['id'], table) not in known:
                    raise ValueError(f'proposals[{index}].{field}[{position}].id not in prepare: {item["id"]}')
        for table, field in (('member', 'delete_members'), ('node', 'delete_nodes'), ('semantic', 'delete_edges')):
            for position, identity in enumerate(proposal.get(field, [])):
                if _record(identity, table) not in known:
                    raise ValueError(f'proposals[{index}].{field}[{position}] not in prepare: {identity}')
        for position, item in enumerate(proposal.get('corrections', [])):
            if _record(item['target']) not in known:
                raise ValueError(f'proposals[{index}].corrections[{position}].target not in prepare: {item["target"]}')
        proposal['expected'] = {identity_text[record]: revision for record, revision in known.items()}

    batch = freeze(proposals, config=config)
    batch['prepare_packages'] = package_refs
    # Apply checks precisely the writes and dependencies it uses. Keep only that
    # closure and reject unknown external references before the frozen file exists.
    new = {_record(identity) for identity in batch['new_members']}
    for table, field in (('node', 'nodes'), ('semantic', 'edges')):
        for item in batch.get(field, []):
            record = _record(item['id'], table)
            if record not in known:
                new.add(record)
    needed = set()
    for table, field, removed in (('member', 'members', 'delete_members'),
                                   ('node', 'nodes', 'delete_nodes'),
                                   ('semantic', 'edges', 'delete_edges')):
        needed.update(_record(item['id'], table) for item in batch.get(field, []))
        needed.update(_record(item, table) for item in batch.get(removed, []))
    needed.update(_record(item['target']) for item in batch.get('corrections', []))
    targets = set(needed)
    walk_roots = set()
    walk_pins = []
    for field in ('members', 'nodes', 'edges'):
        for item in batch.get(field, []):
            evidence_ids = {_record(value) for value in item.get('evidence', [])}
            needed.update(evidence_ids)
            walk_roots.update(evidence_ids)
            if field == 'members' and item.get('parent'):
                parent = _record(item['parent'])
                needed.add(parent)
                walk_roots.add(parent)
            if field == 'edges':
                for endpoint in ('in', 'out'):
                    target = _record(item[endpoint])
                    needed.add(target)
                    pin = item.get('endpoint_versions', {}).get(endpoint)
                    if pin:
                        if _record(pin['id']) != target:
                            raise ValueError(f"Historical endpoint identity mismatch: {item['id']} {endpoint}")
                        walk_pins.append((target, pin['knowledge_revision']))
                    else:
                        walk_roots.add(target)
    for source in batch['sources']:
        for item in source.get('dispositions', []):
            ids = {_record(ref['id']) for ref in item.get('representations', [])}
            needed.update(ids)
            walk_roots.update(ids)
        for item in source.get('deferred_refinement', []):
            ids = {_record(ref['member']) for ref in item.get('gaps', [])}
            needed.update(ids)
            walk_roots.update(ids)
    evidence = {_record(value) for field in ('members', 'nodes', 'edges')
                for item in batch.get(field, []) for value in item.get('evidence', [])}
    retired = {_record(value, table) for table, field in (('member', 'delete_members'),
               ('node', 'delete_nodes'), ('semantic', 'delete_edges')) for value in batch.get(field, [])}
    rewritten = {_record(item['id']) for item in batch.get('members', [])}
    for record in evidence - new - rewritten:
        if record not in known:
            raise ValueError(f'References absent from prepare: {record}')
        row = records.get(record)
        if record in retired or row is None or row.get('retired') or row.get('stale'):
            raise ValueError(f'Evidence is unavailable, stale or retired in prepare: {identity_text.get(record, record)}')
    # Follow each accepted edge at its pinned version, while separately
    # guarding the current head of every logical identity against races.
    pending = [(record, known[record]) for record in walk_roots - new - targets if record in known]
    pending.extend(walk_pins)
    walked = set()
    while pending:
        record, revision = pending.pop()
        key = (record, revision)
        if key in walked:
            continue
        walked.add(key)
        row = records.get(record) if known.get(record) == revision else historical.get(key)
        if row is None or row.get('knowledge_revision') != revision:
            raise ValueError(f'Pinned knowledge version absent from prepare: {identity_text.get(record, record)}@{revision}')
        ancestors = [(entry['member'], entry['knowledge_revision']) for entry in row.get('basis', [])]
        if row.get('parent_version'):
            parent = row['parent_version']
            ancestors.append((parent['id'], parent['knowledge_revision']))
        ancestors.extend((endpoint['id'], endpoint['knowledge_revision'])
                         for endpoint in row.get('endpoint_versions', {}).values())
        for identity, pinned_revision in ancestors:
            dependency = _record(identity)
            if dependency not in known:
                raise ValueError(f'Basis absent from prepare for {identity_text.get(record, record)}: {identity}')
            needed.add(dependency)
            pending.append((dependency, pinned_revision))
    batch['dependency_closure'] = [identity_text[record] for record in sorted(
        needed & set(known), key=lambda record: (record.table, str(record.key)))]
    missing = needed - set(known) - new
    if missing:
        raise ValueError('References absent from prepare: ' + ', '.join(sorted(f'{r.table}:{r.key}' for r in missing)))
    batch['expected'] = {identity_text[record]: known[record] for record in needed if record in known}

    # Freeze classification for exactly the author's writes, using only the
    # selected sources and version-pinned records in the reading packages.
    sources = {source['path']: source for source in batch['sources']}
    writes = {_record(item['id'], table): (item['id'], item)
              for table, field in (('member', 'members'), ('node', 'nodes'), ('semantic', 'edges'))
              for item in batch.get(field, [])}
    private = {}
    resolving = set()

    def classification(record):
        if record in private:
            return private[record]
        if record in resolving:
            raise ValueError(f'Private classification has cyclic evidence: {record}')
        if record not in writes:
            row = records.get(record)
            if row is None or type(row.get('private')) is not bool:
                raise ValueError(f'Private classification missing from prepare: {identity_text.get(record, record)}')
            return row['private']
        resolving.add(record)
        _, item = writes[record]
        markers = [classification(_record(ref)) for ref in item.get('evidence', [])]
        if record.table == 'member':
            source = sources.get(item['path'])
            if source is None or type(source.get('private')) is not bool:
                raise ValueError(f"Member source absent or deleted in proposal: {item['path']}")
            markers.append(source['private'])
        elif record.table == 'semantic':
            for endpoint in ('in', 'out'):
                target = _record(item[endpoint])
                pin = item.get('endpoint_versions', {}).get(endpoint)
                if pin:
                    if _record(pin['id']) != target:
                        raise ValueError(f"Historical endpoint identity mismatch: {item['id']} {endpoint}")
                    revision = pin['knowledge_revision']
                    row = historical.get((target, revision))
                    if row is None and known.get(target) == revision:
                        row = records.get(target)
                    if row is None or type(row.get('private')) is not bool:
                        raise ValueError(f"Historical endpoint private classification absent from prepare: {item['id']} {endpoint}")
                    markers.append(row['private'])
                else:
                    markers.append(classification(target))
        resolving.remove(record)
        private[record] = any(markers)
        return private[record]

    batch['compiled_private'] = {identity_text.get(record, identity): classification(record)
                                 for record, (identity, _) in writes.items()}
    return batch


def freeze_file(drafts, output, *, config=None):
    """Validate and exclusively save one frozen batch before it can be applied."""
    batch = compile_proposals(drafts, config=config)
    validate_batch(batch)
    path = Path(output).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(batch, stream, ensure_ascii=False, indent=2)
    return batch


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

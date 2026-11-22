"""Freeze scoped author drafts into one immutable publication batch."""

from copy import deepcopy
import json
from pathlib import Path
from uuid import uuid4

from .relation_contract import EXACT_ENDPOINT_TABLES, LOGICAL_ENDPOINT_TABLES, validate_edge
from .reviewed import SOURCE_DECISION_FIELDS, disposition_representations


def _reference_position(value, location, *, edge_allowed=False):
    if isinstance(value, str):
        return None
    if isinstance(value, dict):
        for kind in ('member', 'node', 'edge') if edge_allowed else ('member', 'node'):
            if set(value) in ({kind}, {'draft', kind}) and type(value.get(kind)) is int:
                if 'draft' in value and type(value['draft']) is not int:
                    raise ValueError(f'{location}: Draft index must be an integer')
                return value.get('draft'), kind, value[kind]
    kinds = 'member, node, or edge' if edge_allowed else 'member or node'
    raise ValueError(f'{location}: Use an existing record ID as a string, '
                     f'or an object with an integer {kinds} position and optional draft index')


def _reference_slots(draft, prefix, *, writable=False):
    for field in ('members', 'nodes', 'edges'):
        for index, item in enumerate(draft.get(field, [])):
            location = f'{prefix}{field}[{index}]'
            if field == 'members' and item.get('parent') is not None:
                yield item, 'parent', f'{location}.parent', False
            evidence = item.get('evidence', ())
            if writable:
                evidence = item['evidence'] = list(evidence)
            elif 'evidence' in item and not isinstance(evidence, list):
                raise ValueError(f'{location}.evidence: Expected an array of references')
            for position in range(len(evidence)):
                yield evidence, position, f'{location}.evidence[{position}]', False
            if field == 'edges':
                for endpoint in ('in', 'out'):
                    if endpoint in item:
                        yield item, endpoint, f'{location}.{endpoint}', True
                for position, basis in enumerate(item.get('basis', [])):
                    if 'id' in basis:
                        yield basis, 'id', f'{location}.basis[{position}].id', False


def validate_reference_shapes(draft, *, label, separator=': '):
    """Check reference syntax before the wave's other drafts are available."""
    prefix = f'{label}{separator}'
    for index, item in enumerate(draft.get('edges', [])):
        validate_edge(item, location=f'{prefix}edges[{index}]')
    for target, key, location, edge_allowed in _reference_slots(draft, prefix):
        _reference_position(target[key], location, edge_allowed=edge_allowed)


def validate_source_decisions(proposal, *, prefix):
    """Check authored source decisions without resolving any prepared evidence."""
    for position, source in enumerate(proposal.get('sources', [])):
        if isinstance(source, str):
            continue
        location = f'{prefix}sources[{position}]'
        extra = source.keys() - {'path', *SOURCE_DECISION_FIELDS}
        if extra:
            raise ValueError(f'{location} has generated fields: {sorted(extra)}')
        dispositions = source.get('dispositions', [])
        if not isinstance(dispositions, list):
            raise ValueError(f'{location}.dispositions: Expected an array')
        for index, entry in enumerate(dispositions):
            field = f'{location}.dispositions[{index}]'
            if not isinstance(entry, dict):
                raise ValueError(f'{field}: Expected an object')
            disposition_representations(entry, location=field)


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
    for scope, draft in enumerate(drafts):
        if any(key in draft for key in ('protocol', 'batch_id', 'new_members', 'member_mapping')):
            raise ValueError('Expected an author draft, not a frozen batch')
        allowed = {'sources', 'expected', 'members', 'nodes', 'edges', 'delete_members',
                   'delete_nodes', 'delete_edges', 'corrections', 'context'}
        unknown = draft.keys() - allowed
        if unknown:
            raise ValueError(f'Unknown draft fields: {sorted(unknown)}')
        validate_reference_shapes(draft, label=f'drafts[{scope}]', separator='.')
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
        scopes.append({
            'member': ids,
            'node': [item.setdefault('id', 'node:' + uuid4().hex) for item in draft.get('nodes', [])],
            'edge': [item.setdefault('id', 'semantic:' + uuid4().hex) for item in draft.get('edges', [])],
        })

    for scope, draft in enumerate(drafts):
        members = draft.get('members', [])
        for item, identity in zip(members, scopes[scope]['member']):
            item['id'] = identity
        for target, key, location, edge_allowed in _reference_slots(draft, f'drafts[{scope}].', writable=True):
            reference = _reference_position(target[key], location, edge_allowed=edge_allowed)
            if reference is None:
                continue
            selected, kind, index = reference
            if selected is None:
                selected = scope
            if selected < 0 or selected >= len(scopes):
                raise ValueError(f'{location}: Draft index out of range: {selected}')
            group = scopes[selected][kind]
            if index < 0 or index >= len(group):
                raise ValueError(f'{location}: {kind.title()} index out of range: {index}')
            target[key] = group[index]
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

    Prepare supplies identities and versions. The author chooses what to publish.
    Save a new frozen file for every revision.
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
    exact = {}

    def available(row):
        return not (row.get('stale', False) or row.get('retired', False))

    def observe_exact(identity, row):
        record = _record(identity)
        if record in exact and exact[record]['private'] != row['private']:
            raise ValueError(f'Conflicting prepare private markers for {identity}')
        exact[record] = {**exact.get(record, {}), **row}

    def observe_knowledge(row):
        if row.get('exact_id'):
            observe_exact(row['exact_id'], row)

    def observe_current(row):
        record = _record(row['id'])
        if record in records and available(records[record]) != available(row):
            raise ValueError(f"Conflicting prepare availability for {row['id']}")
        records[record] = row
        observe_knowledge(row)

    for index, proposal in enumerate(proposals):
        validate_source_decisions(proposal, prefix=f'proposals[{index}].')
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
                observe_current(row)
            previous = source.get('previous')
            if previous and previous.get('source_version'):
                observe_exact(previous['source_version'], {'path': source['path'], 'kind': 'text', **previous})
        for snapshot in prepared.get('snapshots', []):
            observe_exact(snapshot['id'], snapshot)
        for field in ('members', 'nodes', 'edges'):
            for row in prepared['neighborhood'][field]:
                observe_current(row)
        for row in prepared.get('historical_versions', []):
            key = (_record(row['id']), row['knowledge_revision'])
            if key in historical and historical[key] != row:
                raise ValueError(f'Conflicting historical prepare version: {row["id"]}@{row["knowledge_revision"]}')
            historical[key] = row
            observe_knowledge(row)
        packages.append(prepared)

    for index, (proposal, prepared) in enumerate(zip(proposals, packages)):
        sources = {source['path']: source for source in prepared['sources']}
        selected = []
        for position, decision in enumerate(proposal.get('sources', [])):
            if isinstance(decision, str):
                decision = {'path': decision}
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
            for field in SOURCE_DECISION_FIELDS:
                if field in decision:
                    compiled[field] = decision[field]
            for decision_item in compiled.get('dispositions', []):
                for ref in decision_item.get('representations', []):
                    ref['knowledge_revision'] = known[_record(ref['id'])]
            for decision_item in compiled.get('deferred_refinement', []):
                for ref in decision_item.get('gaps', []):
                    ref['knowledge_revision'] = known[_record(ref['member'])]
            if 'unavailable_gaps' in compiled:
                if not isinstance(compiled['unavailable_gaps'], list):
                    raise ValueError('unavailable_gaps must be a list')
                for ref in compiled['unavailable_gaps']:
                    record = _record(ref['member'])
                    row = records.get(record)
                    if (record.table != 'member' or row is None or row.get('stale') is not False
                            or row.get('retired') is not False
                            or known.get(record) != ref['knowledge_revision']
                            or row.get('knowledge_revision') != ref['knowledge_revision']
                            or row.get('path') != path or row.get('source_revision') != source.get('revision')
                            or ref['gap'] not in row.get('coverage_gaps', [])):
                        raise ValueError('Unavailable gap must match a current prepared member and its coverage gap')
                    if row.get('private') is not False and source.get('private') is not True:
                        raise ValueError('Unavailable gap cannot expose a private member in a public source')
                    if not isinstance(ref.get('reason'), str) or not ref['reason'].strip():
                        raise ValueError('Unavailable gap requires a reason')
            selected.append(compiled)
        proposal['sources'] = selected
        for position, edge in enumerate(proposal.get('edges', [])):
            validate_edge(edge, location=f'proposals[{index}].edges[{position}]')
            for reference in edge.get('basis', []):
                if 'path' in reference and reference['path'] not in sources:
                    raise ValueError(f"Snapshot basis path absent from prepare: {reference['path']}")
        # IDs supplied for writes or retirements must be observed in prepare.
        for table, field in (('member', 'members'), ('node', 'nodes'), ('semantic', 'edges')):
            for position, item in enumerate(proposal.get(field, [])):
                if 'id' in item and _record(item['id'], table) not in known:
                    raise ValueError(f'proposals[{index}].{field}[{position}].id not in prepare: {item["id"]}. '
                                     'Omit id for a new record so the compiler assigns one. '
                                     'For an update, use the ID from a fixed prepare package.')
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
    # Explicit chunk text is a literal original, not an author summary. Check
    # the same exact range/locator used by apply against the pinned prepare.
    from .content import SourceContent, original_text
    selected_sources = {source['path']: source for source in batch['sources'] if not source.get('deleted')}
    prepared_sources = {(source['path'], source['revision']): source
                        for package in packages for source in package['sources'] if not source.get('deleted')}
    originals = {}

    def prepared_original(source):
        path, revision = source['path'], source['revision']
        key = path, revision
        if key not in originals:
            lines = []
            for number, line in enumerate(source['numbered_text'].splitlines(keepends=True), 1):
                prefix = f'{number}: '
                if not line.startswith(prefix):
                    raise ValueError(f'Invalid numbered original in prepare: {path}')
                lines.append(line[len(prefix):])
            raw = ''.join(lines)
            if sha256(raw.encode('utf-8')).hexdigest() != revision:
                raise ValueError(f'Prepared original revision mismatch: {path}')
            originals[key] = SourceContent(path, revision, len(raw.encode('utf-8')), 0, raw)
        return originals[key]

    for item in batch.get('members', []):
        if item.get('kind') != 'chunk' or 'text' not in item:
            continue
        path = item['path']
        selected = selected_sources[path]
        source = prepared_sources[path, selected['revision']]
        if source['kind'] != 'text':
            raise ValueError(f'Chunk requires a text source: {path}')
        raw = original_text(prepared_original(source), item['start_line'], item['end_line'], item.get('locator'))
        if item['text'] != raw:
            raise ValueError(f"Chunk {item['id']} text differs from its original range: {path}")

    def check_snapshot_location(source, reference):
        start, end = reference.get('start_line'), reference.get('end_line')
        if source['kind'] == 'image':
            if start is not None or end is not None:
                raise ValueError(f"Image basis uses a locator without lines: {source['path']}")
        elif start is None or end is None:
            raise ValueError(f"Text basis requires start_line and end_line: {source['path']}")
        elif 'numbered_text' in source:
            original_text(prepared_original(source), start, end, reference.get('locator'))

    def require_exact(record):
        row = exact.get(record)
        if row is None:
            raise ValueError(f'References absent from prepare: {record.table}:{record.key}')
        return row

    # Apply checks precisely the writes and dependencies it uses. Keep only that
    # closure and reject unknown external references before the frozen file exists.
    writes = {_record(item['id'], table): (item['id'], item)
              for table, field in (('member', 'members'), ('node', 'nodes'), ('semantic', 'edges'))
              for item in batch.get(field, [])}
    new = set(writes) - set(known)
    retired = {_record(value, table) for table, field in (('member', 'delete_members'),
               ('node', 'delete_nodes'), ('semantic', 'delete_edges')) for value in batch.get(field, [])}
    needed = set(writes) | retired
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
                    pin = item.get('endpoint_versions', {}).get(endpoint)
                    if target.table in EXACT_ENDPOINT_TABLES:
                        if pin:
                            raise ValueError(f"Exact endpoint already pins the version: {item['id']} {endpoint}")
                        require_exact(target)
                        continue
                    if target.table not in LOGICAL_ENDPOINT_TABLES:
                        raise ValueError(f"Unsupported edge endpoint: {item[endpoint]}")
                    needed.add(target)
                    if not pin and target not in writes and target in known:
                        row = records.get(target)
                        if target in retired or row is None or not available(row):
                            raise ValueError(f"Choose an exact version for an unavailable endpoint: {item[endpoint]}")
                        pin = {'id': item[endpoint], 'knowledge_revision': known[target]}
                        item.setdefault('endpoint_versions', {})[endpoint] = pin
                    if pin:
                        if _record(pin['id']) != target:
                            raise ValueError(f"Historical endpoint identity mismatch: {item['id']} {endpoint}")
                        if target not in known:
                            raise ValueError(f"Explicit endpoint pin is absent from prepare: {item[endpoint]}")
                        walk_pins.append((target, pin['knowledge_revision']))
                    else:
                        walk_roots.add(target)
                for reference in item.get('basis', []):
                    if 'path' in reference:
                        path = reference['path']
                        if path not in selected_sources:
                            raise ValueError(f'Snapshot basis path must be selected for publication: {path}')
                        source = prepared_sources[path, selected_sources[path]['revision']]
                        check_snapshot_location(source, reference)
                    elif 'source_version' in reference:
                        snapshot = _record(reference['source_version'])
                        if snapshot.table != 'source_version':
                            raise ValueError('Snapshot basis requires a source_version ID')
                        check_snapshot_location(require_exact(snapshot), reference)
                    else:
                        target = _record(reference['id'])
                        revision = reference.get('knowledge_revision')
                        if target.table == 'knowledge_version' and revision is None:
                            require_exact(target)
                        elif target.table not in {'member', 'node'}:
                            raise ValueError(f"Basis needs a knowledge version: {reference['id']}")
                        elif revision is not None:
                            if target not in known:
                                raise ValueError(f"Basis absent from prepare: {reference['id']}")
                            needed.add(target)
                            walk_pins.append((target, revision))
                        elif target not in writes:
                            raise ValueError(f"Existing basis requires an exact knowledge version: {reference['id']}")
    for source in batch['sources']:
        for item in source.get('dispositions', []):
            ids = {_record(ref['id']) for ref in item.get('representations', [])}
            needed.update(ids)
            walk_roots.update(ids)
        for item in source.get('deferred_refinement', []):
            ids = {_record(ref['member']) for ref in item.get('gaps', [])}
            needed.update(ids)
            walk_roots.update(ids)
        ids = {_record(ref['member']) for ref in source.get('unavailable_gaps', [])}
        needed.update(ids)
        walk_roots.update(ids)
    evidence = {_record(value) for field in ('members', 'nodes', 'edges')
                for item in batch.get(field, []) for value in item.get('evidence', [])}
    rewritten = {_record(item['id']) for item in batch.get('members', [])}
    for record in evidence - new - rewritten:
        if record not in known:
            raise ValueError(f'References absent from prepare: {record}')
        row = records.get(record)
        if record in retired or row is None or not available(row):
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
        row = historical.get(key)
        if row is None and known.get(record) == revision:
            row = records.get(record)
        if row is None or row.get('knowledge_revision') != revision:
            raise ValueError(f'Pinned knowledge version absent from prepare: {identity_text.get(record, record)}@{revision}')
        ancestors = [(entry['member'], entry['knowledge_revision']) for entry in row.get('basis', [])
                     if 'member' in entry]
        ancestors.extend((entry['id'], entry['knowledge_revision']) for entry in row.get('direct_basis', [])
                         if 'id' in entry and 'knowledge_revision' in entry)
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
    batch['expected_status'] = {
        identity_text[record]: available(row)
        for record, row in records.items() if identity_text.get(record) in batch['expected']
    }

    # Freeze classification for exactly the author's writes, using only the
    # selected sources and version-pinned records in the reading packages.
    sources = {source['path']: source for source in batch['sources']}
    private = {}
    resolving = set()

    def exact_classification(identity, revision=None):
        if revision is None:
            row = require_exact(identity)
        else:
            row = historical.get((identity, revision))
            if row is None and known.get(identity) == revision:
                row = records.get(identity)
        if row is None or type(row.get('private')) is not bool:
            raise ValueError(f"Exact private classification absent from prepare: {identity}@{revision}")
        return row['private']

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
                if pin or target.table in EXACT_ENDPOINT_TABLES:
                    markers.append(exact_classification(target, pin['knowledge_revision'] if pin else None))
                else:
                    markers.append(classification(target))
            for reference in item.get('basis', []):
                if 'path' in reference:
                    markers.append(selected_sources[reference['path']]['private'])
                elif 'source_version' in reference:
                    markers.append(exact_classification(_record(reference['source_version'])))
                else:
                    target = _record(reference['id'])
                    revision = reference.get('knowledge_revision')
                    if revision or target.table == 'knowledge_version':
                        markers.append(exact_classification(target, revision))
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
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Frozen references must use record IDs')
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
    statuses = batch.get('expected_status', {})
    if (not isinstance(statuses, dict) or statuses.keys() - batch['expected'].keys()
            or any(type(status) is not bool for status in statuses.values())):
        raise ValueError('Expected availability must match prepared identities and use booleans')
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
        for index, item in enumerate(batch.get(field, [])):
            for value in item.get('evidence', []):
                if member(value).table != 'member':
                    raise ValueError('Evidence must reference a member')
            if field == 'members' and item.get('parent'):
                member(item['parent'])
            if field == 'edges':
                validate_edge(item, location=f'edges[{index}]')
                for endpoint in ('in', 'out'):
                    target = member(item[endpoint])
                    if target.table not in EXACT_ENDPOINT_TABLES | LOGICAL_ENDPOINT_TABLES:
                        raise ValueError(f'Unsupported edge endpoint: {item[endpoint]}')
                    pin = item.get('endpoint_versions', {}).get(endpoint)
                    if pin and (target.table in EXACT_ENDPOINT_TABLES or member(pin['id']) != target):
                        raise ValueError(f'Endpoint pin must name the same logical record: {item[endpoint]}')
                for reference in item.get('basis', []):
                    if 'source_version' in reference and _record(reference['source_version']).table != 'source_version':
                        raise ValueError('Snapshot basis requires a source_version ID')
                    if 'id' in reference:
                        table = member(reference['id']).table
                        if (table not in {'member', 'node', 'knowledge_version'}
                                or (table == 'knowledge_version' and 'knowledge_revision' in reference)):
                            raise ValueError('Basis requires an exact knowledge version')
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
        if 'unavailable_gaps' in source and not isinstance(source['unavailable_gaps'], list):
            raise ValueError('unavailable_gaps must be a list')
        for ref in source.get('unavailable_gaps', []):
            member(ref['member'])

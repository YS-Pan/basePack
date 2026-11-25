"""Freeze scoped author drafts into one immutable publication batch."""

from copy import deepcopy
from hashlib import sha256
import json
from itertools import chain
from pathlib import Path
from uuid import uuid4

from .privacy import known_private, privacy_rules, rules_revision, source_private
from .relation_contract import EXACT_ENDPOINT_TABLES, LOGICAL_ENDPOINT_TABLES, validate_edge, validate_image_region
from .reviewed import SOURCE_DECISION_FIELDS, disposition_representations


_TEXT_MEMBER_KINDS = {'file', 'section', 'chunk'}


def read_author_draft(path, *, material=None):
    """Decode an external author draft, optionally from already verified bytes."""
    path = Path(path)
    if material is None:
        if path.is_dir():
            raise ValueError(f'Expected a UTF-8 JSON file, got a directory: {path}')
        material = path.read_bytes()
    try:
        draft = json.loads(material.decode('utf-8-sig'))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        error.add_note(f'Author draft: {path}')
        raise
    if not isinstance(draft, dict):
        raise ValueError(f'{path}: Expected an author draft JSON object')
    for index, member in enumerate(draft.get('members', [])):
        if not isinstance(member, dict) or 'path' not in member:
            raise ValueError(f'{path}: members[{index}].path is required')
    _validate_author_image_regions(draft, f'{path}: ')
    return draft


def read_fixed_author_draft(reference):
    from .stages import read_fixed_bytes

    return read_author_draft(reference['path'], material=read_fixed_bytes(reference))


def _validate_author_image_regions(draft, prefix):
    edges = draft.get('edges', [])
    if not isinstance(edges, (list, tuple)):
        return
    for edge_index, edge in enumerate(edges):
        if not isinstance(edge, dict) or not isinstance(edge.get('basis'), list):
            continue
        for basis_index, basis in enumerate(edge['basis']):
            if isinstance(basis, dict) and ('path' in basis or 'source_version' in basis):
                validate_image_region(basis.get('locator'),
                                      location=f'{prefix}edges[{edge_index}].basis[{basis_index}].locator.region')


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
    """Check reference syntax and positions that do not depend on other drafts."""
    prefix = f'{label}{separator}'
    for index, item in enumerate(draft.get('edges', [])):
        validate_edge(item, location=f'{prefix}edges[{index}]')
    _validate_author_image_regions(draft, prefix)
    for target, key, location, edge_allowed in _reference_slots(draft, prefix):
        position = _reference_position(target[key], location, edge_allowed=edge_allowed)
        if position is None:
            continue
        selected, kind, index = position
        if selected is not None and selected < 0:
            raise ValueError(f'{location}: Draft index out of range: {selected}')
        if index < 0 or (selected is None and index >= len(draft.get(f'{kind}s', []))):
            raise ValueError(f'{location}: {kind.title()} index out of range: {index}')


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


def _read_prepare(reference, location):
    path = Path(reference['path']).resolve()
    material = path.read_bytes()
    digest = sha256(material).hexdigest()
    if digest != reference['file_sha256'].lower():
        raise ValueError(f'{location} SHA256 mismatch for {path}')
    return json.loads(material.decode('utf-8')), {'path': str(path), 'file_sha256': digest}


def _prepare_location(reference):
    return f"{reference['path']} (SHA256 {reference['file_sha256']})"


class PrivacyUnknown(ValueError):
    """An authored reference still needs a verified exact privacy marker."""

    def __init__(self, location, identity, revision, prepare_refs, *, authored_identity):
        self.location = location
        self.identity = identity
        self.revision = revision
        self.prepare_refs = tuple(prepare_refs)
        self.authored_identity = authored_identity
        target = f'{identity}@{revision}' if revision is not None else identity
        if identity != authored_identity:
            target += f' via {authored_identity}'
        prepared = ', '.join(map(_prepare_location, self.prepare_refs))
        super().__init__(f'{location}: Unknown exact privacy classification for {target} in prepare: {prepared}')


class _PreparedPrivacy:
    def __init__(self, packages, references):
        from .store import _record

        self.exact = {}
        self.aliases = {}
        self.observations = {}
        self.evidence_sources = {}
        observed = []

        def observe_exact(identity, row):
            record = _record(identity)
            self.exact[record] = {**self.exact.get(record, {}), **row}
            return record

        for prepared, reference in zip(packages, references, strict=True):
            members = []
            for source in prepared['sources']:
                members.extend(source.get('members', []))
                previous = source.get('previous')
                if previous and previous.get('source_version'):
                    snapshot = {'path': source['path'], 'kind': 'text', **previous}
                    observed.append((observe_exact(previous['source_version'], snapshot), snapshot, reference))
            for snapshot in prepared.get('snapshots', []):
                observed.append((observe_exact(snapshot['id'], snapshot), snapshot, reference))
            knowledge = chain(members, *(prepared['neighborhood'][field] for field in ('members', 'nodes', 'edges')),
                              prepared.get('historical_versions', []))
            for row in knowledge:
                key = (_record(row['id']), row.get('knowledge_revision'))
                if row.get('source_version'):
                    snapshot = _record(row['source_version'])
                    if self.evidence_sources.setdefault(key, snapshot) != snapshot:
                        raise ValueError(f"Conflicting prepare source versions for {row['id']}@{key[1]}")
                if row.get('exact_id'):
                    exact = observe_exact(row['exact_id'], row)
                    if self.aliases.setdefault(key, exact) != exact:
                        raise ValueError(f"Conflicting exact prepare IDs for {row['id']}@{key[1]}")
                observed.append((key, row, reference))

        for key, row, reference in observed:
            key = self.aliases.get(key, key)
            refs = self.observations.setdefault(key, {}).setdefault(known_private(row), {})
            refs[reference['path'], reference['file_sha256']] = reference
        for key, markers in self.observations.items():
            if False in markers and True in markers:
                identity, revision = self._identity(key)
                target = f'{identity}@{revision}' if revision is not None else identity
                public = markers[False][min(markers[False])]
                private = markers[True][min(markers[True])]
                raise ValueError(f'Conflicting prepare private markers for {target}: '
                                 f'{_prepare_location(public)} has private=False. '
                                 f'{_prepare_location(private)} has private=True')

    def _identity(self, key):
        if key in self.exact:
            row = self.exact[key]
            return f'{key.table}:{key.key}', row.get('knowledge_revision', row.get('revision'))
        identity, revision = key
        return f'{identity.table}:{identity.key}', revision

    def marker(self, identity, revision, location, *, observed_only=False, authored_identity=None):
        from .store import _record

        record = _record(identity)
        key = record if record.table in EXACT_ENDPOINT_TABLES else (record, revision)
        key = self.aliases.get(key, key)
        markers = self.observations.get(key)
        if markers is None:
            if observed_only:
                return None
            target = f'{record.table}:{record.key}'
            raise ValueError(f'{location}: Exact private classification absent from prepare: {target}@{revision}')
        for marker in (True, False):
            if marker in markers:
                return marker
        exact_id, exact_revision = self._identity(key)
        refs = markers[None]
        raise PrivacyUnknown(location, exact_id, exact_revision, (refs[key] for key in sorted(refs)),
                             authored_identity=authored_identity or identity)


def _privacy_dependencies(field, item, location):
    for index, identity in enumerate(item.get('evidence', [])):
        yield identity, None, f'{location}.evidence[{index}]'
    if field == 'edges':
        for endpoint in ('in', 'out'):
            pin = item.get('endpoint_versions', {}).get(endpoint)
            yield item[endpoint], pin['knowledge_revision'] if pin else None, f'{location}.{endpoint}'
        for index, basis in enumerate(item.get('basis', [])):
            if 'source_version' in basis:
                yield basis['source_version'], None, f'{location}.basis[{index}].source_version'
            elif 'id' in basis:
                yield basis['id'], basis.get('knowledge_revision'), f'{location}.basis[{index}].id'


def proposal_privacy_unknown(proposal, *, label='proposals[0]') -> list[PrivacyUnknown]:
    """Report direct unknown references that other prepares or writes may resolve."""
    from .store import _record

    if 'prepare' not in proposal:
        return []
    rewritten = {_record(item['id'], table)
                 for table, field in (('member', 'members'), ('node', 'nodes'), ('semantic', 'edges'))
                 for item in proposal.get(field, []) if 'id' in item}
    dependencies = []
    for field in ('members', 'nodes', 'edges'):
        for index, item in enumerate(proposal.get(field, [])):
            location = f'{label}.{field}[{index}]'
            dependencies.extend((*dependency, field != 'edges')
                                for dependency in _privacy_dependencies(field, item, location))
            if field == 'members' and item.get('parent'):
                dependencies.append((item['parent'], None, f'{location}.parent', False))
    for index, source in enumerate(proposal.get('sources', [])):
        if isinstance(source, dict):
            for position, ref in enumerate(source.get('unavailable_gaps', [])):
                location = f'{label}.sources[{index}].unavailable_gaps[{position}].member'
                dependencies.append((ref['member'], ref['knowledge_revision'], location, False))
    local = [(identity, revision, location, needs_source) for identity, revision, location, needs_source in dependencies
             if isinstance(identity, str) and (revision is not None or _record(identity) not in rewritten)]
    if not local:
        return []

    prepared, reference = _read_prepare(proposal['prepare'], f'{label}.prepare')
    privacy = _PreparedPrivacy([prepared], [reference])
    revisions = {_record(identity): revision for identity, revision in prepared['expected'].items()}
    unknown = []

    def check(identity, revision, location, *, authored_identity=None):
        try:
            privacy.marker(identity, revision, location, observed_only=True, authored_identity=authored_identity)
        except PrivacyUnknown as error:
            unknown.append(error)

    for identity, revision, location, needs_source in local:
        record = _record(identity)
        revision = revision if revision is not None else revisions.get(record)
        check(identity, revision, location)
        if needs_source and (snapshot := privacy.evidence_sources.get((record, revision))) is not None:
            check(snapshot, None, location, authored_identity=identity)
    return unknown


def _prepared_original(source, originals):
    from .content import SourceContent

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
        data = raw.encode('utf-8')
        if sha256(data).hexdigest() != revision:
            raise ValueError(f'Prepared original revision mismatch: {path}')
        originals[key] = SourceContent(path, revision, len(data), 0, raw)
    return originals[key]


def _validate_member_range_fields(member, location):
    missing = [field for field in ('start_line', 'end_line') if field not in member]
    if missing:
        raise ValueError(f"{location} ({member.get('id', 'new member')}) "
                         f"missing required fields: {', '.join(missing)}")


def _validate_prepared_member_location(member, source, originals, location):
    from .content import original_text

    literal = member['kind'] == 'chunk' and 'text' in member
    path, revision = source['path'], source['revision']
    if source['kind'] != 'text':
        raise ValueError(f'{location}: Image source requires an image member: {path}@{revision}')
    if 'numbered_text' not in source and not literal:
        return
    try:
        raw = original_text(_prepared_original(source, originals), member['start_line'], member['end_line'],
                            member.get('locator'))
    except ValueError as error:
        raise ValueError(f'{location} ({path}@{revision}): {error}') from error
    if literal and member['text'] != raw:
        raise ValueError(f'{location}: Chunk text differs from its original range: {path}@{revision}')


def validate_prepared_member_locations(draft, *, label):
    """Check original locations for sources selected in this draft."""
    selected = {item if isinstance(item, str) else item['path'] for item in draft['sources']}
    local_members = []
    for index, member in enumerate(draft.get('members', [])):
        if member.get('kind') in _TEXT_MEMBER_KINDS:
            location = f'{label}: members[{index}]'
            _validate_member_range_fields(member, location)
            if member['path'] in selected:
                local_members.append((member, location))
    if not local_members or 'prepare' not in draft:
        return
    prepared, _ = _read_prepare(draft['prepare'], f'{label}: prepare')
    sources = {source['path']: source for source in prepared['sources']}
    originals = {}
    for member, location in local_members:
        path = member['path']
        if path not in sources:
            raise ValueError(f'{location}.path not in prepare: {path}')
        if not sources[path].get('deleted'):
            _validate_prepared_member_location(member, sources[path], originals, location)


def freeze(drafts, *, config=None):
    if not drafts:
        raise ValueError('At least one draft is required')
    from .store import _record

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
            if item.get('kind') in _TEXT_MEMBER_KINDS:
                _validate_member_range_fields(item, f'drafts[{scope}].members[{index}]')
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
    from .store import _record

    proposals = [deepcopy(proposal) for proposal in proposals]
    packages = []
    package_refs = []
    known = {}
    identity_text = {}
    records = {}
    historical = {}

    def available(row):
        return not (row.get('stale', False) or row.get('retired', False))

    def observe_current(row):
        record = _record(row['id'])
        if record in records and available(records[record]) != available(row):
            raise ValueError(f"Conflicting prepare availability for {row['id']}")
        records[record] = row

    def historical_facts(row):
        return {key: value for key, value in row.items()
                if key not in {'id', 'exact_id', 'private', 'privacy_unknown'}}

    rules = privacy_rules(config)
    rules_hash = rules_revision(rules)
    for index, proposal in enumerate(proposals):
        validate_source_decisions(proposal, prefix=f'proposals[{index}].')
        prepared, reference = _read_prepare(proposal.pop('prepare'), f'proposals[{index}].prepare')
        package_refs.append(reference)
        if prepared['privacy_rules'] != rules or prepared['privacy_rules_revision'] != rules_hash:
            raise ValueError(f"proposals[{index}].prepare privacy rules changed: {reference['path']}")
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
        for field in ('members', 'nodes', 'edges'):
            for row in prepared['neighborhood'][field]:
                observe_current(row)
        for row in prepared.get('historical_versions', []):
            key = (_record(row['id']), row['knowledge_revision'])
            if key in historical and historical_facts(historical[key]) != historical_facts(row):
                raise ValueError(f'Conflicting historical prepare version: {row["id"]}@{row["knowledge_revision"]}')
            historical[key] = row
        packages.append(prepared)

    privacy = _PreparedPrivacy(packages, package_refs)
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
                for gap, ref in enumerate(compiled['unavailable_gaps']):
                    record = _record(ref['member'])
                    row = records.get(record)
                    if (record.table != 'member' or row is None or row.get('stale') is not False
                            or row.get('retired') is not False
                            or known.get(record) != ref['knowledge_revision']
                            or row.get('knowledge_revision') != ref['knowledge_revision']
                            or row.get('path') != path or row.get('source_revision') != source.get('revision')
                            or ref['gap'] not in row.get('coverage_gaps', [])):
                        raise ValueError('Unavailable gap must match a current prepared member and its coverage gap')
                    location = f'proposals[{index}].sources[{position}].unavailable_gaps[{gap}].member'
                    if privacy.marker(ref['member'], ref['knowledge_revision'], location) and known_private(source) is not True:
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
    from .content import original_text
    selected_sources = {source['path']: source for source in batch['sources'] if not source.get('deleted')}
    prepared_sources = {(source['path'], source['revision']): source
                        for package in packages for source in package['sources'] if not source.get('deleted')}
    originals = {}

    for index, item in enumerate(batch.get('members', [])):
        if item.get('kind') not in _TEXT_MEMBER_KINDS:
            continue
        path = item['path']
        selected = selected_sources.get(path)
        if selected is None:
            raise ValueError(f'batch.members[{index}].path must be selected for publication: {path}')
        source = prepared_sources[path, selected['revision']]
        _validate_prepared_member_location(item, source, originals, f'batch.members[{index}]')

    def check_snapshot_location(source, reference):
        start, end = reference.get('start_line'), reference.get('end_line')
        if source['kind'] == 'image':
            if start is not None or end is not None:
                raise ValueError(f"Image basis uses a locator without lines: {source['path']}")
        elif start is None or end is None:
            raise ValueError(f"Text basis requires start_line and end_line: {source['path']}")
        elif 'numbered_text' in source:
            original_text(_prepared_original(source, originals), start, end, reference.get('locator'))

    def require_exact(record):
        row = privacy.exact.get(record)
        if row is None:
            raise ValueError(f'References absent from prepare: {record.table}:{record.key}')
        return row

    # Apply checks precisely the writes and dependencies it uses. Keep only that
    # closure and reject unknown external references before the frozen file exists.
    def proposal_locations(field):
        return (f'proposals[{index}].{field}[{position}]' for index, proposal in enumerate(proposals)
                for position in range(len(proposal.get(field, []))))

    writes = {_record(item['id'], table): (item['id'], item, field, location)
              for table, field in (('member', 'members'), ('node', 'nodes'), ('semantic', 'edges'))
              for item, location in zip(batch.get(field, []), proposal_locations(field), strict=True)}
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

    def classification(identity, revision, location):
        record = _record(identity)
        if revision is not None or record.table in EXACT_ENDPOINT_TABLES:
            return privacy.marker(identity, revision, location)
        if record in private:
            return private[record]
        if record in resolving:
            raise ValueError(f'Private classification has cyclic evidence: {record}')
        if record not in writes:
            return privacy.marker(identity, known[record], location)
        resolving.add(record)
        _, item, field, location = writes[record]
        markers = []
        for identity, revision, ref_location in _privacy_dependencies(field, item, location):
            markers.append(classification(identity, revision, ref_location))
            if field != 'edges':
                evidence = _record(identity)
                if evidence not in writes:
                    snapshot = privacy.evidence_sources.get((evidence, known[evidence]))
                    if snapshot is not None:
                        markers.append(privacy.marker(snapshot, None, ref_location, authored_identity=identity))
        if field == 'members':
            if item.get('parent') and _record(item['parent']) not in writes:
                classification(item['parent'], None, f'{location}.parent')
            source = sources.get(item['path'])
            if source is None or type(source.get('private')) is not bool:
                raise ValueError(f"Member source absent or deleted in proposal: {item['path']}")
            markers.append(source['private'])
        elif field == 'edges':
            markers.extend(selected_sources[ref['path']]['private'] for ref in item.get('basis', []) if 'path' in ref)
        resolving.remove(record)
        private[record] = any(markers)
        return private[record]

    batch['compiled_private'] = {identity_text.get(record, identity): classification(record, None, location)
                                 for record, (identity, _, _, location) in writes.items()}
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

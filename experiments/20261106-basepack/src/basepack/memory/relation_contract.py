"""Supported graph types and the shape of independently authored relationships."""

SYSTEM_EDGE_TYPES = frozenset({'part_of', 'from_snapshot', 'has_basis', 'version_of'})
AUTHOR_EDGE_TYPES = frozenset({
    'tests', 'supports', 'contradicts', 'implements', 'requires', 'uses',
    'derived_from', 'supersedes', 'other',
})
EDGE_TYPES = SYSTEM_EDGE_TYPES | AUTHOR_EDGE_TYPES

LOGICAL_ENDPOINT_TABLES = frozenset({'member', 'node', 'semantic'})
EXACT_ENDPOINT_TABLES = frozenset({'knowledge_version', 'source_version', 'graph_edge'})


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate_edge(edge, *, location):
    if not isinstance(edge, dict):
        raise ValueError(f'{location}: Expected an edge object')
    unknown = edge.keys() - {'id', 'in', 'out', 'type', 'label', 'text', 'conditions',
                             'endpoint_versions', 'evidence', 'basis'}
    if unknown:
        raise ValueError(f'{location}: Unknown edge fields: {sorted(unknown)}')
    missing = [endpoint for endpoint in ('in', 'out') if endpoint not in edge]
    if missing:
        raise ValueError(f'{location} missing required fields: {", ".join(missing)}')
    edge_type = edge.get('type')
    if not isinstance(edge_type, str) or edge_type not in AUTHOR_EDGE_TYPES:
        raise ValueError(f'{location}.type: Choose an authored edge type: {", ".join(sorted(AUTHOR_EDGE_TYPES))}')
    if edge_type == 'other':
        label = edge.get('label')
        if not _nonempty(label) or not any(c.isascii() and c.isalpha() for c in label):
            raise ValueError(f'{location}.label: Provide a specific English relation phrase for other')
    elif 'label' in edge:
        raise ValueError(f'{location}.label: Only other takes a label')
    if not _nonempty(edge.get('text')):
        raise ValueError(f'{location}.text: Explain the evidenced relation')
    if 'conditions' in edge and not isinstance(edge['conditions'], (str, dict)):
        raise ValueError(f'{location}.conditions: Use text or an object')

    pins = edge.get('endpoint_versions', {})
    if not isinstance(pins, dict) or pins.keys() - {'in', 'out'}:
        raise ValueError(f'{location}.endpoint_versions: Specify in or out pins')
    for endpoint, pin in pins.items():
        if (not isinstance(pin, dict) or pin.keys() != {'id', 'knowledge_revision'}
                or not all(_nonempty(value) for value in pin.values())):
            raise ValueError(f'{location}.endpoint_versions.{endpoint}: Use id and knowledge_revision')

    for field in ('evidence', 'basis'):
        if field in edge and not isinstance(edge[field], list):
            raise ValueError(f'{location}.{field}: Expected an array of references')
    if not (edge.get('evidence') or edge.get('basis')):
        raise ValueError(f'{location}: An authored edge requires evidence or basis')
    for index, reference in enumerate(edge.get('basis', [])):
        validate_basis(reference, location=f'{location}.basis[{index}]')


def validate_basis(reference, *, location):
    if not isinstance(reference, dict):
        raise ValueError(f'{location}: Expected a basis object')
    if 'id' in reference:
        if (reference.keys() - {'id', 'knowledge_revision'}
                or ('knowledge_revision' in reference and not _nonempty(reference['knowledge_revision']))):
            raise ValueError(f'{location}: Use id with an optional knowledge_revision')
        return
    source_key = 'source_version' if 'source_version' in reference else 'path'
    if (not _nonempty(reference.get(source_key))
            or reference.keys() - {source_key, 'start_line', 'end_line', 'locator'}):
        raise ValueError(f'{location}: Use source_version or path with an exact original locator')
    start, end = reference.get('start_line'), reference.get('end_line')
    if (start is not None or end is not None) and (
        type(start) is not int or type(end) is not int or not 1 <= start <= end
    ):
        raise ValueError(f'{location}: Use an inclusive, positive start_line and end_line')
    if reference.get('locator') is not None and not isinstance(reference['locator'], dict):
        raise ValueError(f'{location}.locator: Expected an object')

"""Validate author-recorded source dispositions and refinement deferrals."""

from .images import ImageSource
from .privacy import privacy_rules, source_private


def dependencies(memory, batch, before_members, targets, expected):
    """Return versioned dependencies for the source-level author decisions."""
    from .store import _record

    fields = ('dispositions', 'deferred_refinement', 'unavailable_gaps')
    if not any(any(field in source for field in fields)
               for source in batch['sources']):
        return set()
    records = {_record(row['id']): row for row in before_members}
    for table in ('node', 'semantic'):
        records.update({_record(row['id']): row for row in memory._rows(table)})
    result = set()

    def reference(ref, *, source=None, gap=None):
        record = _record(ref['id'] if gap is None else ref['member'])
        if record.table not in {'member', 'node', 'semantic'}:
            raise ValueError('Disposition references must name knowledge records')
        row = records.get(record)
        revision = ref['knowledge_revision']
        if (row is None or row['stale'] or row['retired'] or row['knowledge_revision'] != revision
                or expected.get(record) != revision or record in targets):
            raise ValueError('Disposition dependency changed; prepare and read again')
        if gap is not None and (record.table != 'member' or row['path'] != source.path
                                or row['source_revision'] != source.revision
                                or gap not in row.get('coverage_gaps', [])):
            raise ValueError('Deferred gap must match a current member and its coverage gap')
        result.add(record)

    for item in batch['sources']:
        if not any(field in item for field in fields):
            continue
        if item.get('deleted'):
            raise ValueError('Deleted sources cannot record reading dispositions')
        source = memory._load_source(item['path'], item.get('kind'))
        if source.revision != item['revision']:
            raise ValueError(f'Source revision mismatch for {source.path}')
        if 'unavailable_gaps' in item:
            if not isinstance(item['unavailable_gaps'], list):
                raise ValueError('unavailable_gaps must be a list')
            for ref in item['unavailable_gaps']:
                if not isinstance(ref.get('reason'), str) or not ref['reason'].strip():
                    raise ValueError('Unavailable gap requires a reason')
                reference(ref, source=source, gap=ref['gap'])
                row = records[_record(ref['member'])]
                if row.get('stale') is not False or row.get('retired') is not False:
                    raise ValueError('Unavailable gap requires a fresh, non-retired member')
                if (row.get('private') is not False
                        and not source_private(source.path, privacy_rules(memory.config)['private_scope'])):
                    raise ValueError('Unavailable gap cannot expose a private member in a public source')
        for field in ('dispositions', 'deferred_refinement'):
            for entry in item.get(field, []):
                if not isinstance(entry.get('reason'), str) or not entry['reason'].strip():
                    raise ValueError('Source disposition or refinement requires a reason')
                if isinstance(source, ImageSource):
                    if entry.get('whole_image') is not True or 'start_line' in entry or 'end_line' in entry:
                        raise ValueError('Image decisions require whole_image')
                else:
                    start, end = entry['start_line'], entry['end_line']
                    if (type(start) is not int or type(end) is not int
                            or start < 1 or end < start or end > len(source.text.splitlines())):
                        raise ValueError('Source decision range is outside the original')
                if field == 'dispositions':
                    kind = entry['kind']
                    refs = entry.get('representations', [])
                    if kind not in {'no_knowledge', 'duplicate'} or (kind == 'duplicate') != bool(refs):
                        raise ValueError('Invalid disposition kind or duplicate representations')
                    for ref in refs:
                        reference(ref)
                else:
                    for gap in entry.get('gaps', []):
                        reference(gap, source=source, gap=gap['gap'])
    return result

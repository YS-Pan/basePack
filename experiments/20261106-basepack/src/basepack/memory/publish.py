"""Publish completed author drafts, or resume one already frozen batch."""

from hashlib import sha256
import json
from pathlib import Path

from .draft import freeze_file, read_author_draft, validate_batch


def publish(memory, *, completed=None, output=None, frozen=None, control, result, timeout=600,
            use_draft_context=True, batch_validator=None):
    """Compose freeze/apply; the publisher attests each assignment is complete.

    ``completed`` is an ordered list of {path, file_sha256, assignment} references.
    Paths are relative to the calling process, as with freeze/apply. ``frozen``
    instead resumes the exact saved batch, including its batch ID and UUIDs.
    The result file is only a projection of Memory.apply's database receipt.
    Wave publication uses ``use_draft_context=False`` to omit batch context on new freezes.
    An optional read-only ``batch_validator`` checks the same batch passed to apply.
    """
    if (completed is None) == (frozen is None):
        raise ValueError('Provide either completed drafts or an existing frozen batch')
    if completed is not None and output is None:
        raise ValueError('Completed drafts require an output path for the frozen batch')
    if frozen is not None and output is not None:
        raise ValueError('An existing frozen batch does not take an output path')
    path = Path(output if completed is not None else frozen).resolve()
    result_path = Path(result).resolve()
    if result_path == path:
        raise ValueError('The result projection must have a different path from the frozen batch')

    references = None
    if completed is not None:
        if not isinstance(completed, list) or not completed:
            raise ValueError('Completed drafts must be a nonempty ordered list')
        references, drafts = [], []
        for index, reference in enumerate(completed):
            if not isinstance(reference['assignment'], str) or not reference['assignment'].strip():
                raise ValueError(f'completed[{index}].assignment must identify the completed assignment')
            draft_path = Path(reference['path']).resolve()
            if draft_path == result_path:
                raise ValueError(f'completed[{index}] draft and result projection must have different paths')
            material = draft_path.read_bytes()
            file_sha256 = sha256(material).hexdigest()
            if file_sha256 != reference['file_sha256'].lower():
                raise ValueError(f'completed[{index}] file SHA256 mismatch for {draft_path}: '
                                 f"expected {reference['file_sha256']}, found {file_sha256}")
            draft = read_author_draft(draft_path, material=material)
            if not use_draft_context:
                # A wave keeps author provenance with each fixed draft and task.
                draft.pop('context', None)
            drafts.append(draft)
            references.append({'path': str(draft_path), 'file_sha256': file_sha256,
                               'assignment': reference['assignment']})
        batch = freeze_file(drafts, path, config=memory.config)
        material = path.read_bytes()
    else:
        material = path.read_bytes()
        batch = json.loads(material.decode('utf-8'))
        validate_batch(batch)

    if batch_validator is not None:
        if completed is not None and json.loads(material.decode('utf-8')) != batch:
            raise ValueError(f'Frozen batch changed after compilation: {path}')
        batch_validator(batch)
    frozen_file_sha256 = sha256(material).hexdigest()
    applied = memory.apply(batch, control=control, timeout=timeout)
    receipt = {'batch_id': batch['batch_id'], 'frozen': str(path),
               'frozen_file_sha256': frozen_file_sha256,
               'completed': references, 'apply': applied}
    try:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    except OSError as error:
        error.add_note(f"Memory.apply returned for batch {batch['batch_id']}; its database receipt is authoritative. "
                       f'Resume with frozen={str(path)!r} to recover this result projection; keep the same owner/control.')
        raise
    return {'batch_id': batch['batch_id'], 'frozen': str(path), 'result': str(result_path),
            **{key: applied[key] for key in ('sources', 'members', 'nodes', 'edges')},
            'invalidated': len(applied['invalidated'])}

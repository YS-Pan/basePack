"""Prepare candidate vectors before the knowledge publication transaction."""

from urllib.error import HTTPError

from basepack.embedding.admin import status
from basepack.embedding.client import EmbeddingClient
from basepack.embedding.qwen3_vl import MAX_REQUEST_INPUTS


def encode_candidates(memory, submitted, existing, *, timeout=600, control=None):
    from .maintenance import check

    identity = status(memory.config.machine)['model']['embedding_identity']
    pending = []
    for key, value in submitted.items():
        prior = existing.get(key)
        if (prior and prior.get('embedding_identity') == identity
                and prior.get('embedded_revision') == value['input_revision']
                and prior.get('embedding') is not None):
            value.update(embedding=prior['embedding'], embedding_identity=identity,
                         embedded_revision=value['input_revision'])
        else:
            pending.append((key, value))
    client = EmbeddingClient(memory.config.machine)
    for start in range(0, len(pending), MAX_REQUEST_INPUTS):
        if control:
            check(control)
        batch = pending[start:start + MAX_REQUEST_INPUTS]
        inputs = [({'image': str(memory.config.memory_dir / value['asset'])}
                   if value['kind'] == 'image' else value['title'] + '\n' + value['text'])
                  for _, value in batch]
        try:
            result = client.embed(inputs, timeout=timeout)
        except HTTPError as error:
            error.add_note("Candidate encoding failed for request inputs: " + "; ".join(
                f"{index}: member key={key!r} ({value['path']}, "
                f"lines {value['start_line']}:{value['end_line']})"
                for index, (key, value) in enumerate(batch)))
            raise
        if control:
            check(control)
        if result['embedding_identity'] != identity:
            raise ValueError('Embedding service identity changed during candidate encoding')
        if len(result['vectors']) != len(batch):
            raise ValueError('Embedding service returned a different number of vectors')
        for (_, value), vector in zip(batch, result['vectors'], strict=True):
            value.update(embedding=vector, embedding_identity=identity,
                         embedded_revision=value['input_revision'])

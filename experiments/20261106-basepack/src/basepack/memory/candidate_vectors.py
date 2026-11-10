"""Prepare candidate vectors before the knowledge publication transaction."""

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
            pending.append(value)
    client = EmbeddingClient(memory.config.machine)
    for start in range(0, len(pending), MAX_REQUEST_INPUTS):
        if control:
            check(control)
        batch = pending[start:start + MAX_REQUEST_INPUTS]
        inputs = [({'image': str(memory.config.memory_dir / value['asset'])}
                   if value['kind'] == 'image' else value['title'] + '\n' + value['text'])
                  for value in batch]
        result = client.embed(inputs, timeout=timeout)
        if control:
            check(control)
        if result['embedding_identity'] != identity:
            raise ValueError('Embedding service identity changed during candidate encoding')
        if len(result['vectors']) != len(batch):
            raise ValueError('Embedding service returned a different number of vectors')
        for value, vector in zip(batch, result['vectors'], strict=True):
            value.update(embedding=vector, embedding_identity=identity,
                         embedded_revision=value['input_revision'])

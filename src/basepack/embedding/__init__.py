"""Machine-shared local multimodal embeddings; importing never loads Torch."""

from .client import EmbeddingClient, EmbeddingError

__all__ = ["EmbeddingClient", "EmbeddingError"]

"""Machine-shared local multimodal embeddings; importing never loads Torch."""

from .client import EmbeddingClient

__all__ = ["EmbeddingClient"]

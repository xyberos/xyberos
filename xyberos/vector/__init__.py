"""Vector store provider implementations for the VectorStore contract (RFC-0016).

``CosineVectorStore`` is dependency-free and is the default backing store for
local development. ``ChromaVectorStore`` and ``PgVectorStore`` are optional
third-party adapters that import their dependency lazily and raise a clear
:class:`~exceptions.provider.ProviderError` when it is missing.
"""

from .adapters import ChromaVectorStore, PgVectorStore
from .cosine import CosineVectorStore

__all__ = ["ChromaVectorStore", "CosineVectorStore", "PgVectorStore"]

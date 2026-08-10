"""Vector store provider implementations for the VectorStore contract (RFC-0016).

``CosineVectorStore`` is a dependency-free in-memory store; ``SqliteVectorStore``
is a dependency-free persistent store (stdlib ``sqlite3``). ``ChromaVectorStore``
and ``PgVectorStore`` are optional third-party adapters that import their
dependency lazily and raise a clear :class:`~exceptions.provider.ProviderError`
when it is missing.
"""

from .adapters import ChromaVectorStore, PgVectorStore
from .cosine import CosineVectorStore
from .rerank import LexicalReranker, Reranker, ScoreReranker
from .sqlite import SqliteVectorStore

__all__ = [
    "ChromaVectorStore",
    "CosineVectorStore",
    "LexicalReranker",
    "PgVectorStore",
    "Reranker",
    "ScoreReranker",
    "SqliteVectorStore",
]

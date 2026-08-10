"""Second-stage rerankers for retrieval (RFC-0018, M13 deferred)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, cast

from ..contracts.vector import ScoredHit
from ..llm.adapters import require


class Reranker(ABC):
    """Re-rank candidate hits for a query (RFC-0018, M13)."""

    @abstractmethod
    def rerank(self, query: str, hits: Sequence[ScoredHit]) -> list[ScoredHit]:
        """Return ``hits`` re-ordered by the reranker's signal (best first)."""


class ScoreReranker(Reranker):
    """Dependency-free reranker that preserves the store's similarity order.

    A no-op re-order that makes reranking an explicit, swappable seam — useful
    as the default when no stronger signal is configured.
    """

    def rerank(self, query: str, hits: Sequence[ScoredHit]) -> list[ScoredHit]:
        return sorted(hits, key=lambda hit: hit.score, reverse=True)


class LexicalReranker(Reranker):
    """Optional TF-IDF lexical reranker (requires ``xyberos[rerank]``).

    Re-orders hits by cosine similarity between the query's TF-IDF vector and
    each hit's text (read from the payload ``value``/``text``/``fact``). A
    cheap, dependency-light second stage that often beats raw embedding scores
    for keyword-heavy queries. ``scikit-learn`` is imported lazily; a clear
    :class:`~exceptions.provider.ProviderError` is raised when it is missing.
    """

    def __init__(self, *, top_k: int = 5) -> None:
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")
        self._top_k = top_k

    def rerank(self, query: str, hits: Sequence[ScoredHit]) -> list[ScoredHit]:
        if not hits:
            return []
        require("sklearn")  # ensure scikit-learn is installed (raises ProviderError if missing)
        from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore[import-not-found]  # optional dependency

        texts = [self._text(hit) for hit in hits]
        vectorizer = cast(Any, TfidfVectorizer()).fit(texts + [query])
        query_vec = vectorizer.transform([query]).toarray()[0]

        scored: list[tuple[float, ScoredHit]] = []
        for index, hit in enumerate(hits):
            doc_vec = vectorizer.transform([texts[index]]).toarray()[0]
            scored.append((self._cosine(query_vec, doc_vec), hit))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [hit for _, hit in scored[: self._top_k]]

    @staticmethod
    def _text(hit: ScoredHit) -> str:
        payload = hit.payload or {}
        value = payload.get("value") or payload.get("text") or payload.get("fact")
        return str(value) if value is not None else hit.id

    @staticmethod
    def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

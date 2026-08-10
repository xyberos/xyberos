"""Pure-Python cosine-similarity vector store (no runtime dependencies)."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from ..contracts.vector import ScoredHit, VectorStore


class CosineVectorStore(VectorStore):
    """An in-memory :class:`VectorStore` using exact cosine similarity.

    Dependency-free and deterministic, so it is the default backing store for
    local development and tests. Every namespace holds ``id -> (vector,
    payload)`` and queries perform an exact (brute-force) similarity scan,
    which is fine for the small example/learning workloads Phase 0 targets.
    """

    def __init__(self) -> None:
        self._namespaces: dict[str, dict[str, tuple[list[float], Mapping[str, Any] | None]]] = {}

    def _bucket(self, namespace: str) -> dict[str, tuple[list[float], Mapping[str, Any] | None]]:
        return self._namespaces.setdefault(namespace, {})

    def upsert(
        self,
        namespace: str,
        id: str,
        vector: Sequence[float],
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        self._bucket(namespace)[id] = (list(vector), dict(payload) if payload is not None else None)

    def query(
        self,
        namespace: str,
        vector: Sequence[float],
        *,
        top_k: int = 5,
        threshold: float | None = None,
    ) -> list[ScoredHit]:
        bucket = self._bucket(namespace)
        query_vector = list(vector)
        scored: list[ScoredHit] = []
        for item_id, (stored, payload) in bucket.items():
            similarity = cosine(query_vector, stored)
            if threshold is not None and similarity < threshold:
                continue
            scored.append(ScoredHit(id=item_id, score=similarity, payload=payload))
        scored.sort(key=lambda hit: hit.score, reverse=True)
        return scored[:top_k]

    def delete(self, namespace: str, id: str) -> None:
        bucket = self._bucket(namespace)
        bucket.pop(id, None)
        if not bucket:
            self._namespaces.pop(namespace, None)

    def clear(self, namespace: str) -> None:
        self._namespaces.pop(namespace, None)

    def clear_all(self) -> None:
        """Drop every namespace and every vector."""
        self._namespaces.clear()


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Return cosine similarity in [-1.0, 1.0]; zero for empty/zero vectors."""
    if not a or not b:
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))

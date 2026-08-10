"""Semantic + recency memory over a VectorStore (RFC-0016, Phase 1)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ..contracts.memory import Memory
from ..contracts.vector import ScoredHit, VectorStore
from ..llm.embeddings import embed_text
from .sqlite import MemoryEntry


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_time(value: Any) -> float:
    """Best-effort timestamp for a stored ``created_at`` ISO string."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).timestamp()
        except ValueError:
            return 0.0
    return 0.0


def _entry_from_payload(payload: Mapping[str, Any] | None) -> MemoryEntry:
    payload = payload or {}
    return MemoryEntry(
        prompt=payload.get("prompt"),
        response=payload.get("response"),
        created_at=payload.get("created_at") or "",
    )


class VectorMemory(Memory):
    """Hybrid memory: embedding similarity blended with recency.

    Each stored turn is embedded (the prompt, or the response when there is no
    prompt) into a :class:`VectorStore` namespace and also kept in insertion
    order. Retrieval ranks by ``alpha * similarity + (1 - alpha) * recency``,
    so semantically relevant history is preferred without forgetting recent
    context. Entries preserve the ``prompt``/``response`` shape the Brain's
    history formatter expects.
    """

    def __init__(
        self,
        store: VectorStore,
        *,
        embedder: Any | None = None,
        namespace: str = "memory",
        top_k: int = 5,
        alpha: float = 0.7,
    ) -> None:
        if not isinstance(store, VectorStore):  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
            raise TypeError("store must be a VectorStore")
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")
        if not 0.0 <= alpha <= 1.0:
            raise ValueError("alpha must be between 0 and 1")
        self._store = store
        self._embedder = embedder
        self._namespace = namespace
        self._top_k = top_k
        self._alpha = alpha
        self._entries: list[MemoryEntry] = []

    def store(self, context: object) -> None:
        prompt = getattr(context, "prompt", None)
        response = getattr(context, "response", None)
        created = _utc_now()
        entry = MemoryEntry(
            prompt=prompt,
            response=response,
            metadata=dict(getattr(context, "metadata", None) or {}),
            plan=getattr(context, "plan", None),
            created_at=created,
        )
        self._entries.append(entry)
        text = prompt if isinstance(prompt, str) and prompt.strip() else (response or "")
        if self._embedder is not None and text:
            vector = embed_text(self._embedder, text)
            self._store.upsert(
                self._namespace,
                uuid4().hex,
                vector,
                payload={"prompt": prompt, "response": response, "created_at": created},
            )

    def retrieve(self, context: object) -> list[MemoryEntry]:
        if not self._entries:
            return []
        prompt = getattr(context, "prompt", None)
        if not isinstance(prompt, str) or not prompt or self._embedder is None:
            return list(reversed(self._entries[-self._top_k :]))
        vector = embed_text(self._embedder, prompt)
        hits = self._store.query(self._namespace, vector, top_k=self._top_k)
        if not hits:
            return list(reversed(self._entries[-self._top_k :]))
        ranked = _hybrid_rank(hits, self._alpha)
        return [_entry_from_payload(hit.payload) for hit in ranked]

    def retrieve_scored(self, context: object, *, top_k: int = 1) -> list[ScoredHit]:
        """Return the top matching turns as scored hits for confidence gating.

        Unlike :meth:`retrieve` (which blends similarity with recency), this
        exposes raw similarity scores so the hybrid router's ``MemoryResponder``
        can gate on how well a past turn actually matches (RFC-0017).
        """
        prompt = getattr(context, "prompt", None)
        if not isinstance(prompt, str) or not prompt or self._embedder is None:
            return []
        vector = embed_text(self._embedder, prompt)
        return self._store.query(self._namespace, vector, top_k=top_k)

    def clear(self) -> None:
        """Drop every stored turn, both vectors and insertion history."""
        self._entries = []
        self._store.clear(self._namespace)


def _hybrid_rank(hits: list[ScoredHit], alpha: float) -> list[ScoredHit]:
    """Sort hits by ``alpha * similarity + (1 - alpha) * recency``."""
    ordered = sorted(
        enumerate(hits),
        key=lambda pair: _parse_time(
            pair[1].payload.get("created_at") if pair[1].payload else None
        ),
    )
    n = len(ordered)
    scored: list[tuple[float, ScoredHit]] = []
    for index, (_, hit) in enumerate(ordered):
        recency = (index + 1) / n  # newest stored turn scores highest
        scored.append((alpha * hit.score + (1 - alpha) * recency, hit))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [hit for _, hit in scored]

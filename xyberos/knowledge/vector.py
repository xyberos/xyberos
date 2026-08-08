"""Semantic knowledge retrieval over a VectorStore (RFC-0016, Phase 1)."""

from __future__ import annotations

from typing import Any

from ..contracts.knowledge import Knowledge
from ..contracts.vector import VectorStore
from ..llm.embeddings import embed_text


class VectorKnowledge(Knowledge):
    """Knowledge facts retrieved by embedding similarity instead of keywords.

    ``add(key, value)`` indexes a fact under its key; ``query`` embeds the
    request and returns the top matching facts formatted for prompt injection,
    so the Brain's existing ``Relevant knowledge:`` section works unchanged.
    """

    def __init__(
        self,
        store: VectorStore,
        *,
        embedder: Any | None = None,
        namespace: str = "knowledge",
        top_k: int = 5,
    ) -> None:
        if not isinstance(store, VectorStore):
            raise TypeError("store must be a VectorStore")
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")
        self._store = store
        self._embedder = embedder
        self._namespace = namespace
        self._top_k = top_k

    def add(self, key: str, value: Any) -> None:
        """Index a fact; ``key`` is the stable id used for upserts."""
        text = f"{key}: {value}"
        vector = embed_text(self._embedder, text)
        self._store.upsert(
            self._namespace,
            key,
            vector,
            payload={"key": key, "value": value},
        )

    def query(self, context: object) -> str:
        prompt = getattr(context, "prompt", None)
        if not isinstance(prompt, str) or not prompt or self._embedder is None:
            return ""
        vector = embed_text(self._embedder, prompt)
        hits = self._store.query(self._namespace, vector, top_k=self._top_k)
        if not hits:
            return ""
        lines = []
        for hit in hits:
            payload = hit.payload or {}
            lines.append(f"- {payload.get('key', hit.id)}: {payload.get('value')}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Drop every indexed fact."""
        self._store.clear(self._namespace)

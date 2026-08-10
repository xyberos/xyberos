"""Embedding-based intent classification that learns by accumulation (RFC-0016)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from ..contracts.intent import Intent, IntentEngine
from ..contracts.vector import VectorStore
from ..llm.embeddings import embed_text


class EmbeddingIntentEngine(IntentEngine):
    """Classify by the nearest labeled example stored in a :class:`VectorStore`.

    ``learn(name, example)`` upserts a labeled example; ``classify`` embeds the
    request and returns the nearest neighbor's intent with its similarity as the
    confidence. Adding examples improves classification — "learning by
    accumulation" with no retraining.
    """

    def __init__(
        self,
        store: VectorStore,
        *,
        embedder: Any | None = None,
        namespace: str = "intents",
        threshold: float = 0.0,
        fallback: str = "general",
        default_target: str | None = None,
    ) -> None:
        # Defensive runtime guard for untyped callers; the annotation already
        # guarantees this type for type-checked callers.
        if not isinstance(store, VectorStore):  # type: ignore[unnecessary-isinstance]
            raise TypeError("store must be a VectorStore")
        self._store = store
        self._embedder = embedder
        self._namespace = namespace
        self._threshold = threshold
        self._fallback = fallback
        self._default_target = default_target

    def learn(
        self,
        name: str,
        example: str,
        *,
        target: str | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> None:
        """Store ``example`` as a labeled example of intent ``name``."""
        vector = embed_text(self._embedder, example)
        payload: dict[str, Any] = {"name": name, "example": example, "target": target}
        if params:
            payload["params"] = dict(params)
        self._store.upsert(self._namespace, uuid4().hex, vector, payload=payload)

    def classify(self, context: object) -> Intent:
        prompt = getattr(context, "prompt", None)
        if not isinstance(prompt, str) or not prompt:
            return Intent(name=self._fallback, confidence=0.0, target=self._default_target)
        vector = embed_text(self._embedder, prompt)
        hits = self._store.query(self._namespace, vector, top_k=1, threshold=self._threshold)
        if not hits:
            return Intent(name=self._fallback, confidence=0.0, target=self._default_target)
        payload = hits[0].payload or {}
        return Intent(
            name=payload.get("name", self._fallback),
            confidence=hits[0].score,
            params=payload.get("params") or {},
            target=payload.get("target") or self._default_target,
        )

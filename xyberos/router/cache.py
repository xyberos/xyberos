"""Cache-based responder — tier 5 of the hybrid chain (RFC-0017)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast
from uuid import uuid4

from ..contracts.responder import Responder
from ..llm.embeddings import embed_text


class CacheResponder(Responder):
    """Serve learned ``prompt → answer`` pairs with zero model calls.

    The cache answers IDENTICAL or NEAR-IDENTICAL requests from previously
    taught pairs. Two modes:

    * **store mode** (``store`` + ``embedder`` given) — near-exact matching by
      embedding similarity; ``teach()`` records an answer so a similar future
      request skips the model entirely.
    * **exact mode** (no store) — a lightweight in-memory ``prompt → answer``
      dict; ``teach()`` records an exact match.

    ``teach_batch()`` supports pre-seeding FAQ pairs at startup (RFC-0017, M5).
    """

    def __init__(
        self,
        store: Any | None = None,
        *,
        embedder: Any | None = None,
        namespace: str = "cache",
        threshold: float = 0.9,
        top_k: int = 1,
    ) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")
        if store is not None and embedder is None:
            raise ValueError("embedder is required when a store is provided")
        self._store = store
        self._embedder = embedder
        self._namespace = namespace
        self._threshold = threshold
        self._top_k = top_k
        self._exact: dict[str, str] = {}
        self._count = 0

    @property
    def size(self) -> int:
        """The number of taught pairs, in either mode."""
        return self._count

    def teach(self, prompt: str, answer: str) -> None:
        """Record ``prompt → answer`` for future identical/near requests."""
        if not isinstance(prompt, str) or not prompt:  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
            raise ValueError("prompt must be a non-empty string")
        if not isinstance(answer, str):  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
            raise TypeError("answer must be a string")
        if self._store is None:
            self._exact[prompt] = answer
        else:
            vector = embed_text(self._embedder, prompt)
            self._store.upsert(
                self._namespace,
                uuid4().hex,
                vector,
                payload={"prompt": prompt, "answer": answer},
            )
        self._count += 1

    def teach_batch(self, pairs: Iterable[tuple[str, str]]) -> int:
        """Record many ``(prompt, answer)`` pairs; return how many were added."""
        count = 0
        for prompt, answer in pairs:
            self.teach(prompt, answer)
            count += 1
        return count

    def respond(self, context: object) -> Any | None:
        """Return the cached answer for an identical/near request, else ``None``."""
        prompt = getattr(context, "prompt", None)
        if not isinstance(prompt, str) or not prompt:
            return None
        if self._store is None:
            return self._exact.get(prompt)
        vector = embed_text(self._embedder, prompt)
        hits = self._store.query(self._namespace, vector, top_k=self._top_k)
        if not hits or hits[0].score < self._threshold:
            return None
        return cast(dict[str, Any], hits[0].payload or {}).get("answer")

    def confidence(self, context: object) -> float:
        """Exact-mode: 1.0 on a hit; store-mode: the top similarity score."""
        prompt = getattr(context, "prompt", None)
        if not isinstance(prompt, str) or not prompt:
            return 0.0
        if self._store is None:
            return 1.0 if prompt in self._exact else 0.0
        vector = embed_text(self._embedder, prompt)
        hits = self._store.query(self._namespace, vector, top_k=self._top_k)
        return hits[0].score if hits else 0.0

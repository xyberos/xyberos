"""Memory-based responder — tier 4 of the hybrid chain (RFC-0017)."""

from __future__ import annotations

from typing import Any, cast

from ..contracts.responder import Responder


class MemoryResponder(Responder):
    """Answer from the most similar past Q→A in memory.

    Uses :meth:`~memory.VectorMemory.retrieve_scored` to get the most similar
    past turn with its raw similarity score. When the top score clears
    ``threshold``, the stored response is returned; otherwise ``None`` so the
    chain escalates to a stronger tier.

    The default ``threshold`` is conservative (0.9) because the default
    ``HashEmbedder`` is biased toward high cosine scores for unrelated text; a
    real semantic embedder supports lower thresholds (e.g. 0.7).
    """

    def __init__(self, memory: Any, *, threshold: float = 0.9, top_k: int = 1) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")
        self._memory = memory
        self._threshold = threshold
        self._top_k = top_k

    @property
    def memory(self) -> Any:
        """The wrapped memory provider."""
        return self._memory

    def respond(self, context: object) -> Any | None:
        """Return the best-matching past response when it clears the gate."""
        hits = self._scored_hits(context)
        if not hits or hits[0].score < self._threshold:
            return None
        payload = cast(dict[str, Any], hits[0].payload or {})
        response = payload.get("response")
        return response if isinstance(response, str) and response else None

    def confidence(self, context: object) -> float:
        """The best-matching turn's similarity score, or ``0.0``."""
        hits = self._scored_hits(context)
        return hits[0].score if hits else 0.0

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #

    def _scored_hits(self, context: object) -> list[Any]:
        """Best-effort scored retrieval; a non-supporting provider escalates."""
        retrieve_scored = getattr(self._memory, "retrieve_scored", None)
        if not callable(retrieve_scored):
            return []
        try:
            return cast(list[Any], retrieve_scored(context, top_k=self._top_k))
        except Exception:
            return []

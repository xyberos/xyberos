"""Knowledge-based responder — tier 3 of the hybrid chain (RFC-0017)."""

from __future__ import annotations

from typing import Any, cast

from ..contracts.responder import Responder


class KnowledgeResponder(Responder):
    """Answer from retrieved knowledge when the top fact clears a gate.

    Uses :meth:`~knowledge.VectorKnowledge.query_scored` to retrieve the top
    matching fact with its raw similarity score. When the top score clears
    ``threshold``, the fact's value is returned; otherwise ``None`` so the
    chain escalates to a stronger tier.

    The default ``threshold`` is conservative (0.9) because the default
    ``HashEmbedder`` is biased toward high cosine scores for unrelated text; a
    real semantic embedder supports lower thresholds (e.g. 0.7) for paraphrase
    matching.
    """

    def __init__(self, knowledge: Any, *, threshold: float = 0.9, top_k: int = 1) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")
        self._knowledge = knowledge
        self._threshold = threshold
        self._top_k = top_k

    @property
    def knowledge(self) -> Any:
        """The wrapped knowledge provider."""
        return self._knowledge

    def respond(self, context: object) -> Any | None:
        """Return the top fact's value when it clears the gate, else ``None``."""
        hits = self._scored_hits(context)
        if not hits or hits[0].score < self._threshold:
            return None
        payload = cast(dict[str, Any], hits[0].payload or {})
        return payload.get("value")

    def confidence(self, context: object) -> float:
        """The top fact's similarity score, or ``0.0`` when nothing retrieves."""
        hits = self._scored_hits(context)
        return hits[0].score if hits else 0.0

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #

    def _scored_hits(self, context: object) -> list[Any]:
        """Best-effort scored retrieval; a non-supporting provider escalates."""
        query_scored = getattr(self._knowledge, "query_scored", None)
        if not callable(query_scored):
            return []
        try:
            return cast(list[Any], query_scored(context, top_k=self._top_k))
        except Exception:
            return []

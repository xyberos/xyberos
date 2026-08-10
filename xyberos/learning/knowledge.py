"""Self-expanding knowledge ingestion (RFC-0018, M6)."""

from __future__ import annotations

from ..contracts.experience import ExperienceStore
from ..knowledge import VectorKnowledge
from .filters import promote_successful

__all__ = ["KnowledgePromoter"]


class KnowledgePromoter:
    """Auto-ingest positively-rated answers into a knowledge store.

    This is the "teacher loop" as a standalone step (RFC-0018, M6): successful
    episodes — explicit success or positive feedback — have their
    ``prompt → response`` pair indexed as a knowledge fact, so a
    :class:`~router.KnowledgeResponder` can answer similar future requests
    without an LLM call. The knowledge base grows from usage.
    """

    def __init__(
        self,
        experience: ExperienceStore,
        knowledge: VectorKnowledge,
        *,
        min_feedback: float = 0.5,
    ) -> None:
        self._experience = experience
        self._knowledge = knowledge
        self._min_feedback = min_feedback
        self._seen: set[str] = set()

    def promote(self, *, limit: int = 50) -> int:
        """Ingest successful episodes; return how many facts were added.

        Each episode is ingested at most once (tracked by episode id), so
        repeated ``promote()`` calls are idempotent.
        """
        episodes = promote_successful(
            self._experience,
            min_feedback=self._min_feedback,
            limit=limit,
        )
        ingested = 0
        for episode in episodes:
            if episode.id in self._seen:
                continue
            response = episode.response
            if not isinstance(response, str) or not response:
                continue
            self._seen.add(episode.id)
            self._knowledge.add(self._key_for(episode.prompt), response)
            ingested += 1
        return ingested

    @staticmethod
    def _key_for(prompt: str) -> str:
        """A stable store key so re-ingesting the same prompt upserts in place."""
        return f"qa:{prompt}"

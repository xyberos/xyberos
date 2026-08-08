"""Outcome-driven example promotion (RFC-0016, Phase 2).

:class:`ExamplePromoter` automates the promote step of the learning loop: it
scans the experience store for successful/positively rated episodes and feeds
them to the trainable providers so they improve by accumulation.
"""

from __future__ import annotations

from ..contracts.experience import ExperienceStore
from ..intent.embedding import EmbeddingIntentEngine
from ..planner.adaptive import AdaptivePlanner
from .filters import promote_successful

__all__ = ["ExamplePromoter"]


class ExamplePromoter:
    """Promote successful episodes into trainable intent/planner providers.

    ``promote()`` feeds each successful episode's intent label and plan into the
    configured :class:`EmbeddingIntentEngine` and :class:`AdaptivePlanner` via
    their ``learn`` methods.
    """

    def __init__(
        self,
        experience: ExperienceStore,
        *,
        intent_engine: EmbeddingIntentEngine | None = None,
        planner: AdaptivePlanner | None = None,
        min_feedback: float = 0.5,
    ) -> None:
        self._experience = experience
        self._intent_engine = intent_engine
        self._planner = planner
        self._min_feedback = min_feedback

    def promote(self, *, intent: str | None = None, limit: int = 50) -> int:
        """Promote successful episodes; returns how many learner calls were made."""
        promoted = 0
        episodes = promote_successful(
            self._experience,
            intent=intent,
            min_feedback=self._min_feedback,
            limit=limit,
        )
        for episode in episodes:
            if self._intent_engine is not None and episode.intent is not None:
                self._intent_engine.learn(episode.intent.name, episode.prompt)
                promoted += 1
            if self._planner is not None and episode.plan is not None:
                self._planner.learn(episode.prompt, episode.plan)
                promoted += 1
        return promoted

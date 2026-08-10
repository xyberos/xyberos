"""Escalation threshold tuning (RFC-0017, M14)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from ..contracts.experience import ExperienceStore
from .chain import ResponderChain

# Tiers that answer without any model generation — the "LLM-free" path.
CHEAP_TIERS = ("template", "tool", "knowledge", "memory", "cache")


class EscalationTuner:
    """Tune per-tier escalation gates from outcomes/feedback (bandit-style).

    Implements the RFC-0017 escalation-learning loop (M14): after each rated
    episode we know which tier answered (recorded on
    ``episode.metadata["responder"]`` by the chain). The tuner then:

    * raises a tier's gate when it answered but received **negative** feedback
      (escalate sooner next time);
    * slightly relaxes a tier's gate when it answered well (reward success);
    * relaxes all cheap tiers when the request escalated to the LLM yet was
      rated well (a cheap tier likely could have handled it).

    It also tracks recent per-tier hit rates and exposes :meth:`is_detached`
    for warm-up auto-detach: once LLM-free tiers reliably answer most requests,
    the system has "earned" its independence.
    """

    def __init__(
        self,
        chain: ResponderChain,
        *,
        learning_rate: float = 0.05,
        min_feedback: float = 0.5,
        min_gate: float = 0.0,
        max_gate: float = 0.95,
        window: int = 100,
    ) -> None:
        if not 0.0 <= learning_rate <= 1.0:
            raise ValueError("learning_rate must be between 0.0 and 1.0")
        self._chain = chain
        self._learning_rate = learning_rate
        self._min_feedback = min_feedback
        self._min_gate = min_gate
        self._max_gate = max_gate
        self._window = window
        self._recent_hits: list[str | None] = []

    @property
    def chain(self) -> ResponderChain:
        """The chain whose gates are tuned."""
        return self._chain

    def record_hit(self, tier: str | None) -> None:
        """Record which tier answered (``None`` = escalated to the LLM/degraded)."""
        self._recent_hits.append(tier)
        if len(self._recent_hits) > self._window:
            self._recent_hits.pop(0)

    def cheap_tier_hit_rate(self) -> float:
        """Fraction of recent requests answered by LLM-free tiers."""
        if not self._recent_hits:
            return 0.0
        cheap = sum(1 for tier in self._recent_hits if tier in CHEAP_TIERS)
        return cheap / len(self._recent_hits)

    def is_detached(self, *, threshold: float = 0.8) -> bool:
        """Whether LLM-free tiers have reliably answered recent requests."""
        return self.cheap_tier_hit_rate() >= threshold

    def tune(self, episodes: Sequence[Any]) -> int:
        """Adjust per-tier gates from rated episodes; return # adjustments made."""
        adjusted = 0
        for episode in episodes:
            feedback = getattr(episode, "feedback", None)
            if feedback is None:
                continue
            metadata = cast(dict[str, Any], getattr(episode, "metadata", None) or {})
            tier = metadata.get("responder")
            self.record_hit(tier)
            if tier is not None:
                if feedback < 0:
                    self._adjust(tier, self._learning_rate)
                    adjusted += 1
                elif feedback >= self._min_feedback:
                    self._adjust(tier, -self._learning_rate * 0.5)
                    adjusted += 1
            elif feedback >= self._min_feedback:
                # Escalated to the LLM yet rated well — cheap tiers should try harder.
                for name in self._tier_names():
                    self._adjust(name, -self._learning_rate * 0.25)
                adjusted += 1
        return adjusted

    def tune_from_experience(self, experience: ExperienceStore, *, limit: int = 50) -> int:
        """Pull rated episodes from an ``ExperienceStore`` and tune the gates."""
        episodes = [
            episode for episode in experience.query(limit=limit) if episode.feedback is not None
        ]
        return self.tune(episodes)

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #

    def _adjust(self, name: str, delta: float) -> None:
        current = self._chain.get_threshold(name)
        new = max(self._min_gate, min(self._max_gate, current + delta))
        if new != current:
            self._chain.set_threshold(name, new)

    def _tier_names(self) -> list[str]:
        return [name for name, _ in self._chain.responders]

"""Promote/demote helpers for the experience layer (RFC-0016, Phase 1).

These are the runtime "training" signals: they turn recorded episodes into
positive/negative examples that feed the trainable providers — e.g.
``promote_successful`` results can be passed to ``AdaptivePlanner.learn`` or
``EmbeddingIntentEngine.learn``.
"""

from __future__ import annotations

from typing import Any

from ..contracts.experience import Episode, ExperienceStore

__all__ = ["demote_failed", "promote_successful", "to_examples"]


def promote_successful(
    experience: ExperienceStore,
    *,
    intent: str | None = None,
    min_feedback: float = 0.5,
    limit: int = 50,
) -> list[Episode]:
    """Return episodes worth promoting (explicit success or a positive rating)."""
    episodes = experience.query(intent=intent, limit=limit)
    return [episode for episode in episodes if _is_success(episode, min_feedback)]


def demote_failed(
    experience: ExperienceStore,
    *,
    intent: str | None = None,
    max_feedback: float = -0.5,
    limit: int = 50,
) -> list[Episode]:
    """Return episodes worth demoting (explicit failure or a negative rating)."""
    episodes = experience.query(intent=intent, limit=limit)
    return [
        episode
        for episode in episodes
        if episode.outcome == "failure"
        or (episode.feedback is not None and episode.feedback <= max_feedback)
    ]


def to_examples(episodes: list[Episode], *, field: str = "response") -> list[tuple[str, Any]]:
    """Extract ``(prompt, target)`` pairs for the trainable providers.

    Feed the results to ``AdaptivePlanner.learn(prompt, plan)`` (use
    ``field="plan"``) or ``EmbeddingIntentEngine.learn(name, example)``.
    """
    examples: list[tuple[str, Any]] = []
    for episode in episodes:
        value = getattr(episode, field, None)
        if value is not None:
            examples.append((episode.prompt, value))
    return examples


def _is_success(episode: Episode, min_feedback: float) -> bool:
    if episode.outcome == "success":
        return True
    if episode.feedback is not None:
        return episode.feedback >= min_feedback
    return False

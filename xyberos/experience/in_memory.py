"""In-memory implementation of the ExperienceStore contract (no dependencies)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from ..contracts.experience import Episode, ExperienceStore


class InMemoryExperience(ExperienceStore):
    """Keep recorded episodes in memory.

    ``query`` returns the most recently recorded matching episodes (newest
    first). Suitable for development, tests, and single-process apps that do
    not need cross-restart learning data.
    """

    def __init__(self) -> None:
        self._episodes: list[Episode] = []
        self._by_id: dict[str, Episode] = {}

    def record(self, episode: Episode) -> Episode:
        if not episode.id:
            episode.id = uuid4().hex
        self._by_id[episode.id] = episode
        self._episodes.append(episode)
        return episode

    def query(
        self,
        *,
        intent: str | None = None,
        outcome: str | None = None,
        limit: int = 20,
    ) -> list[Episode]:
        matched = [
            episode
            for episode in self._episodes
            if (intent is None or (episode.intent is not None and episode.intent.name == intent))
            and (outcome is None or episode.outcome == outcome)
        ]
        return list(reversed(matched[-limit:]))

    def feedback(self, episode_id: str, rating: float, note: str | None = None) -> None:
        episode = self._by_id.get(episode_id)
        if episode is None:
            raise KeyError(f"no episode recorded with id {episode_id!r}")
        episode.feedback = rating
        if note:
            episode.metadata = {**episode.metadata, "feedback_note": note}

    def stats(self) -> Mapping[str, Any]:
        by_outcome: dict[str, int] = {}
        by_intent: dict[str, int] = {}
        for episode in self._episodes:
            by_outcome[episode.outcome] = by_outcome.get(episode.outcome, 0) + 1
            if episode.intent is not None:
                by_intent[episode.intent.name] = by_intent.get(episode.intent.name, 0) + 1
        return {
            "total": len(self._episodes),
            "by_outcome": by_outcome,
            "by_intent": by_intent,
        }

    def clear(self) -> None:
        """Drop every recorded episode."""
        self._episodes = []
        self._by_id = {}

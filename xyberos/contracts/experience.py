"""Experience / learning layer contract introduced by RFC-0016 (Phase 0).

The experience store is the *training signal source*: it records every episode
(prompt, intent, plan, tool calls, response, outcome, feedback) so that
intent/planner/memory/knowledge providers can learn from runtime outcomes. It
depends only on plain data (``object``), consistent with every other extension
contract.
"""

import time
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .intent import Intent


@dataclass
class Episode:
    """One recorded request/response cycle through the Brain pipeline."""

    prompt: str
    id: str = field(default_factory=lambda: uuid4().hex)
    intent: Intent | None = None
    plan: Any = None
    tool_calls: list[Mapping[str, Any]] = field(default_factory=list)
    response: str | None = None
    outcome: str | None = None  # "success" | "failure" | None
    feedback: float | None = None  # -1.0..1.0, set via ExperienceStore.feedback
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class ExperienceStore(ABC):
    """Records and queries runtime episodes for learning and feedback."""

    @abstractmethod
    def record(self, episode: Episode) -> Episode:
        """Persist an episode (filling in ``episode.id`` when missing)."""

    @abstractmethod
    def query(
        self,
        *,
        intent: str | None = None,
        outcome: str | None = None,
        limit: int = 20,
    ) -> list[Episode]:
        """Return recorded episodes matching the given filters."""

    @abstractmethod
    def feedback(self, episode_id: str, rating: float, note: str | None = None) -> None:
        """Attach a user/outcome rating (-1.0..1.0) to a recorded episode."""

    @abstractmethod
    def stats(self) -> Mapping[str, Any]:
        """Return aggregate counts (total episodes, by outcome, by intent)."""


# Compatibility alias matching the MemoryProvider/KnowledgeProvider convention.
ExperienceStoreProvider = ExperienceStore

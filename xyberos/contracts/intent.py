"""Intent classification contract introduced by RFC-0016 (Phase 0).

An intent engine classifies a request so the Brain can route it to the right
planner mode, tool, agent, or workflow. Like every other extension contract it
depends on ``object`` rather than Runtime's Context type, so providers stay
independent of core layers.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


def _empty_params() -> Mapping[str, Any]:
    """A fresh params mapping for each Intent."""
    return {}


@dataclass(frozen=True)
class Intent:
    """A classification of one request.

    ``name`` is the intent label (e.g. ``"refund"``, ``"faq"``, ``"chat"``).
    ``confidence`` ranges from 0.0 to 1.0. ``params`` may carry extracted
    slots/arguments. ``target`` optionally names the tool, agent, or workflow
    this intent routes to.
    """

    name: str
    confidence: float = 0.0
    params: Mapping[str, Any] = field(default_factory=_empty_params)
    target: str | None = None


class IntentEngine(ABC):
    """Classifies a request into an :class:`Intent`.

    Implementations range from deterministic rule engines to LLM-driven and
    embedding-based classifiers (added in RFC-0016 Phase 1). All of them share
    this one stable contract.
    """

    @abstractmethod
    def classify(self, context: object) -> Intent:
        """Classify the supplied execution context and return an Intent."""


# Compatibility alias matching the MemoryProvider/KnowledgeProvider convention.
IntentEngineProvider = IntentEngine

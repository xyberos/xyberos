"""Responder contracts for the hybrid router (RFC-0017, M4/M5)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class Responder(ABC):
    """Answers a request if it can; returns ``None`` to escalate.

    A responder that returns a non-``None`` value "handles" the request. The
    :class:`~router.chain.ResponderChain` iterates responders in priority
    order and stops at the first one that returns a confident answer.

    A responder may also expose :meth:`confidence` — a gate the router uses to
    decide whether an answer is confident enough to serve or should escalate to
    a stronger tier. The default returns ``1.0`` (always confident).
    """

    @abstractmethod
    def respond(self, context: object) -> Any | None:
        """Answer ``context`` if possible; return ``None`` to escalate."""

    def confidence(self, context: object) -> float:
        """Optional gate: ``0.0`` = cannot handle, ``1.0`` = certain."""
        return 1.0


@dataclass(frozen=True)
class Template:
    """One response template with multiple natural-language variants.

    ``pattern`` is matched against the request prompt and/or the classified
    intent name. ``variants`` are selected in rotation to avoid robotic
    repetition. ``requires_context`` lists metadata keys that, when present,
    are injected into ``{key}`` placeholders (RFC-0017, M5).
    """

    pattern: str
    variants: tuple[str, ...]
    confidence: float = 1.0
    requires_context: tuple[str, ...] = ()

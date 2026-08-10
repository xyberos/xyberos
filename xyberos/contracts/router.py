"""Router contract for the hybrid responder chain (RFC-0017, M4)."""

from abc import ABC, abstractmethod
from typing import Any


class Router(ABC):
    """Runs responders in priority order; escalates on ``None`` or low confidence.

    A router answers a request by consulting a configured chain of responders
    and returning the first confident answer. When every responder declines,
    it falls back to a configured policy (a final responder, a callable, or
    ``None`` to let the caller decide — e.g. the Brain's normal LLM path).
    """

    @abstractmethod
    def respond(self, context: object) -> Any:
        """Answer ``context`` via the configured responder chain."""

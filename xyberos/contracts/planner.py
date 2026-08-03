"""Planning extension contract defined by the v0.5 roadmap."""

from abc import ABC, abstractmethod
from typing import Any


class Planner(ABC):
    """Produces a provider-specific plan for an execution context.

    Planning engines are intentionally independent of Runtime and Brain. A
    future Brain orchestration revision can consume this contract without
    changing the Runtime request/response interface.
    """

    @abstractmethod
    def plan(self, context: object) -> Any:
        """Build and return a plan for the supplied execution context."""

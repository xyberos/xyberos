"""Agent extension contract defined by the v0.9 roadmap."""

from abc import ABC, abstractmethod


class Agent(ABC):
    """A named cognitive participant that transforms an execution context."""

    @property
    @abstractmethod
    def name(self) -> str:
        """A stable, unique agent identifier."""

    @abstractmethod
    def run(self, context: object) -> object:
        """Process and return an execution context."""

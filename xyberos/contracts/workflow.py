"""Workflow extension contract defined by the v0.7 roadmap."""

from abc import ABC, abstractmethod


class Workflow(ABC):
    """Executes one or more operations against an execution context."""

    @abstractmethod
    def run(self, context: object) -> object:
        """Run the workflow and return its resulting context."""

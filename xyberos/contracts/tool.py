"""Tool extension contract defined by the v0.4 roadmap."""

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """A named capability that can act on an execution context.

    This contract does not import Runtime or Context. Tool orchestration belongs
    to a later Brain capability, while implementations remain free to support
    the context type they need.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """A stable, unique name used to register and select the tool."""

    @abstractmethod
    def execute(self, context: object, **arguments: Any) -> Any:
        """Execute the tool for a context and return its provider-specific result."""

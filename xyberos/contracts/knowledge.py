"""Knowledge extension contract defined by the v0.6 roadmap."""

from abc import ABC, abstractmethod
from typing import Any


class Knowledge(ABC):
    """Queries a knowledge source using an execution context.

    The returned shape is provider-defined so local documents, graph stores,
    vector databases, and remote search services can share one stable contract.
    """

    @abstractmethod
    def query(self, context: object) -> Any:
        """Return knowledge relevant to the supplied execution context."""


# Compatibility name for external provider implementations.
KnowledgeProvider = Knowledge

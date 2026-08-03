"""Memory extension contract defined by the v0.3 roadmap."""

from abc import ABC, abstractmethod
from typing import Any


class Memory(ABC):
    """Stores and retrieves execution context without prescribing a backend.

    The contract intentionally depends on ``object`` rather than Runtime's
    Context type. This keeps extension contracts independent of core layers,
    allowing providers to support future context representations.
    """

    @abstractmethod
    def retrieve(self, context: object) -> Any:
        """Return memory relevant to the supplied execution context."""

    @abstractmethod
    def store(self, context: object) -> None:
        """Persist information from the supplied execution context."""


# Compatibility name for consumers of the early v0.2 placeholder.
MemoryProvider = Memory

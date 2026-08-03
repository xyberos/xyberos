"""In-memory implementation of the Memory contract."""

from typing import Any

from ..contracts.memory import Memory


class InMemoryMemory(Memory):
    """Store execution contexts in memory and retrieve them on demand.

    This is a minimal reference implementation suitable for development and
    tests. Real deployments can swap in database or vector-store providers
    without changing the contract.
    """

    def __init__(self) -> None:
        self._entries: list[Any] = []

    def retrieve(self, context: object) -> Any:
        """Return all stored entries as a list."""
        return list(self._entries)

    def store(self, context: object) -> None:
        """Persist the supplied execution context in memory."""
        self._entries.append(context)

    def clear(self) -> None:
        """Remove all stored entries."""
        self._entries.clear()

"""Reserved contract for the v0.3 memory subsystem."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class MemoryProvider(Protocol):
    """Marker contract for a future memory implementation."""

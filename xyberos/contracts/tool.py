"""Reserved contract for the v0.4 tool subsystem."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Tool(Protocol):
    """Marker contract for a future tool implementation."""

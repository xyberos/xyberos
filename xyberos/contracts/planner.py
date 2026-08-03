"""Reserved contract for the v0.5 planning subsystem."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Planner(Protocol):
    """Marker contract for a future planning implementation."""

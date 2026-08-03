"""Reserved contract for the v0.6 knowledge subsystem."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class KnowledgeProvider(Protocol):
    """Marker contract for a future knowledge implementation."""

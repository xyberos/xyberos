"""Lifecycle contract for platform services."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Service(Protocol):
    """A service that participates in Kernel lifecycle management."""

    def start(self) -> None:
        """Start the service."""

    def stop(self) -> None:
        """Stop the service."""

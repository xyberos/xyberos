"""Plugin extension contract defined by the v0.8 roadmap."""

from abc import ABC, abstractmethod


class Plugin(ABC):
    """An extension that can register and remove platform services."""

    @property
    @abstractmethod
    def name(self) -> str:
        """A stable, unique identifier for this plugin."""

    @abstractmethod
    def register(self, kernel: object) -> None:
        """Register the plugin's services with the supplied platform kernel."""

    @abstractmethod
    def unregister(self, kernel: object) -> None:
        """Remove the plugin's services from the supplied platform kernel."""

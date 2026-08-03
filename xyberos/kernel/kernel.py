"""Composition root for a Xyberos instance."""

from collections.abc import Callable, Mapping
from typing import Any

from .config import Config
from .logger import Logger
from .registry import ServiceRegistry
from ..plugins.loader import PluginLoader


class Kernel:
    """Own platform configuration, logging, services, and lifecycle only."""

    def __init__(self, config: Config | Mapping[str, Any] | None = None) -> None:
        self.config = config if isinstance(config, Config) else Config(config)
        self.registry = ServiceRegistry()
        self._started = False
        self.logger = Logger(
            name=self.config.get("logger_name", "xyberos"),
            level=self.config.get("log_level", "INFO"),
        )
        self.register("config", self.config)
        self.register("logger", self.logger)
        self.plugins = PluginLoader(self)
        self.register("plugins", self.plugins)

    @property
    def started(self) -> bool:
        """Whether the kernel lifecycle is currently active."""
        return self._started

    def register(self, name: str, service: object, *, replace: bool = False) -> object:
        """Register a shared service and return it.

        Registered services with a ``start`` or ``stop`` method participate in
        the kernel lifecycle in registration order and reverse order,
        respectively.
        """
        registered = self.registry.register(name, service, replace=replace)
        if self._started:
            start = getattr(service, "start", None)
            if callable(start):
                start()
        return registered

    def register_factory(
        self, name: str, factory: Callable[..., object], *, singleton: bool = True, replace: bool = False
    ) -> Callable[..., object]:
        """Register a dependency-injected service factory."""
        if self._started:
            raise RuntimeError("register factories before starting the kernel")
        return self.registry.register_factory(name, factory, singleton=singleton, replace=replace)

    def resolve(self, name: str) -> object:
        """Retrieve a registered shared service by name."""
        return self.registry.resolve(name)

    def inject(self, target: Callable[..., object], /, **overrides: object) -> object:
        """Construct or invoke a callable with registered dependencies."""
        return self.registry.inject(target, **overrides)

    def start(self) -> None:
        """Start all registered lifecycle-aware services."""
        if self._started:
            return
        for service in self.registry.values():
            start = getattr(service, "start", None)
            if callable(start):
                start()
        self._started = True

    def stop(self) -> None:
        """Stop registered lifecycle-aware services in reverse order."""
        if not self._started:
            return
        try:
            for service in reversed(self.registry.values()):
                stop = getattr(service, "stop", None)
                if callable(stop):
                    stop()
        finally:
            self._started = False

"""Composition root for a Xyberos instance."""

from collections.abc import Callable, Mapping
from typing import Any, TypeVar

from ..events import EventBus
from ..events.names import KERNEL_STARTED, KERNEL_STOPPED
from ..plugins.loader import PluginLoader
from ..security import Security, SqliteAuditStore
from .config import Config
from .logger import Logger
from .registry import ServiceRegistry

T = TypeVar("T")


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
        self.events = EventBus(logger=self.logger)
        self.register("config", self.config)
        self.register("logger", self.logger)
        self.register("events", self.events)
        self.plugins = PluginLoader(self)
        self.register("plugins", self.plugins)
        audit_path = self.config.get("security.audit_path")
        if audit_path:
            audit_store = SqliteAuditStore(audit_path)
            self.security = Security(audit_store=audit_store)
            self.register("security.audit_store", audit_store)
        else:
            self.security = Security()
        self.security._events = self.events
        self.register("security", self.security)

    @property
    def started(self) -> bool:
        """Whether the kernel lifecycle is currently active."""
        return self._started

    def register(self, name: str, service: T, *, replace: bool = False) -> T:
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
        self, name: str, factory: Callable[..., T], *, singleton: bool = True, replace: bool = False
    ) -> Callable[..., T]:
        """Register a dependency-injected service factory."""
        if self._started:
            raise RuntimeError("register factories before starting the kernel")
        return self.registry.register_factory(name, factory, singleton=singleton, replace=replace)

    def resolve(self, name: str) -> object:
        """Retrieve a registered shared service by name."""
        return self.registry.resolve(name)

    def inject(self, target: Callable[..., T], /, **overrides: object) -> T:
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
        self.events.emit(KERNEL_STARTED)

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
            self.events.emit(KERNEL_STOPPED)

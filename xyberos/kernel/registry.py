"""Service registration and constructor dependency injection."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..exceptions.registry import (
    CircularDependencyError,
    DependencyResolutionError,
    InvalidServiceNameError,
    ServiceAlreadyRegisteredError,
    ServiceNotFoundError,
)


_UNSET = object()


@dataclass
class _Registration:
    factory: Callable[..., object] | None = None
    instance: object = _UNSET
    singleton: bool = True


class ServiceRegistry:
    """A named service container with lazy factories and dependency injection.

    Dependencies are resolved from parameter names.  For example, a constructor
    ``def __init__(self, logger, config)`` receives services registered as
    ``"logger"`` and ``"config"``. Explicit keyword arguments always win.
    """

    def __init__(self) -> None:
        self._registrations: dict[str, _Registration] = {}
        self._resolving: list[str] = []
        self._registrations["registry"] = _Registration(instance=self)

    def register(self, name: str, service: object, *, replace: bool = False) -> object:
        """Register an already-created service instance."""
        self._validate_name(name)
        self._add(name, _Registration(instance=service), replace=replace)
        return service

    def register_factory(
        self,
        name: str,
        factory: Callable[..., object],
        *,
        singleton: bool = True,
        replace: bool = False,
    ) -> Callable[..., object]:
        """Register a lazy factory whose parameters are dependency-injected."""
        self._validate_name(name)
        if not callable(factory):
            raise TypeError("factory must be callable")
        self._add(name, _Registration(factory=factory, singleton=singleton), replace=replace)
        return factory

    def resolve(self, name: str) -> object:
        """Return a service, creating it from a factory if necessary."""
        self._validate_name(name)
        try:
            registration = self._registrations[name]
        except KeyError as exc:
            raise ServiceNotFoundError(f"No service registered with name: {name}") from exc

        if registration.instance is not _UNSET:
            return registration.instance
        if name in self._resolving:
            cycle = " -> ".join([*self._resolving, name])
            raise CircularDependencyError(f"Circular service dependency: {cycle}")

        self._resolving.append(name)
        try:
            assert registration.factory is not None
            service = self.inject(registration.factory)
            if registration.singleton:
                registration.instance = service
            return service
        finally:
            self._resolving.pop()

    def inject(self, target: Callable[..., object], /, **overrides: object) -> object:
        """Call ``target`` with registered services injected by parameter name."""
        if not callable(target):
            raise TypeError("target must be callable")

        arguments: list[object] = []
        keyword_arguments: dict[str, object] = {}
        for parameter in inspect.signature(target).parameters.values():
            if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
                continue
            if parameter.name in overrides:
                value = overrides[parameter.name]
            elif self.contains(parameter.name):
                value = self.resolve(parameter.name)
            elif parameter.default is not inspect.Parameter.empty:
                continue
            else:
                raise DependencyResolutionError(
                    f"Cannot inject required dependency '{parameter.name}' into {target!r}"
                )
            if parameter.kind is parameter.POSITIONAL_ONLY:
                arguments.append(value)
            else:
                keyword_arguments[parameter.name] = value
        return target(*arguments, **keyword_arguments)

    def contains(self, name: str) -> bool:
        """Return whether a name has been registered."""
        return name in self._registrations

    def unregister(self, name: str) -> object:
        """Remove and return the resolved service for ``name``."""
        self._validate_name(name)
        if name == "registry":
            raise ServiceAlreadyRegisteredError("The registry service cannot be removed")
        service = self.resolve(name)
        del self._registrations[name]
        return service

    @property
    def names(self) -> tuple[str, ...]:
        """Registered service names in lifecycle order."""
        return tuple(self._registrations)

    def values(self) -> tuple[object, ...]:
        """Resolve and return services in registration order."""
        return tuple(self.resolve(name) for name in self.names)

    def _add(self, name: str, registration: _Registration, *, replace: bool) -> None:
        if name in self._registrations and not replace:
            raise ServiceAlreadyRegisteredError(f"Service is already registered: {name}")
        self._registrations[name] = registration

    @staticmethod
    def _validate_name(name: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise InvalidServiceNameError("service name must be a non-empty string")

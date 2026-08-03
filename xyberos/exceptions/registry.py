"""Errors raised by the service registry."""


class RegistryError(Exception):
    """Base exception for registry and dependency-injection failures."""


class InvalidServiceNameError(RegistryError, ValueError):
    """Raised when a service name is not a non-empty string."""


class ServiceAlreadyRegisteredError(RegistryError, KeyError):
    """Raised when registering a name that is already in use."""


class ServiceNotFoundError(RegistryError, KeyError):
    """Raised when resolving or removing an unknown service."""


class CircularDependencyError(RegistryError):
    """Raised when factory dependencies form a cycle."""


class DependencyResolutionError(RegistryError):
    """Raised when a callable has a required dependency that cannot be injected."""

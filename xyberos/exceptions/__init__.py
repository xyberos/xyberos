"""Xyberos domain exceptions."""

from .agent import AgentAlreadyRegisteredError, AgentError, AgentNotFoundError
from .plugin import PluginAlreadyLoadedError, PluginError, PluginLoadError, PluginNotFoundError
from .tool import ToolAlreadyRegisteredError, ToolError, ToolNotFoundError
from .registry import (
    CircularDependencyError,
    DependencyResolutionError,
    InvalidServiceNameError,
    RegistryError,
    ServiceAlreadyRegisteredError,
    ServiceNotFoundError,
)
from .runtime import CognitiveRuntimeError, ContextExecutionError
from .kernel import KernelError
from .provider import ProviderError

__all__ = [
    "AgentAlreadyRegisteredError",
    "AgentError",
    "AgentNotFoundError",
    "CircularDependencyError",
    "CognitiveRuntimeError",
    "ContextExecutionError",
    "DependencyResolutionError",
    "InvalidServiceNameError",
    "KernelError",
    "ProviderError",
    "PluginAlreadyLoadedError",
    "PluginError",
    "PluginLoadError",
    "PluginNotFoundError",
    "RegistryError",
    "ServiceAlreadyRegisteredError",
    "ServiceNotFoundError",
    "ToolAlreadyRegisteredError",
    "ToolError",
    "ToolNotFoundError",
]

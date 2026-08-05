"""Xyberos domain exceptions."""

from .agent import (
    AgentAlreadyRegisteredError,
    AgentError,
    AgentNotFoundError,
    HandoffLoopError,
)
from .plugin import PluginAlreadyLoadedError, PluginError, PluginLoadError, PluginNotFoundError
from .tool import ToolAlreadyRegisteredError, ToolArgumentError, ToolError, ToolNotFoundError
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
from .llm import LLMOutputError, StructuredOutputError
from .provider import ProviderError
from .workflow import WorkflowError, WorkflowPaused

__all__ = [
    "AgentAlreadyRegisteredError",
    "AgentError",
    "AgentNotFoundError",
    "CircularDependencyError",
    "CognitiveRuntimeError",
    "ContextExecutionError",
    "DependencyResolutionError",
    "HandoffLoopError",
    "InvalidServiceNameError",
    "KernelError",
    "LLMOutputError",
    "ProviderError",
    "PluginAlreadyLoadedError",
    "PluginError",
    "PluginLoadError",
    "PluginNotFoundError",
    "RegistryError",
    "ServiceAlreadyRegisteredError",
    "ServiceNotFoundError",
    "StructuredOutputError",
    "ToolAlreadyRegisteredError",
    "ToolArgumentError",
    "ToolError",
    "ToolNotFoundError",
    "WorkflowError",
    "WorkflowPaused",
]

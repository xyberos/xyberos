"""Typed plugin base classes (``EXTRA.md`` approach #1).

Each typed base is a thin :class:`~xyberos.contracts.Plugin` subclass whose
``register()`` wires a contribution through the **public** kernel API
(``kernel.resolve(...)`` / ``kernel.register(...)`` / ``ToolRegistry.register``).
The core stays untouched; "typed plugins" are an SDK concern.

A typed plugin adds two things on top of the ``Plugin`` contract:

* ``plugin_type`` — a machine-readable key (matches :data:`introspect.CONTRACTS`)
* ``description`` — a human-readable summary for docs/wizards
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from xyberos.contracts import (
    Agent,
    Knowledge,
    KnowledgeProvider,
    LLMProvider,
    Memory,
    MemoryProvider,
    Planner,
    Plugin,
    Service,
    Tool,
    VectorStore,
    Workflow,
)

__all__ = [
    "CONTRIBUTE_METHODS",
    "TYPED_BASES",
    "AgentPlugin",
    "KnowledgePlugin",
    "LLMPlugin",
    "MemoryPlugin",
    "PlannerPlugin",
    "ServicePlugin",
    "ToolPlugin",
    "TypedPlugin",
    "VectorPlugin",
    "WorkflowPlugin",
]


def _pop_tool(registry: Any, name: str) -> None:
    """Best-effort removal of a tool (ToolRegistry has no public unregister)."""
    unregister = getattr(registry, "unregister", None)
    if callable(unregister):
        unregister(name)
        return
    store = getattr(registry, "_tools", None)
    if isinstance(store, dict):
        store.pop(name, None)


class TypedPlugin(Plugin, ABC):
    """Base for all typed plugins. Adds ``plugin_type`` + ``description``.

    ``name``/``register``/``unregister`` remain abstract (from ``Plugin``);
    each typed subclass below supplies the standard ``register``/``unregister``
    wiring.
    """

    plugin_type: str = "other"
    description: str = ""

    @property
    def name(self) -> str:  # pragma: no cover - abstract in Plugin
        raise NotImplementedError


class ToolPlugin(TypedPlugin, ABC):
    """A plugin that contributes one or more :class:`~xyberos.contracts.Tool`."""

    plugin_type = "tool"

    @abstractmethod
    def tools(self) -> list[Tool]:
        """Return the Tool instances this plugin contributes."""

    def register(self, kernel: Any) -> None:
        registry = kernel.resolve("tools")
        for tool in self.tools():
            registry.register(tool)

    def unregister(self, kernel: Any) -> None:
        registry = kernel.resolve("tools")
        for tool in self.tools():
            _pop_tool(registry, tool.name)


class LLMPlugin(TypedPlugin, ABC):
    """A plugin that contributes an :class:`~xyberos.contracts.LLMProvider`."""

    plugin_type = "llm"

    @abstractmethod
    def llm(self) -> LLMProvider:
        """Return the LLM provider this plugin contributes."""

    def register(self, kernel: Any) -> None:
        kernel.register("llm", self.llm(), replace=True)

    def unregister(self, kernel: Any) -> None:
        pass


class MemoryPlugin(TypedPlugin, ABC):
    """A plugin that contributes a :class:`~xyberos.contracts.Memory` provider."""

    plugin_type = "memory"

    @abstractmethod
    def memory(self) -> MemoryProvider:
        """Return the memory provider this plugin contributes."""

    def register(self, kernel: Any) -> None:
        kernel.register("memory", self.memory(), replace=True)

    def unregister(self, kernel: Any) -> None:
        pass


class KnowledgePlugin(TypedPlugin, ABC):
    """A plugin that contributes a :class:`~xyberos.contracts.Knowledge` provider."""

    plugin_type = "knowledge"

    @abstractmethod
    def knowledge(self) -> KnowledgeProvider:
        """Return the knowledge provider this plugin contributes."""

    def register(self, kernel: Any) -> None:
        kernel.register("knowledge", self.knowledge(), replace=True)

    def unregister(self, kernel: Any) -> None:
        pass


class VectorPlugin(TypedPlugin, ABC):
    """A plugin that contributes a :class:`~xyberos.contracts.VectorStore`."""

    plugin_type = "vector"

    @abstractmethod
    def vector_store(self) -> VectorStore:
        """Return the vector store this plugin contributes."""

    def register(self, kernel: Any) -> None:
        kernel.register("vector_store", self.vector_store(), replace=True)

    def unregister(self, kernel: Any) -> None:
        pass


class WorkflowPlugin(TypedPlugin, ABC):
    """A plugin that contributes a :class:`~xyberos.contracts.Workflow`."""

    plugin_type = "workflow"

    @abstractmethod
    def workflow(self) -> Workflow:
        """Return the workflow this plugin contributes."""

    def register(self, kernel: Any) -> None:
        kernel.register("workflow", self.workflow(), replace=True)

    def unregister(self, kernel: Any) -> None:
        pass


class PlannerPlugin(TypedPlugin, ABC):
    """A plugin that contributes a :class:`~xyberos.contracts.Planner`."""

    plugin_type = "planner"

    @abstractmethod
    def planner(self) -> Planner:
        """Return the planner this plugin contributes."""

    def register(self, kernel: Any) -> None:
        kernel.register("planner", self.planner(), replace=True)

    def unregister(self, kernel: Any) -> None:
        pass


class AgentPlugin(TypedPlugin, ABC):
    """A plugin that contributes an :class:`~xyberos.contracts.Agent`."""

    plugin_type = "agent"

    @abstractmethod
    def agent(self) -> Agent:
        """Return the agent this plugin contributes."""

    def register(self, kernel: Any) -> None:
        kernel.register("agent", self.agent(), replace=True)

    def unregister(self, kernel: Any) -> None:
        pass


class ServicePlugin(TypedPlugin, ABC):
    """A plugin that contributes a :class:`~xyberos.contracts.Service`."""

    plugin_type = "service"

    @abstractmethod
    def service(self) -> Service:
        """Return the lifecycle-aware service this plugin contributes."""

    def register(self, kernel: Any) -> None:
        kernel.register(self.name, self.service(), replace=True)

    def unregister(self, kernel: Any) -> None:
        pass


#: plugin type key -> typed base class (shared with the generator/validator).
TYPED_BASES: dict[str, type[TypedPlugin]] = {
    "tool": ToolPlugin,
    "llm": LLMPlugin,
    "memory": MemoryPlugin,
    "knowledge": KnowledgePlugin,
    "vector": VectorPlugin,
    "workflow": WorkflowPlugin,
    "planner": PlannerPlugin,
    "agent": AgentPlugin,
    "service": ServicePlugin,
    "other": TypedPlugin,
}

#: plugin type key -> name of the abstract contribute method on its typed base.
CONTRIBUTE_METHODS: dict[str, str | None] = {
    "tool": "tools",
    "llm": "llm",
    "memory": "memory",
    "knowledge": "knowledge",
    "vector": "vector_store",
    "workflow": "workflow",
    "planner": "planner",
    "agent": "agent",
    "service": "service",
    "other": None,
}

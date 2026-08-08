"""Higher-level orchestration for executing tools against a context."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..contracts.tool import Tool
from ..runtime.context import CognitiveContext
from .registry import ToolRegistry


class ToolRunner:
    """Select and execute tools using a shared registry."""

    def __init__(self, tools: ToolRegistry | Iterable[Tool] | None = None) -> None:
        if isinstance(tools, ToolRegistry):
            self.registry = tools
        else:
            self.registry = ToolRegistry(list(tools or ()))

    @property
    def names(self) -> tuple[str, ...]:
        """Registered tool names in execution order."""
        return self.registry.names

    def register(self, tool: Tool) -> Tool:
        """Register a tool for future orchestration."""
        return self.registry.register(tool)

    def get(self, name: str) -> Tool:
        """Return a tool by name."""
        return self.registry.get(name)

    def choose(self, context: CognitiveContext, *, tool_names: Iterable[str] | None = None) -> str:
        """Pick a tool name, honoring an intent target before the prompt heuristic.

        When the context carries an :class:`~contracts.intent.Intent` whose
        ``target`` names a registered tool, that tool wins (RFC-0016). Otherwise
        the historical prompt-name heuristic is used.
        """
        names = tuple(tool_names) if tool_names is not None else self.names
        if not names:
            raise ValueError("no tools are registered")

        intent = getattr(context, "intent", None)
        target = getattr(intent, "target", None)
        if target and target in names:
            return target

        prompt = context.prompt
        for name in names:
            if name and name in prompt:
                return name
        return names[0]

    def run(self, name: str, context: CognitiveContext, **arguments: Any) -> Any:
        """Execute a named tool against a context."""
        return self.registry.execute(name, context, **arguments)

    def dispatch(
        self, context: CognitiveContext, *, tool_names: Iterable[str] | None = None, **arguments: Any
    ) -> Any:
        """Choose a tool and execute it against a cognitive context."""
        # Runtime guard for untyped callers; type checkers treat it as redundant.
        if not isinstance(context, CognitiveContext):  # type: ignore[unnecessary-isinstance]
            raise TypeError("context must be a CognitiveContext")
        return self.run(self.choose(context, tool_names=tool_names), context, **arguments)

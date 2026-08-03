"""Registry for named tools implementing the Tool contract."""

from typing import Any

from ..contracts.tool import Tool
from ..exceptions.tool import ToolAlreadyRegisteredError, ToolNotFoundError


class ToolRegistry:
    """Register, look up, and execute named tools."""

    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or ():
            self.register(tool)

    @property
    def names(self) -> tuple[str, ...]:
        """Registered tool names in registration order."""
        return tuple(self._tools)

    def register(self, tool: Tool) -> Tool:
        """Register a tool for subsequent execution."""
        if not isinstance(tool, Tool):
            raise TypeError("tool must implement the Tool contract")
        if not isinstance(tool.name, str) or not tool.name.strip():
            raise ValueError("tool name must be a non-empty string")
        if tool.name in self._tools:
            raise ToolAlreadyRegisteredError(f"Tool is already registered: {tool.name}")
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Tool:
        """Return a registered tool by name."""
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolNotFoundError(f"No tool registered with name: {name}") from exc

    def execute(self, name: str, context: object, **arguments: Any) -> Any:
        """Execute the named tool against a context."""
        return self.get(name).execute(context, **arguments)

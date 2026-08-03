"""Tool registry errors."""


class ToolError(Exception):
    """Base error for tool registration and execution failures."""


class ToolAlreadyRegisteredError(ToolError, KeyError):
    """Raised when a tool name is already registered."""


class ToolNotFoundError(ToolError, KeyError):
    """Raised when an unknown tool is requested or executed."""

"""Multi-agent runtime errors."""


class AgentError(Exception):
    """Base error for agent registration and execution failures."""


class AgentAlreadyRegisteredError(AgentError, KeyError):
    """Raised when an agent name is already registered."""


class AgentNotFoundError(AgentError, KeyError):
    """Raised when an unknown agent is requested or removed."""

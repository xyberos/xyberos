"""Errors associated with cognitive runtime execution."""


class CognitiveRuntimeError(Exception):
    """Base error type for future runtime-specific failures."""


class ContextExecutionError(CognitiveRuntimeError):
    """Raised when a context cannot be executed by the runtime."""

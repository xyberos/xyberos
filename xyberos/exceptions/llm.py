"""Errors associated with language model output."""


class LLMOutputError(Exception):
    """Base error for language model output problems."""


class StructuredOutputError(LLMOutputError):
    """Raised when LLM text output cannot be parsed into structured data."""

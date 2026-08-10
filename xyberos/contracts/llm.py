"""Language model provider contract."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """A backend capable of generating text from a prompt."""

    def generate(self, prompt: str) -> str:
        """Generate a text response for ``prompt``."""
        ...

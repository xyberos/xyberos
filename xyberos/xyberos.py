"""Public API for the Xyberos core."""

from collections.abc import Mapping
from typing import Any

try:
    from .brain.llm import LLMProvider
    from .kernel.kernel import Kernel
except ImportError:  # Executing from the repository directory.
    from brain.llm import LLMProvider
    from kernel.kernel import Kernel


class Xyberos(Kernel):
    """Named public application class; inherits the complete kernel API."""


def create_app(config: Mapping[str, Any] | None = None, llm: LLMProvider | None = None) -> Xyberos:
    """Build a ready-to-use Xyberos application."""
    return Xyberos(config=config, llm=llm)


def chat(prompt: str, *, config: Mapping[str, Any] | None = None, llm: LLMProvider | None = None) -> str:
    """One-shot helper for the default application configuration."""
    return create_app(config=config, llm=llm).chat(prompt)


__all__ = ["Xyberos", "create_app", "chat"]

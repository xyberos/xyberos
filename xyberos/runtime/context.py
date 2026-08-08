"""Data passed through the Xyberos cognitive pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - import-time only, not runtime
    from ..contracts.intent import Intent


@dataclass
class CognitiveContext:
    """A single request and its eventual response.

    ``metadata`` is deliberately open-ended so callers can attach request IDs,
    user information, or tracing data without changing the core API. ``plan``
    holds a provider-defined plan produced by the planner during processing.
    ``intent`` holds the classification produced by an intent engine, when one
    is configured (RFC-0016).
    """

    prompt: str
    response: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: Exception | None = None
    plan: Any | None = None
    intent: Intent | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.prompt, str):
            raise TypeError("prompt must be a string")
        if not self.prompt.strip():
            raise ValueError("prompt must not be empty")

    @property
    def succeeded(self) -> bool:
        """Whether this request completed without an error."""
        return self.response is not None and self.error is None

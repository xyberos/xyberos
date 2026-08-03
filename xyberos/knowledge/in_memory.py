"""In-memory implementation of the Knowledge contract."""

from typing import Any

from ..contracts.knowledge import Knowledge


class InMemoryKnowledge(Knowledge):
    """Query a simple in-memory knowledge store.

    Facts are keyed by keyword; ``query`` returns the facts whose keyword
    appears in the context prompt. Suitable for development and tests.
    """

    def __init__(self, facts: dict[str, Any] | None = None) -> None:
        self._facts = dict(facts or {})

    def query(self, context: object) -> dict[str, Any]:
        """Return facts whose keyword appears in the context prompt."""
        prompt = str(getattr(context, "prompt", ""))
        return {key: value for key, value in self._facts.items() if key in prompt}

    def add(self, key: str, value: Any) -> None:
        """Register a fact under a keyword."""
        self._facts[key] = value

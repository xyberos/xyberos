"""LLM-driven planning engine."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..contracts.planner import Planner
from ..llm import EchoLLM, LLMProvider


class LLMPlanner(Planner):
    """Derive an ordered plan by asking an LLM to break down a request.

    ``plan`` asks the configured LLM to return one step per line and parses the
    response into a list of steps. A custom ``parse`` callable can turn the raw
    model output into any shape (e.g. JSON). When no model is supplied it falls
    back to ``EchoLLM`` — a degenerate default; pass a real model in production.
    """

    INSTRUCTION = (
        "Break the following request into a short, ordered plan. "
        "Return one step per line with no numbering or bullet prefixes.\n\n{request}"
    )

    def __init__(
        self,
        llm: LLMProvider | None = None,
        *,
        parse: Callable[[str], Any] | None = None,
    ) -> None:
        if parse is not None and not callable(parse):
            raise TypeError("parse must be callable")
        self._llm = llm or EchoLLM()
        self._parse = parse or self._default_parse

    def plan(self, context: object) -> Any:
        """Build a plan by asking the LLM to break down the context prompt."""
        request = getattr(context, "prompt", "")
        response = self._llm.generate(self.INSTRUCTION.format(request=request))
        if not isinstance(response, str):
            raise TypeError("LLM must return a string")
        return self._parse(response)

    @staticmethod
    def _default_parse(response: str) -> list[str]:
        """Split the model output into non-empty lines."""
        return [line.strip() for line in response.splitlines() if line.strip()]

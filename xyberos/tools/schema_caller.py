"""Schema-driven tool calling (RFC-0018, M9)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, cast

from ..exceptions.llm import StructuredOutputError
from ..exceptions.tool import ToolArgumentError, ToolNotFoundError
from ..llm import LLMProvider, structured
from ..runtime.context import CognitiveContext
from .runner import ToolRunner

# A parser turns raw LLM text into a mapping with tool/arguments.
ToolCallParser = Callable[[str], Any]


class SchemaToolCaller:
    """Pick a tool and extract typed arguments via structured LLM output.

    Given the user request and the registered tools' JSON schemas, asks the LLM
    to return ``{"tool": "...", "arguments": {...}}`` — or ``{"tool": null}``
    when no tool applies — replacing the name-substring heuristic in
    :meth:`ToolRunner.choose` (RFC-0018, M9). Arguments are validated/coerced by
    the tool's own schema on execution.
    """

    _INSTRUCTION = (
        "You have access to these tools. Given the user request, choose the "
        "single best tool (or none) and extract its arguments.\n\n"
        "Tools:\n{tools}\n\n"
        'Respond ONLY with JSON: {{"tool": "name" or null, "arguments": {{params}}}}.\n\n'
        "User request: {prompt}"
    )

    def __init__(
        self,
        llm: LLMProvider,
        runner: ToolRunner,
        *,
        parse: ToolCallParser | None = None,
    ) -> None:
        self._llm = llm
        self._runner = runner
        self._parse: ToolCallParser = parse if parse is not None else self._default_parse

    def _default_parse(self, text: str) -> Any:
        """Parse structured output from the configured LLM."""
        return structured(self._llm, text)

    @property
    def llm(self) -> LLMProvider:
        """The LLM used for selection."""
        return self._llm

    @property
    def runner(self) -> ToolRunner:
        """The tool runner whose registry is consulted."""
        return self._runner

    def select(self, context: object) -> tuple[str, dict[str, Any]] | None:
        """Return ``(tool_name, arguments)`` for the best tool, or ``None``.

        ``None`` means no tool applies (LLM returned null, parsing failed, or
        the chosen name is unknown) — the caller should escalate.
        """
        prompt = getattr(context, "prompt", None)
        if not isinstance(prompt, str) or not prompt or not self._runner.names:
            return None
        instruction = self._instruction(prompt)
        try:
            data = self._parse(instruction)
        except (StructuredOutputError, ValueError, TypeError):
            return None
        if not isinstance(data, dict):
            return None
        data_dict = cast(dict[str, Any], data)
        name = data_dict.get("tool")
        if not isinstance(name, str) or name not in self._runner.names:
            return None
        arguments = data_dict.get("arguments")
        if not isinstance(arguments, dict):
            arguments = {}
        return (name, cast(dict[str, Any], arguments))

    def run(self, context: object, **defaults: Any) -> Any | None:
        """Select a tool, merge defaults, coerce arguments, and execute.

        Returns ``None`` when no tool applies, parsing fails, or the arguments
        are rejected by the tool's schema — so callers can escalate.
        """
        selected = self.select(context)
        if selected is None:
            return None
        name, arguments = selected
        merged = {**defaults, **arguments}
        try:
            return self._runner.run(name, cast(CognitiveContext, context), **merged)
        except (ToolArgumentError, ToolNotFoundError):
            return None

    def _instruction(self, prompt: str) -> str:
        lines: list[str] = []
        for name in self._runner.names:
            tool = self._runner.get(name)
            schema = getattr(tool, "schema", None)
            lines.append(json.dumps(schema) if isinstance(schema, dict) else json.dumps({"name": name}))
        return self._INSTRUCTION.format(tools="\n".join(lines), prompt=prompt)

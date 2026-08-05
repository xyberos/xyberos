"""Structured output parsing for language model responses."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from ..exceptions.llm import StructuredOutputError
from .llm import LLMProvider


# A parser turns raw LLM text into structured data.
Parser = Callable[[str], Any]


def extract_json(text: str) -> Any:
    """Extract the first JSON value (object, array, or scalar) from ``text``.

    Tolerates surrounding prose and markdown code fences — common in LLM
    output. Raises ``json.JSONDecodeError`` when no valid JSON value exists.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z0-9_-]*\s*\n?", "", stripped)
        stripped = re.sub(r"\n?```\s*$", "", stripped).strip()

    for opener, closer in (("{", "}"), ("[", "]"), ('"', '"')):
        start = stripped.find(opener)
        if start == -1:
            continue
        candidate = _balanced(stripped, start, opener, closer)
        if candidate is None:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return json.loads(stripped)


def _balanced(text: str, start: int, opener: str, closer: str) -> str | None:
    """Return the balanced JSON span starting at ``start``, or ``None``."""
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


class StructuredLLM:
    """Wrap an ``LLMProvider`` to parse its text output into structured data.

    ``parse(prompt)`` calls the underlying provider and converts the response
    with the configured parser (JSON by default), raising
    :class:`~exceptions.llm.StructuredOutputError` on failure.
    """

    def __init__(self, llm: LLMProvider, *, parser: Parser | None = None) -> None:
        if parser is not None and not callable(parser):
            raise TypeError("parser must be callable")
        self._llm = llm
        self._parser = parser or extract_json

    def generate(self, prompt: str) -> str:
        """Delegate to the wrapped provider."""
        return self._llm.generate(prompt)

    def parse(self, prompt: str) -> Any:
        """Generate and parse structured output from ``prompt``."""
        text = self.generate(prompt)
        try:
            return self._parser(text)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise StructuredOutputError(f"could not parse LLM output: {exc}") from exc


def structured(llm: LLMProvider, prompt: str, *, parser: Parser | None = None) -> Any:
    """One-shot structured output: parse ``llm.generate(prompt)`` into data."""
    return StructuredLLM(llm, parser=parser).parse(prompt)

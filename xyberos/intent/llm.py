"""LLM-driven intent classification (RFC-0016, Phase 1)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..contracts.intent import Intent, IntentEngine
from ..exceptions.llm import StructuredOutputError
from ..llm import EchoLLM, LLMProvider, extract_json, structured

# A parser turns raw LLM text into a mapping with name/confidence/target.
IntentParser = Callable[[str], dict[str, Any]]

_INSTRUCTION = (
    "Classify the user request into one intent. Return ONLY a JSON object with "
    'fields: "name" (a short intent label), "confidence" (0.0 to 1.0), '
    '"params" (an object of extracted arguments), and "target" (optional tool/agent/'
    'workflow name, or null).'
)


class LLMIntentEngine(IntentEngine):
    """Classify intents by asking an LLM for structured JSON output.

    Mirrors the :class:`~planner.llm.LLMPlanner` shape: an optional ``parse``
    callable customizes output handling, and a configurable ``fallback`` intent
    is returned when parsing fails so the engine composes safely in a cascade.
    """

    def __init__(
        self,
        llm: LLMProvider | None = None,
        *,
        schema: str | None = None,
        parse: IntentParser | None = None,
        fallback: str = "general",
        default_target: str | None = None,
        instruction: str | None = None,
    ) -> None:
        self._llm = llm or EchoLLM()
        self._schema = schema
        self._parse = parse or extract_json
        self._fallback = fallback
        self._default_target = default_target
        self._instruction = instruction or _INSTRUCTION

    def classify(self, context: object) -> Intent:
        prompt = getattr(context, "prompt", None)
        if not isinstance(prompt, str):
            prompt = ""
        instruction = self._instruction
        if self._schema:
            instruction = f"{instruction}\nAllowed intents / schema:\n{self._schema}"
        instruction = f"{instruction}\nUser request: {prompt}"
        try:
            data = structured(self._llm, instruction, parser=self._parse)
        except (StructuredOutputError, ValueError, TypeError):
            return Intent(name=self._fallback, confidence=0.0, target=self._default_target)
        if not isinstance(data, dict):
            return Intent(name=self._fallback, confidence=0.0, target=self._default_target)
        name = data.get("name") or data.get("intent") or self._fallback
        try:
            confidence = float(data.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        params = data.get("params") or {}
        if not isinstance(params, dict):
            params = {}
        target = data.get("target") or self._default_target
        return Intent(name=name, confidence=confidence, params=params, target=target)

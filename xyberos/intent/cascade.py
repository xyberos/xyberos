"""Confidence-gated cascade of intent engines (RFC-0016, Phase 1)."""

from __future__ import annotations

from ..contracts.intent import Intent, IntentEngine


class CascadeIntentEngine(IntentEngine):
    """Try engines in priority order; return the first above the threshold.

    Engines that return low confidence are skipped so a cheap heuristic or
    embedding engine can hand off to a stronger LLM engine, with a deterministic
    fallback when nothing is confident.
    """

    def __init__(
        self,
        *engines: IntentEngine,
        fallback: str = "general",
        confidence_threshold: float = 0.5,
        default_target: str | None = None,
    ) -> None:
        if not engines:
            raise ValueError("at least one intent engine is required")
        self._engines = engines
        self._fallback = fallback
        self._threshold = confidence_threshold
        self._default_target = default_target

    @property
    def engines(self) -> tuple[IntentEngine, ...]:
        """The engines tried in priority order."""
        return self._engines

    def classify(self, context: object) -> Intent:
        for engine in self._engines:
            intent = engine.classify(context)
            if intent.confidence >= self._threshold:
                return intent
        return Intent(name=self._fallback, confidence=0.0, target=self._default_target)

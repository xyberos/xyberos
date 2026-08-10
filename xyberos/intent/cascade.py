"""Confidence-gated cascade of intent engines (RFC-0016, Phase 1)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..contracts.intent import Intent, IntentEngine


class CascadeIntentEngine(IntentEngine):
    """Try engines in priority order; return the first above the threshold.

    Engines that return low confidence are skipped so a cheap heuristic or
    embedding engine can hand off to a stronger LLM engine, with a deterministic
    fallback when nothing is confident. ``learn`` is forwarded to every
    sub-engine that supports it, so ``app.intent.learn(...)`` keeps working when
    a cascade is installed (RFC-0017, M8).
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

    def learn(
        self,
        name: str,
        example: str,
        *,
        target: str | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> None:
        """Forward ``learn`` to every sub-engine that supports it.

        The embedding engine learns labeled examples by accumulation; this keeps
        ``app.intent.learn(...)`` working when a cascade is installed.
        Engines without a ``learn`` method are skipped.
        """
        for engine in self._engines:
            learn = getattr(engine, "learn", None)
            if callable(learn):
                learn(name, example, target=target, params=params)

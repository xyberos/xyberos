"""Deterministic, rule-based intent classification (no dependencies)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..contracts.intent import Intent, IntentEngine


@dataclass(frozen=True)
class IntentRule:
    """One intent classification rule.

    ``patterns`` are matched case-insensitively against the request prompt;
    the first rule with a matching pattern wins. ``target`` optionally names
    the tool, agent, or workflow this intent routes to.
    """

    name: str
    patterns: tuple[str, ...]
    target: str | None = None


class HeuristicIntentEngine(IntentEngine):
    """Classify requests by substring/keyword rules.

    The first rule whose pattern appears in the prompt (case-insensitive) wins
    with full confidence. When no rule matches, a fallback intent is returned
    with zero confidence so callers can escalate to a stronger engine.
    """

    def __init__(
        self,
        rules: Sequence[IntentRule] | None = None,
        *,
        fallback: str = "general",
        default_target: str | None = None,
    ) -> None:
        self._rules = tuple(rules or ())
        self._fallback = fallback
        self._default_target = default_target

    @property
    def rules(self) -> tuple[IntentRule, ...]:
        """The configured rules, in match priority order."""
        return self._rules

    def classify(self, context: object) -> Intent:
        prompt = getattr(context, "prompt", None)
        if not isinstance(prompt, str):
            prompt = ""
        normalized = prompt.lower()
        for rule in self._rules:
            if any(pattern and pattern.lower() in normalized for pattern in rule.patterns):
                return Intent(name=rule.name, confidence=1.0, target=rule.target)
        return Intent(name=self._fallback, confidence=0.0, target=self._default_target)

    def add_rule(self, rule: IntentRule) -> None:
        """Append a rule; later rules only win when earlier ones do not match."""
        self._rules = self._rules + (rule,)

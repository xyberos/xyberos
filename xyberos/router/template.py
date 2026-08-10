"""Template-based responder — tier 0 of the hybrid chain (RFC-0017, M5)."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any, cast

from ..contracts.responder import Responder, Template


class TemplateResponder(Responder):
    """Answer requests by matching patterns to multi-variant templates.

    Tier 0 of the responder chain — the cheapest, fastest path for common
    patterns (greetings, FAQs, well-known intents) with zero model calls.

    Matching is intentionally simple and deterministic:

    * an exact match against the classified intent name is the strongest
      signal, then
    * a case-insensitive substring match against the request prompt.

    When a template matches, a natural-language variant is selected in
    round-robin rotation (avoiding robotic repetition), and metadata values are
    injected into ``{key}`` placeholders so responses can feel personalized.

    A matched template reports :meth:`confidence` equal to its configured
    ``Template.confidence``; the router gates on this via ``threshold``.
    """

    def __init__(
        self,
        templates: Iterable[Template] | None = None,
        *,
        threshold: float = 0.0,
    ) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")
        self._templates: list[Template] = []
        self._threshold = threshold
        self._rotations: dict[str, int] = {}
        if templates:
            self.load(templates)

    @property
    def templates(self) -> tuple[Template, ...]:
        """The registered templates, in match priority order."""
        return tuple(self._templates)

    def load(self, templates: Iterable[Template]) -> None:
        """Register ``templates``; later registrations append."""
        for template in templates:
            if not isinstance(template, Template):  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
                raise TypeError("each template must be a Template")
            if not template.variants:
                raise ValueError("each template must provide at least one variant")
            self._templates.append(template)

    def respond(self, context: object) -> str | None:
        """Return the best matching template variant, or ``None`` to escalate."""
        intent_name = self._intent_name(context)
        text = self._text(context)
        best: Template | None = None
        best_confidence = self._threshold  # below the gate -> escalate
        for template in self._templates:
            match = self._match(template, text, intent_name)
            if match is None:
                continue
            if match > best_confidence:
                best = template
                best_confidence = match
        if best is None:
            return None
        variant = self._pick_variant(best)
        return self._inject_context(variant, context)

    def confidence(self, context: object) -> float:
        """Return the confidence of the best matching template, or ``0.0``."""
        intent_name = self._intent_name(context)
        text = self._text(context)
        best = 0.0
        for template in self._templates:
            match = self._match(template, text, intent_name)
            if match is not None and match > best:
                best = match
        return best

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #

    @staticmethod
    def _intent_name(context: object) -> str | None:
        intent = getattr(context, "intent", None)
        name = getattr(intent, "name", None)
        return name if isinstance(name, str) and name else None

    @staticmethod
    def _text(context: object) -> str:
        prompt = getattr(context, "prompt", None)
        return prompt if isinstance(prompt, str) else ""

    @classmethod
    def _match(cls, template: Template, text: str, intent_name: str | None) -> float | None:
        """Return match confidence for ``template``, or ``None`` if it doesn't match."""
        # Exact intent-name match is the strongest, most reliable signal.
        if intent_name is not None and template.pattern == intent_name:
            return template.confidence
        # Otherwise a case-insensitive regex (or literal) match on the prompt.
        if template.pattern and cls._pattern_matches(template.pattern, text):
            return template.confidence
        return None

    @staticmethod
    def _pattern_matches(pattern: str, text: str) -> bool:
        """Case-insensitive regex match; falls back to a literal substring match."""
        try:
            return re.search(pattern, text, re.IGNORECASE) is not None
        except re.error:
            return pattern.lower() in text.lower()

    def _pick_variant(self, template: Template) -> str:
        """Select the next variant in round-robin rotation for this pattern."""
        key = template.pattern
        index = self._rotations.get(key, 0) % len(template.variants)
        self._rotations[key] = index + 1
        return template.variants[index]

    @staticmethod
    def _inject_context(variant: str, context: object) -> str:
        """Replace ``{key}`` placeholders with values from ``context.metadata``."""
        if "{" not in variant:
            return variant
        metadata = getattr(context, "metadata", None)
        if not isinstance(metadata, dict):
            return variant
        metadata_dict = cast(dict[str, Any], metadata)
        for key, value in metadata_dict.items():
            placeholder = "{" + str(key) + "}"
            if placeholder in variant:
                variant = variant.replace(placeholder, str(value))
        return variant

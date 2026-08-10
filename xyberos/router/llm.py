"""LLM-based responder — tiers 6-7 of the hybrid chain (RFC-0017)."""

from __future__ import annotations

from typing import Any

from ..contracts.responder import Responder


class LLMResponder(Responder):
    """Wrap an :class:`~contracts.llm.LLMProvider` as the final answering tier.

    Uses the enriched prompt (memory/knowledge/plan context) when the Brain has
    stored it on ``context.metadata["enriched_prompt"]``, otherwise the raw
    prompt. The LLM is the strongest tier, so it always answers — this makes it
    the natural terminal tier before the chain's fallback.
    """

    def __init__(self, llm: Any) -> None:
        self._llm = llm

    @property
    def llm(self) -> Any:
        """The wrapped LLM provider."""
        return self._llm

    def respond(self, context: object) -> Any | None:
        """Generate from the (enriched) prompt."""
        prompt = self._prompt(context)
        if prompt is None:
            return None
        return self._llm.generate(prompt)

    def confidence(self, context: object) -> float:
        """The LLM is the strongest tier — always confident."""
        return 1.0

    @staticmethod
    def _prompt(context: object) -> str | None:
        """Prefer the Brain's enriched prompt, falling back to the raw prompt."""
        enriched = getattr(context, "enriched_prompt", None)
        if isinstance(enriched, str) and enriched:
            return enriched
        prompt = getattr(context, "prompt", None)
        return prompt if isinstance(prompt, str) and prompt else None

"""Grounding-checked responder wrapper (RFC-0018, M12)."""

from __future__ import annotations

from typing import Any

from ..contracts.responder import Responder


class GroundingResponder(Responder):
    """Wrap a responder to verify its answer against reference knowledge.

    Delegates :meth:`respond`; if the answer fails the grounding check, returns
    ``None`` so the chain escalates rather than committing an unsupported or
    hallucinated response (RFC-0018, M12).

    The reference knowledge is taken from ``context.enriched_prompt`` (which
    the Brain populates with memory/knowledge/plan sections) when present,
    otherwise from ``context.prompt``.
    """

    def __init__(self, responder: Responder, checker: Any) -> None:
        if not isinstance(responder, Responder):  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
            raise TypeError("responder must implement the Responder contract")
        if not callable(getattr(checker, "verify", None)):
            raise TypeError("checker must expose verify(response, reference)")
        self._responder = responder
        self._checker = checker

    @property
    def responder(self) -> Responder:
        """The wrapped responder."""
        return self._responder

    def respond(self, context: object) -> Any | None:
        """Return the grounded answer, or ``None`` to escalate."""
        answer = self._responder.respond(context)
        if answer is None:
            return None
        reference = self._reference(context)
        result = self._checker.verify(str(answer), reference)
        metadata = getattr(context, "metadata", None)
        if isinstance(metadata, dict):
            metadata["grounding"] = {
                "grounded": result.grounded,
                "confidence": result.confidence,
                "reason": result.reason,
            }
        if not result.grounded:
            return None
        return answer

    def confidence(self, context: object) -> float:
        """Delegate confidence to the wrapped responder."""
        return self._responder.confidence(context)

    @staticmethod
    def _reference(context: object) -> str:
        enriched = getattr(context, "enriched_prompt", None)
        if isinstance(enriched, str) and enriched:
            return enriched
        prompt = getattr(context, "prompt", None)
        return prompt if isinstance(prompt, str) else ""

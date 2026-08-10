"""Response grounding: verify claims against reference knowledge (RFC-0018, M12)."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from ..llm import LLMProvider, structured

_STOPWORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "of", "to", "in", "on", "for",
        "with", "is", "are", "was", "were", "be", "been", "i", "you", "we",
        "they", "he", "she", "it", "this", "that", "these", "those", "my",
        "your", "our", "their", "from", "at", "by", "as", "not", "no", "yes",
        "do", "does", "did", "will", "can", "could", "would", "should", "have",
        "has", "had", "what", "which", "who", "whom", "how", "when", "where",
        "there", "here", "if", "then", "than", "so", "about", "please", "etc",
    }
)

_WORD_RE = re.compile(r"[a-z0-9]+")

# A checker returns {"grounded": bool, "confidence": float, "reason": str}.
Checker = Callable[[str, str], dict[str, Any]]


@dataclass(frozen=True)
class GroundingResult:
    """The outcome of a grounding check."""

    grounded: bool
    confidence: float  # 0.0..1.0 — how well-supported the response is
    reason: str = ""


class GroundingCheck:
    """Verify a response against reference knowledge.

    Defaults to a deterministic, LLM-free term-coverage check: the response's
    content words that appear in the reference divided by its total content
    words. An LLM ``checker`` (or ``llm=``) can be supplied for stronger,
    semantic verification (RFC-0018, M12).
    """

    def __init__(
        self,
        checker: Checker | None = None,
        *,
        llm: LLMProvider | None = None,
        coverage_threshold: float = 0.5,
    ) -> None:
        if not 0.0 <= coverage_threshold <= 1.0:
            raise ValueError("coverage_threshold must be between 0.0 and 1.0")
        if checker is not None and not callable(checker):
            raise TypeError("checker must be callable")
        self._llm = llm
        if checker is not None:
            self._checker = checker
        elif llm is not None:
            self._checker = self._llm_check
        else:
            self._checker = self._coverage_check
        self._coverage_threshold = coverage_threshold

    def verify(self, response: str, reference: str) -> GroundingResult:
        """Verify ``response`` against ``reference`` knowledge text."""
        if not isinstance(response, str) or not response:  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
            return GroundingResult(grounded=False, confidence=0.0, reason="empty response")
        if not reference:
            return GroundingResult(grounded=False, confidence=0.0, reason="no reference knowledge")
        try:
            data = self._checker(response, reference)
        except Exception:
            return GroundingResult(grounded=False, confidence=0.0, reason="checker failed")
        if not isinstance(data, dict):  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
            return GroundingResult(grounded=False, confidence=0.0, reason="invalid checker result")
        grounded = bool(data.get("grounded", False))
        try:
            confidence = float(data.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        return GroundingResult(
            grounded=grounded,
            confidence=max(0.0, min(1.0, confidence)),
            reason=str(data.get("reason", "")),
        )

    def _coverage_check(self, response: str, reference: str) -> dict[str, Any]:
        """Deterministic LLM-free grounding via content-term coverage."""
        response_terms = _content_terms(response)
        reference_terms = _content_terms(reference)
        if not response_terms:
            return {"grounded": True, "confidence": 1.0, "reason": "no claim terms"}
        reference_set = set(reference_terms)
        covered = sum(1 for term in response_terms if term in reference_set)
        coverage = covered / len(response_terms)
        return {
            "grounded": coverage >= self._coverage_threshold,
            "confidence": coverage,
            "reason": f"term coverage {coverage:.2f}",
        }

    def _llm_check(self, response: str, reference: str) -> dict[str, Any]:
        """LLM-based grounding verdict."""
        prompt = (
            "Verify whether the RESPONSE is fully supported by the REFERENCE "
            "knowledge. Respond ONLY with JSON: "
            '{"grounded": bool, "confidence": 0.0-1.0, "reason": "short text"}.\n\n'
            f"REFERENCE:\n{reference}\n\nRESPONSE:\n{response}"
        )
        data = structured(cast(LLMProvider, self._llm), prompt)
        return cast(dict[str, Any], data if isinstance(data, dict) else {})


def _content_terms(text: str) -> list[str]:
    """Lowercased content tokens, excluding stopwords and single chars."""
    return [
        token
        for token in _WORD_RE.findall(text.lower())
        if token not in _STOPWORDS and len(token) > 1
    ]

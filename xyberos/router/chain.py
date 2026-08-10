"""The confidence-gated responder chain (RFC-0017, M4)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, cast

from ..contracts.responder import Responder
from ..contracts.router import Router
from ..events import EventBus
from ..events.names import DEGRADED, ESCALATED, RESPONDER_HIT
from .llm import LLMResponder

# A responder can be passed as a plain Responder or as a (name, responder)
# pair so the chain can attribute hits/escalations and apply per-tier gates.
NamedResponder = tuple[str, Responder]

# Tier names treated as model-generation tiers for the cheap-first pass.
_LLM_TIER_NAMES = ("llm", "local", "cloud")


class ResponderChain(Router):
    """Run responders in priority order; stop at the first confident hit.

    Each responder is asked to answer the request. The chain escalates when a
    responder:

    * returns ``None`` (declines), or
    * reports a confidence below its per-tier (or the global) gate, or
    * raises an exception (a failing tier must not fail the request).

    When every responder declines, the chain runs the configured ``fallback``
    — a final :class:`Responder`, a ``context -> answer`` callable, or ``None``
    to return ``None`` so the caller (e.g. the Brain) falls through to its
    normal LLM path. Returning ``None`` on a full miss means the router is a
    pure optimization layer: it never degrades behavior below the LLM baseline
    unless a fallback is explicitly configured.

    Every tier hit and escalation is emitted on the optional ``events`` bus
    (``brain.responder_hit`` / ``brain.escalated`` / ``brain.degraded``) so
    per-tier hit-rates are measurable (RFC-0017, G4).
    """

    def __init__(
        self,
        responders: Sequence[NamedResponder | Responder] | None = None,
        *,
        threshold: float = 0.0,
        per_tier_threshold: Mapping[str, float] | None = None,
        fallback: Responder | Callable[[object], Any] | None = None,
        events: EventBus | None = None,
    ) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")
        self._responders: tuple[NamedResponder, ...] = tuple(
            self._coerce(index, responder) for index, responder in enumerate(responders or ())
        )
        self._threshold = threshold
        self._per_tier_threshold = dict(per_tier_threshold or {})
        self._fallback = fallback
        self._events = events

    @property
    def responders(self) -> tuple[NamedResponder, ...]:
        """The ordered ``(name, responder)`` chain."""
        return self._responders

    @property
    def fallback(self) -> Responder | Callable[[object], Any] | None:
        """The configured fallback policy."""
        return self._fallback

    @property
    def is_llm_free(self) -> bool:
        """Whether the chain has no model-generation tier.

        True when no responder is an :class:`~router.LLMResponder` and no tier
        is named ``llm``/``local``/``cloud``. Lets the Brain default the
        ``cheap_first`` fast path on for fully LLM-free chains (RFC-0017).
        """
        return all(
            not isinstance(responder, LLMResponder) and name not in _LLM_TIER_NAMES
            for name, responder in self._responders
        )

    def attach_events(self, events: EventBus | None) -> None:
        """Attach an event bus after construction (e.g. from the app facade).

        Lets a chain built before the app exists emit ``responder_hit`` /
        ``escalated`` / ``degraded`` events once the app's bus is available
        (RFC-0017, M11 warm-up).
        """
        self._events = events

    def get_threshold(self, name: str | None = None) -> float:
        """Return the effective confidence gate for ``name`` (or the global gate)."""
        if name is None:
            return self._threshold
        return self._per_tier_threshold.get(name, self._threshold)

    def set_threshold(self, name: str, value: float) -> None:
        """Set the per-tier confidence gate for ``name`` (RFC-0017, M14 tuning)."""
        if not 0.0 <= value <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")
        self._per_tier_threshold[name] = value

    def respond(self, context: object) -> Any:
        """Answer ``context`` with the first confident tier, or run the fallback."""
        for name, responder in self._responders:
            answer = self._try_tier(name, responder, context)
            if answer is not None:
                return answer
        return self._run_fallback(context)

    def respond_cheap(self, context: object) -> Any | None:
        """Run only the LLM-free tiers; return ``None`` if none answer.

        Enables the Brain's ``brain.cheap_first`` optimization: cheap tiers are
        consulted before intent/planner LLM calls are spent, so cache/knowledge/
        memory/template/tool answers cost zero LLM calls (RFC-0017). The
        fallback is NOT run — ``None`` means "do the full pass" (RFC-0017).
        """
        for name, responder in self._responders:
            if isinstance(responder, LLMResponder) or name in _LLM_TIER_NAMES:
                break
            answer = self._try_tier(name, responder, context)
            if answer is not None:
                return answer
        return None

    def _try_tier(self, name: str, responder: Responder, context: object) -> Any | None:
        """Ask one tier; return its answer, or ``None`` to keep escalating."""
        gate = self._effective_threshold(name)
        confidence = self._confidence(responder, context)
        if confidence < gate:
            self._emit_escalation(name, context, confidence, "below gate")
            return None
        try:
            answer = responder.respond(context)
        except Exception as exc:  # a failing tier escalates, never breaks the chain
            self._record_error(context, name, exc)
            self._emit_escalation(name, context, confidence, "raised")
            return None
        if answer is None:
            self._emit_escalation(name, context, confidence, "declined")
            return None
        self._record_hit(context, name, confidence)
        self._emit_hit(name, context, confidence, answer)
        return answer

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #

    @staticmethod
    def _coerce(index: int, entry: NamedResponder | Responder) -> NamedResponder:
        """Normalize a responder entry to a ``(name, responder)`` pair."""
        if isinstance(entry, tuple) and len(entry) == 2 and isinstance(entry[0], str):  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
            return (entry[0], entry[1])
        if not isinstance(entry, Responder):
            raise TypeError("each responder must be a Responder or a (name, Responder) pair")
        return (f"tier{index}", entry)

    def _effective_threshold(self, name: str) -> float:
        """Return the per-tier gate for ``name``, or the global threshold."""
        return self._per_tier_threshold.get(name, self._threshold)

    @staticmethod
    def _confidence(responder: Responder, context: object) -> float:
        """Read a responder's confidence gate, defaulting to confident."""
        try:
            value = responder.confidence(context)
        except Exception:
            return 0.0
        if value is None:  # type: ignore[comparison-overlap]  # defensive runtime guard
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _run_fallback(self, context: object) -> Any:
        """Run the configured fallback, or return ``None`` to let the caller decide."""
        self._emit(DEGRADED, context=context)
        if self._fallback is None:
            return None
        if isinstance(self._fallback, Responder):
            return self._fallback.respond(context)
        return self._fallback(context)

    def _emit_hit(self, name: str, context: object, confidence: float, answer: Any) -> None:
        self._emit(RESPONDER_HIT, context=context, tier=name, confidence=confidence, response=answer)

    def _emit_escalation(self, name: str, context: object, confidence: float, reason: str) -> None:
        self._emit(ESCALATED, context=context, tier=name, confidence=confidence, reason=reason)

    def _emit(self, name: str, *, context: object | None = None, **data: Any) -> None:
        if self._events is not None:
            self._events.emit(name, context=context, **data)

    @staticmethod
    def _record_hit(context: object, name: str, confidence: float) -> None:
        """Stamp the winning tier onto the context for telemetry/learning."""
        metadata = getattr(context, "metadata", None)
        if isinstance(metadata, dict):
            metadata["responder"] = name
            metadata["responder_confidence"] = confidence

    @staticmethod
    def _record_error(context: object, name: str, exc: Exception) -> None:
        metadata = getattr(context, "metadata", None)
        if isinstance(metadata, dict):
            metadata_dict = cast(dict[str, Any], metadata)
            errors = metadata_dict.setdefault("router.errors", [])
            errors.append({"tier": name, "error": repr(exc)})

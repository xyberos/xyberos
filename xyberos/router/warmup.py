"""Warm-up: teach the cache from LLM responses (RFC-0017, M11)."""

from __future__ import annotations

from typing import Any, cast

from ..events import EventBus
from ..events.names import RESPONDER_HIT, RESPONSE_PRODUCED
from .cache import CacheResponder


class CacheTeacher:
    """Teach a :class:`CacheResponder` from LLM-generated responses (warm-up).

    The "teacher loop" that shrinks LLM traffic over time: every LLM-generated
    ``(prompt, response)`` pair is cached, so a similar future request is served
    by the cache instead of the LLM. Learns from both paths:

    * ``brain.response_produced`` — the Brain's direct LLM generation (router
      declined), and
    * ``brain.responder_hit`` with ``tier == "llm"`` — the router's LLM tier.
    """

    def __init__(self, cache: CacheResponder, events: EventBus | None = None) -> None:
        self._cache = cache
        self._taught = 0
        if events is not None:
            events.subscribe(RESPONSE_PRODUCED, self._on_llm_response)
            events.subscribe(RESPONDER_HIT, self._on_responder_hit)

    @property
    def cache(self) -> CacheResponder:
        """The cache being taught."""
        return self._cache

    @property
    def taught(self) -> int:
        """The number of pairs taught so far."""
        return self._taught

    def _on_llm_response(self, event: Any) -> None:
        """Teach from the Brain's direct LLM path."""
        context = getattr(event, "context", None)
        data = cast(dict[str, Any], getattr(event, "data", None) or {})
        prompt = getattr(context, "prompt", None) if context is not None else None
        response = data.get("response")
        self._teach(prompt, response)

    def _on_responder_hit(self, event: Any) -> None:
        """Teach from the router's LLM tier (and only that tier)."""
        data = cast(dict[str, Any], getattr(event, "data", None) or {})
        if data.get("tier") != "llm":
            return
        context = getattr(event, "context", None)
        prompt = getattr(context, "prompt", None) if context is not None else None
        response = data.get("response")
        self._teach(prompt, response)

    def _teach(self, prompt: Any, response: Any) -> None:
        if isinstance(prompt, str) and prompt and isinstance(response, str) and response:
            self._cache.teach(prompt, response)
            self._taught += 1

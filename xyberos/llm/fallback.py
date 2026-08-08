"""Model-level fallback chain (RFC-0017)."""

from __future__ import annotations

from typing import Any

from ..exceptions.provider import ProviderError


class FallbackLLM:
    """Try a primary LLM, then fall back to other providers on failure.

    Duck-typed as an ``LLMProvider`` (``generate``). If the primary raises a
    retryable error (``ProviderError`` by default — outage, rate limit, etc.),
    the next model is tried, and so on. When every model fails, the last error
    is re-raised.

    This is the cloud → local cascade from RFC-0017: a provider outage degrades
    to a local model (e.g. Ollama) instead of failing the request. Only the
    synchronous ``generate`` capability is provided; the Brain's async path uses
    it as a fallback. ``stream``/``agenerate`` variants are future work (partial
    tokens cannot be retracted across models).
    """

    def __init__(
        self,
        primary: Any,
        *fallbacks: Any,
        retry_on: tuple[type[BaseException], ...] | None = None,
    ) -> None:
        models = (primary,) + fallbacks
        for model in models:
            if not callable(getattr(model, "generate", None)):
                raise TypeError("every model must implement generate(prompt)")
        self._models = models
        self._retry_on = retry_on or (ProviderError,)

    @property
    def models(self) -> tuple[Any, ...]:
        """The ordered model chain, primary first."""
        return self._models

    def generate(self, prompt: str) -> str:
        """Generate with the first model that succeeds; re-raise if all fail."""
        last_error: BaseException | None = None
        for model in self._models:
            try:
                response = model.generate(prompt)
            except self._retry_on as exc:
                last_error = exc
                continue
            if not isinstance(response, str):
                raise TypeError("LLM must return a string")
            return response
        assert last_error is not None
        raise last_error

"""Embedding capabilities for language model providers (RFC-0016, Phase 0).

Embeddings are a *duck-typed* LLM capability, exactly like ``stream`` /
``agenerate``: the core :class:`~contracts.llm.LLMProvider` protocol stays
minimal, and providers that can embed simply expose an ``embed(text) ->
Sequence[float]`` method. :class:`EmbeddingLLM` adapts a plain generator plus an
embedder callable, and :class:`HashEmbedder` provides a dependency-free
deterministic embedder for local development and tests.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from hashlib import blake2b
from typing import Any

from ..exceptions.provider import ProviderError
from .llm import EchoLLM, LLMProvider

# An embedder turns text into a fixed-length float vector.
Embedder = Callable[[str], Sequence[float]]


class EmbeddingLLM:
    """Wrap an ``LLMProvider`` and an embedder into one provider.

    Exposes both ``generate`` (delegating to the wrapped LLM) and ``embed``
    (delegating to the embedder). Useful when a model server provides chat and
    embeddings separately.
    """

    def __init__(self, llm: LLMProvider | None = None, *, embedder: Embedder | None = None) -> None:
        if embedder is not None and not callable(embedder):
            raise TypeError("embedder must be callable")
        self._llm = llm or EchoLLM()
        self._embedder = embedder

    def generate(self, prompt: str) -> str:
        """Delegate text generation to the wrapped provider."""
        return self._llm.generate(prompt)

    def embed(self, text: str) -> Sequence[float]:
        """Embed ``text`` with the configured embedder."""
        if self._embedder is None:
            raise ProviderError("no embedder configured; pass embedder= to EmbeddingLLM")
        vector = self._embedder(text)
        if not vector:
            raise ProviderError("embedder returned an empty vector")
        return [float(value) for value in vector]


class HashEmbedder:
    """Deterministic, dependency-free embeddings for local use and tests.

    Hashes ``text`` into a fixed-dimension unit vector using BLAKE2b. Not
    semantically meaningful, but stable and collision-resistant enough for
    examples, fixtures, and development before a real embedding model is wired
    in.
    """

    def __init__(self, dim: int = 64, *, seed: str = "xyberos") -> None:
        if dim <= 0:
            raise ValueError("dim must be a positive integer")
        self._dim = dim
        self._seed = seed

    def __call__(self, text: str) -> list[float]:
        vector = [0.0] * self._dim
        for index in range(self._dim):
            digest = blake2b(f"{self._seed}:{index}:{text}".encode(), digest_size=8).digest()
            vector[index] = int.from_bytes(digest, "big") / 2**64
        norm = sum(value * value for value in vector) ** 0.5
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]


def embed_text(embedder: Any, text: str) -> list[float]:
    """Embed ``text`` using a callable or any object exposing ``embed(text)``.

    Accepts either a plain ``str -> Sequence[float]`` callable (e.g. a
    :class:`HashEmbedder`) or a duck-typed embedder such as an
    :class:`EmbeddingLLM` / ``OpenAIEmbeddingLLM`` with an ``embed`` method.
    Raises :class:`~exceptions.provider.ProviderError` when embedding is not
    possible or returns an empty vector.
    """
    if embedder is None:
        raise ProviderError("an embedder is required to embed text")
    if callable(embedder):
        vector = embedder(text)
    else:
        embed = getattr(embedder, "embed", None)
        if not callable(embed):
            raise ProviderError("embedder must be callable or expose embed(text)")
        vector = embed(text)
    if not vector:
        raise ProviderError("embedder returned an empty vector")
    return [float(value) for value in vector]


__all__ = ["Embedder", "EmbeddingLLM", "HashEmbedder", "embed_text"]

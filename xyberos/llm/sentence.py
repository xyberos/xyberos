"""Optional semantic embedder (requires ``xyberos[embeddings]``)."""

from __future__ import annotations

from typing import Any

from .adapters import require


class SentenceTransformerEmbedder:
    """A real semantic embedder backed by ``sentence-transformers``.

    Unlocks paraphrase/semantic matching that the dependency-free
    :class:`~llm.HashEmbedder` cannot do. The model is imported lazily on first
    use; a clear :class:`~exceptions.provider.ProviderError` is raised when
    ``sentence-transformers`` is not installed (``pip install xyberos[embeddings]``).

    Usable anywhere an embedder is expected — e.g.
    ``create_semantic_app(embedder=SentenceTransformerEmbedder("all-MiniLM-L6-v2"))``.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        if not isinstance(model_name, str) or not model_name.strip():  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
            raise ValueError("model_name must be a non-empty string")
        self._model_name = model_name
        self._model: Any | None = None

    @property
    def model_name(self) -> str:
        """The configured sentence-transformers model name."""
        return self._model_name

    def __call__(self, text: str) -> list[float]:
        """Embed ``text`` into a normalized float vector."""
        model = self._load()
        vector = model.encode(text)
        values = [float(value) for value in vector]
        norm = sum(value * value for value in values) ** 0.5
        if norm == 0.0:
            return values
        return [value / norm for value in values]

    def _load(self) -> Any:
        if self._model is None:
            module = require("sentence_transformers", "sentence-transformers")
            self._model = module.SentenceTransformer(self._model_name)
        return self._model

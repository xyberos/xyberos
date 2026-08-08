"""Optional offline training / distillation (RFC-0016, Phase 3).

Phase 3 keeps the core dependency-free: ``embedding`` artifacts are plain JSON,
and ``sklearn`` artifacts use scikit-learn/joblib only when installed
(``pip install xyberos[train]``). Fine-tuned engines still implement the same
:class:`~contracts.intent.IntentEngine` contract, so nothing in the core changes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..contracts.experience import ExperienceStore
from ..contracts.intent import IntentEngine
from ..intent import EmbeddingIntentEngine
from ..learning.filters import promote_successful
from ..vector import CosineVectorStore

__all__ = ["Trainer", "engine_from_config", "export_dataset"]


def export_dataset(
    experience: ExperienceStore,
    *,
    field: str = "intent",
    min_feedback: float = 0.5,
    limit: int = 500,
) -> list[tuple[str, str]]:
    """Export successful episodes as ``(prompt, label)`` rows for training.

    ``field`` selects the label: ``"intent"`` uses the classified intent name,
    ``"plan"`` uses the JSON-encoded plan, or any other string episode attribute.
    """
    episodes = promote_successful(experience, min_feedback=min_feedback, limit=limit)
    rows: list[tuple[str, str]] = []
    for episode in episodes:
        label = _label(episode, field)
        if label is not None:
            rows.append((episode.prompt, label))
    return rows


def _label(episode: Any, field: str) -> str | None:
    if field == "intent":
        return episode.intent.name if episode.intent is not None else None
    if field == "plan":
        if episode.plan is None:
            return None
        if isinstance(episode.plan, str):
            return episode.plan
        return json.dumps(episode.plan, default=str)
    value = getattr(episode, field, None)
    return value if isinstance(value, str) else None


class Trainer:
    """Turn a ``(prompt, label)`` dataset into a trainable intent engine.

    ``train_intent_embedding`` distills the dataset into an embedding-based
    engine with no dependencies; ``train_intent_sklearn`` fits a scikit-learn
    classifier (requires ``xyberos[train]``). ``save``/``load`` implement the
    artifact registry so trained engines persist and reload behind the same
    :class:`~contracts.intent.IntentEngine` contract.
    """

    def __init__(self, dataset: list[tuple[str, str]]) -> None:
        if not dataset:
            raise ValueError("dataset must not be empty")
        self._dataset = list(dataset)

    @property
    def dataset(self) -> list[tuple[str, str]]:
        """A copy of the training rows ``(prompt, label)``."""
        return list(self._dataset)

    def train_intent_embedding(
        self,
        embedder: Any,
        *,
        store: Any | None = None,
        namespace: str = "intents",
    ) -> EmbeddingIntentEngine:
        """Distill the dataset into an embedding-based intent engine (no deps)."""
        engine = EmbeddingIntentEngine(
            store or CosineVectorStore(),
            embedder=embedder,
            namespace=namespace,
        )
        for prompt, label in self._dataset:
            engine.learn(label, prompt)
        return engine

    def train_intent_sklearn(self, embedder: Any) -> IntentEngine:
        """Train a scikit-learn intent classifier (optional ``xyberos[train]``)."""
        from .sklearn import SkLearnIntentEngine

        return SkLearnIntentEngine.from_data(self._dataset, embedder)

    def save(self, path: str, *, algorithm: str = "embedding", embedder: Any | None = None) -> None:
        """Persist the trained artifact (embedding JSON or sklearn model)."""
        if algorithm == "embedding":
            payload = {"algorithm": "embedding", "examples": self._dataset}
            Path(path).write_text(json.dumps(payload), encoding="utf-8")
        elif algorithm == "sklearn":
            if embedder is None:
                raise ValueError("embedder is required to save a sklearn artifact")
            from .sklearn import _dump_engine

            _dump_engine(self.train_intent_sklearn(embedder), path)
        else:
            raise ValueError(f"unknown algorithm: {algorithm!r}")

    @classmethod
    def load(
        cls,
        path: str,
        *,
        embedder: Any | None = None,
        algorithm: str | None = None,
    ) -> IntentEngine:
        """Rebuild an intent engine from a saved artifact."""
        algorithm = algorithm or _detect_algorithm(path)
        if algorithm == "embedding":
            if embedder is None:
                raise ValueError("embedder is required to load an embedding artifact")
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            examples = payload.get("examples", []) if isinstance(payload, dict) else []
            rows = [(str(prompt), str(label)) for prompt, label in examples]
            return cls(rows).train_intent_embedding(embedder)
        if algorithm == "sklearn":
            from .sklearn import _load_engine

            return _load_engine(path)
        raise ValueError(f"unknown algorithm: {algorithm!r}")


def engine_from_config(config: Any, *, embedder: Any | None = None) -> IntentEngine | None:
    """Load an intent engine from the ``learning.model`` / ``learning.algorithm`` config keys."""
    get = config.get if hasattr(config, "get") else (lambda key, default=None: default)
    model = get("learning.model")
    if not model:
        return None
    return Trainer.load(model, embedder=embedder, algorithm=get("learning.algorithm"))


def _detect_algorithm(path: str) -> str:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return "sklearn"
    if isinstance(payload, dict):
        return payload.get("algorithm", "embedding")
    return "embedding"

"""Optional scikit-learn intent classifier (RFC-0016, Phase 3).

Requires ``xyberos[train]`` (scikit-learn + joblib). The fitted classifier is
wrapped in the standard :class:`~contracts.intent.IntentEngine` contract so it
drops into ``create_app(intent=...)`` exactly like any other engine.
"""

from __future__ import annotations

from typing import Any

from ..contracts.intent import Intent, IntentEngine
from ..llm.adapters import _require
from ..llm.embeddings import embed_text

__all__ = ["SkLearnIntentEngine"]


def _sklearn() -> Any:
    return _require("sklearn")


class SkLearnIntentEngine(IntentEngine):
    """A trained intent classifier backed by scikit-learn (optional dependency).

    Uses an embedder to vectorize prompts and a logistic-regression classifier
    fit on a ``(prompt, intent)`` dataset. Classification returns the predicted
    label with its probability as the confidence.
    """

    def __init__(self, classifier: Any, embedder: Any) -> None:
        self._classifier = classifier
        self._embedder = embedder

    @classmethod
    def from_data(cls, dataset: list[tuple[str, str]], embedder: Any) -> SkLearnIntentEngine:
        """Fit a classifier on ``(prompt, label)`` rows."""
        sklearn = _sklearn()
        features = [embed_text(embedder, prompt) for prompt, _ in dataset]
        labels = [label for _, label in dataset]
        classifier = sklearn.linear_model.LogisticRegression(max_iter=1000)
        classifier.fit(features, labels)
        return cls(classifier, embedder)

    def classify(self, context: object) -> Intent:
        prompt = getattr(context, "prompt", None)
        if not isinstance(prompt, str) or not prompt:
            return Intent(name="general", confidence=0.0)
        vector = embed_text(self._embedder, prompt)
        name = str(self._classifier.predict([vector])[0])
        return Intent(name=name, confidence=_confidence(self._classifier, vector, name))


def _confidence(classifier: Any, vector: list[float], name: str) -> float:
    predict_proba = getattr(classifier, "predict_proba", None)
    classes = getattr(classifier, "classes_", None)
    if callable(predict_proba) and classes is not None:
        try:
            probabilities = predict_proba([vector])[0]
            index = list(classes).index(name)
            return float(probabilities[index])
        except (ValueError, TypeError):
            return 1.0
    return 1.0


def _dump_engine(engine: Any, path: str) -> None:
    joblib = _require("joblib")
    joblib.dump(engine, path)


def _load_engine(path: str) -> Any:
    joblib = _require("joblib")
    return joblib.load(path)

"""Score → confidence calibration (RFC-0018, M13)."""

from __future__ import annotations

import math
from collections.abc import Sequence


class ScoreCalibrator:
    """Map raw retrieval scores to calibrated confidence via Platt scaling.

    Fits ``p(relevant | score) = sigmoid(A * score + B)`` from labeled
    ``(score, is_relevant)`` pairs using gradient descent on the logistic
    likelihood — dependency-free (RFC-0018, M13). ``A`` is constrained to be
    non-negative so confidence increases monotonically with the raw score.

    Before fitting, :meth:`calibrate` is the identity (score clamped to
    ``[0, 1]``). After fitting, raw scores from different embedders map to
    comparable confidence values, so a single router threshold is meaningful
    across embedders (e.g. the default ``HashEmbedder``'s biased ~0.6-0.8
    unrelated scores vs a real embedder's ~0.2-0.4).
    """

    def __init__(self, *, learning_rate: float = 0.1, iterations: int = 500) -> None:
        self._a = 1.0
        self._b = 0.0
        self._learning_rate = learning_rate
        self._iterations = iterations
        self._fitted = False

    @property
    def is_fitted(self) -> bool:
        """Whether :meth:`fit` has been called."""
        return self._fitted

    @property
    def coefficients(self) -> tuple[float, float]:
        """The fitted ``(A, B)`` logistic coefficients."""
        return (self._a, self._b)

    def fit(self, scores: Sequence[float], labels: Sequence[bool]) -> "ScoreCalibrator":
        """Fit ``A``/``B`` from aligned ``(score, is_relevant)`` pairs."""
        if len(scores) != len(labels):
            raise ValueError("scores and labels must be the same length")
        if not scores:
            raise ValueError("need at least one (score, label) pair")

        a, b = self._a, self._b
        n = len(scores)
        for _ in range(self._iterations):
            grad_a = 0.0
            grad_b = 0.0
            for score, label in zip(scores, labels):
                z = _clamp_z(a * float(score) + b)
                p = 1.0 / (1.0 + math.exp(-z))
                residual = p - (1.0 if label else 0.0)
                grad_a += residual * float(score)
                grad_b += residual
            a -= self._learning_rate * (grad_a / n)
            b -= self._learning_rate * (grad_b / n)
            a = max(a, 0.0)  # enforce monotonic increasing confidence

        self._a, self._b = a, b
        self._fitted = True
        return self

    def calibrate(self, score: float) -> float:
        """Return calibrated confidence in ``[0, 1]`` for a raw ``score``."""
        if not self._fitted:
            return max(0.0, min(1.0, float(score)))
        z = _clamp_z(self._a * float(score) + self._b)
        return 1.0 / (1.0 + math.exp(-z))

    def __call__(self, score: float) -> float:
        """Alias for :meth:`calibrate`."""
        return self.calibrate(score)


def _clamp_z(z: float) -> float:
    """Clamp a logit to avoid overflow/underflow in ``exp``."""
    return max(-50.0, min(50.0, z))

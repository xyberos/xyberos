"""Confidence-calibrated responder wrapper (RFC-0018, M13)."""

from __future__ import annotations

from typing import Any

from ..contracts.responder import Responder


class CalibratedResponder(Responder):
    """Wrap any responder to calibrate its confidence before the router gates.

    Delegates :meth:`respond` unchanged, but maps the inner responder's raw
    :meth:`confidence` through a :class:`~utils.calibration.ScoreCalibrator`.
    This lets a single router threshold be meaningful across embedders — e.g.
    the default ``HashEmbedder``'s biased ~0.6-0.8 unrelated scores vs a real
    embedder's ~0.2-0.4 — without changing responder internals (RFC-0018, M13).
    """

    def __init__(self, responder: Responder, calibrator: Any) -> None:
        if not isinstance(responder, Responder):  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
            raise TypeError("responder must implement the Responder contract")
        if not callable(getattr(calibrator, "calibrate", None)):
            raise TypeError("calibrator must expose calibrate(score) -> float")
        self._responder = responder
        self._calibrator = calibrator

    @property
    def responder(self) -> Responder:
        """The wrapped responder."""
        return self._responder

    def respond(self, context: object) -> Any | None:
        """Delegate to the wrapped responder unchanged."""
        return self._responder.respond(context)

    def confidence(self, context: object) -> float:
        """The calibrated confidence of the wrapped responder."""
        raw = self._responder.confidence(context)
        try:
            return float(self._calibrator.calibrate(raw))
        except (TypeError, ValueError):
            return 0.0

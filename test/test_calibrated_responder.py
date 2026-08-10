import pytest

from xyberos.contracts import Responder
from xyberos.router import CalibratedResponder, ResponderChain
from xyberos.runtime.context import CognitiveContext
from xyberos.utils import ScoreCalibrator


class StaticResponder(Responder):
    """A Responder with a controllable raw confidence."""

    def __init__(self, answer, confidence):
        self._answer = answer
        self._confidence = confidence

    def respond(self, context):
        return self._answer

    def confidence(self, context):
        return self._confidence


def test_calibrated_responder_delegates_response():
    inner = StaticResponder("answer", 0.7)
    wrapped = CalibratedResponder(inner, ScoreCalibrator())

    assert wrapped.respond(CognitiveContext("x")) == "answer"


def test_calibrated_responder_calibrates_confidence():
    # Fit: raw 0.7 is irrelevant, raw 1.0 is relevant.
    calibrator = ScoreCalibrator().fit([0.7, 1.0], [False, True])
    wrapped = CalibratedResponder(StaticResponder("a", 1.0), calibrator)

    assert wrapped.confidence(CognitiveContext("x")) > 0.5


def test_calibrated_responder_identity_before_fit():
    wrapped = CalibratedResponder(StaticResponder("a", 0.7), ScoreCalibrator())
    assert wrapped.confidence(CognitiveContext("x")) == 0.7


def test_calibrated_responder_rejects_bad_calibrator():
    with pytest.raises(TypeError, match="calibrate"):
        CalibratedResponder(StaticResponder("a", 0.5), "not-a-calibrator")


def test_calibrated_responder_in_chain_gates_on_calibrated_confidence():
    calibrator = ScoreCalibrator().fit([0.7, 1.0], [False, True])
    low = CalibratedResponder(StaticResponder("low", 0.7), calibrator)
    high = CalibratedResponder(StaticResponder("high", 1.0), calibrator)

    chain = ResponderChain([("low", low), ("high", high)], threshold=0.5)

    assert chain.respond(CognitiveContext("x")) == "high"

import math

from xyberos.utils import ScoreCalibrator


def test_calibrator_identity_before_fit():
    calibrator = ScoreCalibrator()
    assert not calibrator.is_fitted
    assert calibrator.calibrate(0.7) == 0.7
    assert calibrator.calibrate(1.2) == 1.0  # clamped
    assert calibrator.calibrate(-0.1) == 0.0  # clamped


def test_calibrator_fit_separates_relevant_from_irrelevant():
    # Unrelated HashEmbedder pairs cluster ~0.6-0.8; identical pairs ~1.0.
    scores = [0.62, 0.70, 0.78, 0.66, 1.0, 1.0, 0.99, 1.0]
    labels = [False, False, False, False, True, True, True, True]
    calibrator = ScoreCalibrator().fit(scores, labels)

    assert calibrator.is_fitted
    # After calibration, low raw scores map well below high raw scores.
    assert calibrator.calibrate(0.65) < calibrator.calibrate(1.0)
    assert calibrator.calibrate(1.0) > 0.5
    assert calibrator.calibrate(0.65) < 0.5


def test_calibrator_is_monotonic_increasing():
    scores = [0.5, 0.7, 0.9, 1.0, 1.0, 1.0, 0.8, 1.0]
    labels = [False, False, True, True, True, True, False, True]
    calibrator = ScoreCalibrator().fit(scores, labels)

    previous = -1.0
    for raw in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        value = calibrator.calibrate(raw)
        assert value >= previous
        assert 0.0 <= value <= 1.0
        previous = value


def test_calibrator_returns_confidence_in_unit_interval():
    scores = [0.6, 0.7, 0.8, 0.9, 1.0]
    labels = [False, False, True, True, True]
    calibrator = ScoreCalibrator().fit(scores, labels)

    for raw in (-5.0, 0.0, 0.5, 1.0, 5.0):
        value = calibrator.calibrate(raw)
        assert 0.0 <= value <= 1.0


def test_calibrator_rejects_mismatched_inputs():
    with __import__("pytest").raises(ValueError, match="same length"):
        ScoreCalibrator().fit([0.5], [True, False])
    with __import__("pytest").raises(ValueError, match="at least one"):
        ScoreCalibrator().fit([], [])


def test_calibrator_callable_alias():
    calibrator = ScoreCalibrator().fit([0.5, 1.0], [False, True])
    assert calibrator(0.5) == calibrator.calibrate(0.5)

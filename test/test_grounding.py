import json

from xyberos.llm import CallableLLM
from xyberos.utils import GroundingCheck


def test_grounding_check_grounded_when_terms_overlap():
    checker = GroundingCheck()
    result = checker.verify(
        "Returns accepted within 30 days",
        "return policy: Returns accepted within 30 days with receipt",
    )
    assert result.grounded
    assert result.confidence > 0.5


def test_grounding_check_ungrounded_when_no_overlap():
    checker = GroundingCheck()
    result = checker.verify(
        "Free worldwide shipping on all orders",
        "return policy: Returns accepted within 30 days with receipt",
    )
    assert not result.grounded


def test_grounding_check_rejects_empty_response():
    result = GroundingCheck().verify("", "some knowledge")
    assert not result.grounded
    assert result.reason == "empty response"


def test_grounding_check_rejects_empty_reference():
    result = GroundingCheck().verify("an answer", "")
    assert not result.grounded
    assert result.reason == "no reference knowledge"


def test_grounding_check_llm_mode():
    checker = GroundingCheck(llm=CallableLLM(
        lambda prompt: json.dumps({"grounded": True, "confidence": 0.9, "reason": "ok"})
    ))
    result = checker.verify("some answer", "some reference")
    assert result.grounded
    assert result.confidence == 0.9


def test_grounding_check_llm_mode_unparseable_defaults_ungrounded():
    checker = GroundingCheck(llm=CallableLLM(lambda prompt: "not json"))
    result = checker.verify("some answer", "some reference")
    assert not result.grounded
    assert result.confidence == 0.0


def test_grounding_check_custom_checker():
    checker = GroundingCheck(lambda response, reference: {"grounded": True, "confidence": 1.0, "reason": "custom"})
    result = checker.verify("x", "y")
    assert result.grounded
    assert result.confidence == 1.0


def test_grounding_check_rejects_invalid_threshold():
    import pytest

    with pytest.raises(ValueError, match="coverage_threshold"):
        GroundingCheck(coverage_threshold=1.5)

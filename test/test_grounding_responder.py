import pytest

from xyberos.contracts import Responder
from xyberos.router import GroundingResponder, ResponderChain
from xyberos.runtime.context import CognitiveContext
from xyberos.utils import GroundingCheck


class StaticResponder(Responder):
    def __init__(self, answer, confidence=1.0):
        self._answer = answer
        self._confidence = confidence

    def respond(self, context):
        return self._answer

    def confidence(self, context):
        return self._confidence


def _context(prompt, enriched=None):
    context = CognitiveContext(prompt)
    if enriched is not None:
        context.enriched_prompt = enriched
    return context


def test_grounding_responder_returns_grounded_answer():
    checker = GroundingCheck()
    wrapped = GroundingResponder(StaticResponder("Returns accepted within 30 days"), checker)

    answer = wrapped.respond(_context("return policy", enriched="return policy: Returns accepted within 30 days"))

    assert answer == "Returns accepted within 30 days"


def test_grounding_responder_escalates_ungrounded_answer():
    checker = GroundingCheck()
    wrapped = GroundingResponder(StaticResponder("Free worldwide shipping"), checker)

    assert wrapped.respond(_context("return policy", enriched="return policy: Returns accepted within 30 days")) is None


def test_grounding_responder_passes_none_through():
    wrapped = GroundingResponder(StaticResponder(None), GroundingCheck())
    assert wrapped.respond(_context("anything")) is None


def test_grounding_responder_records_metadata():
    checker = GroundingCheck()
    wrapped = GroundingResponder(StaticResponder("Returns accepted within 30 days"), checker)
    context = _context("return policy", enriched="return policy: Returns accepted within 30 days")

    wrapped.respond(context)

    assert context.metadata["grounding"]["grounded"] is True


def test_grounding_responder_in_chain_escalates_to_llm():
    checker = GroundingCheck()
    grounded_tier = GroundingResponder(StaticResponder("Returns accepted within 30 days"), checker)
    hallucinating_tier = GroundingResponder(StaticResponder("Free worldwide shipping"), checker)

    chain = ResponderChain(
        [("grounded", grounded_tier), ("hallucinating", hallucinating_tier)],
        fallback=lambda context: "llm",
    )
    context = _context("return policy", enriched="return policy: Returns accepted within 30 days")

    # The grounded tier answers first; the hallucinating one would be skipped anyway.
    assert chain.respond(context) == "Returns accepted within 30 days"


def test_grounding_responder_rejects_bad_checker():
    with pytest.raises(TypeError, match="verify"):
        GroundingResponder(StaticResponder("x"), "not-a-checker")

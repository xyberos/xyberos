import pytest

from xyberos.router import DegradedResponder, ResponderChain
from xyberos.runtime.context import CognitiveContext


def test_degraded_responder_refusal_lists_capabilities():
    degraded = DegradedResponder("refusal", capabilities=["billing", "orders"])

    message = degraded.respond(CognitiveContext("anything"))

    assert "billing" in message
    assert "orders" in message


def test_degraded_responder_offline_message():
    degraded = DegradedResponder("offline", capabilities=["support"])

    assert "unable to connect" in degraded.respond(CognitiveContext("anything"))


def test_degraded_responder_human_message():
    degraded = DegradedResponder("human")

    assert "connect you with someone" in degraded.respond(CognitiveContext("anything"))


def test_degraded_responder_default_capabilities():
    degraded = DegradedResponder()
    assert "general assistance" in degraded.respond(CognitiveContext("anything"))


def test_degraded_responder_rejects_unknown_policy():
    with pytest.raises(ValueError, match="policy"):
        DegradedResponder("bogus")


def test_degraded_responder_confidence_is_zero():
    assert DegradedResponder().confidence(object()) == 0.0


def test_degraded_responder_as_chain_fallback():
    chain = ResponderChain(
        [],
        fallback=DegradedResponder("refusal", capabilities=["help"]),
    )

    message = chain.respond(CognitiveContext("anything"))

    assert "help" in message

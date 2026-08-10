import pytest

from xyberos.contracts import Responder, Template
from xyberos.llm import CallableLLM
from xyberos.router import LLMResponder, ResponderChain, TemplateResponder


class FailingResponder(Responder):
    """A responder that raises, to prove the chain escalates on failure."""

    def respond(self, context):
        raise RuntimeError("boom")


class RecordingResponder(Responder):
    """A responder that records its own calls and returns a canned answer."""

    def __init__(self, answer=None, confidence=1.0):
        self.answer = answer
        self.conf = confidence
        self.calls = 0

    def respond(self, context):
        self.calls += 1
        return self.answer

    def confidence(self, context):
        return self.conf


def test_chain_returns_first_confident_answer_in_priority_order():
    low = RecordingResponder(answer=None)
    high = RecordingResponder(answer="high")
    chain = ResponderChain([("low", low), ("high", high)])

    assert chain.respond(object()) == "high"
    assert low.calls == 1
    assert high.calls == 1


def test_chain_stops_at_first_answer_and_never_calls_later_tiers():
    low = RecordingResponder(answer="answer")
    skipped = RecordingResponder(answer="skipped")
    chain = ResponderChain([("low", low), ("skipped", skipped)])

    assert chain.respond(object()) == "answer"
    assert skipped.calls == 0


def test_chain_honors_per_tier_confidence_gate():
    low = RecordingResponder(answer="low", confidence=0.4)
    high = RecordingResponder(answer="high", confidence=0.9)
    chain = ResponderChain(
        [("low", low), ("high", high)],
        threshold=0.5,
    )

    assert chain.respond(object()) == "high"
    assert low.calls == 0  # gated out before respond() is consulted
    assert high.calls == 1


def test_chain_records_winning_tier_on_context_metadata():
    class Context:
        def __init__(self):
            self.metadata = {}

    context = Context()
    chain = ResponderChain([("template", RecordingResponder(answer="hi"))])

    assert chain.respond(context) == "hi"
    assert context.metadata["responder"] == "template"
    assert context.metadata["responder_confidence"] == 1.0


def test_chain_escalates_when_responder_raises():
    chain = ResponderChain([("failing", FailingResponder()), ("ok", RecordingResponder(answer="ok"))])

    assert chain.respond(object()) == "ok"


def test_chain_returns_none_when_everyone_declines_and_no_fallback():
    chain = ResponderChain([("declines", RecordingResponder(answer=None))])

    assert chain.respond(object()) is None


def test_chain_runs_responder_fallback():
    fallback = RecordingResponder(answer="fallback")
    chain = ResponderChain([("declines", RecordingResponder(answer=None))], fallback=fallback)

    assert chain.respond(object()) == "fallback"


def test_chain_runs_callable_fallback():
    chain = ResponderChain([], fallback=lambda context: "callable-fallback")

    assert chain.respond(object()) == "callable-fallback"


def test_chain_accepts_plain_responders_and_assigns_tier_names():
    chain = ResponderChain([RecordingResponder(answer="x")])
    assert chain.responders[0][0] == "tier0"


def test_chain_rejects_invalid_threshold():
    with pytest.raises(ValueError, match="threshold"):
        ResponderChain(threshold=1.5)


def test_chain_respond_cheap_stops_before_llm_tier():
    cheap = RecordingResponder(answer="cheap")
    llm = LLMResponder(CallableLLM(lambda prompt: "llm"))
    chain = ResponderChain([("cache", cheap), ("llm", llm)])

    assert chain.respond_cheap(object()) == "cheap"


def test_chain_respond_cheap_returns_none_when_no_cheap_tier_answers():
    chain = ResponderChain(
        [("cache", RecordingResponder(answer=None)), ("llm", LLMResponder(CallableLLM(lambda p: "llm")))],
        fallback=lambda context: "fallback",
    )

    assert chain.respond_cheap(object()) is None  # no fallback in the cheap pass


def test_chain_respond_cheap_skips_fallback():
    chain = ResponderChain([("cache", RecordingResponder(answer=None))], fallback=lambda context: "fallback")
    assert chain.respond_cheap(object()) is None


def test_chain_respond_cheap_stops_before_local_cloud_names():
    cheap = RecordingResponder(answer="cheap")
    cloud = RecordingResponder(answer="cloud")
    chain = ResponderChain([("cache", cheap), ("cloud", cloud)])

    assert chain.respond_cheap(object()) == "cheap"


def test_template_responder_requires_template_instances():
    with pytest.raises(TypeError, match="Template"):
        TemplateResponder(["not-a-template"])  # type: ignore[list-item]


def test_template_responder_rejects_empty_variants():
    with pytest.raises(ValueError, match="variant"):
        TemplateResponder([Template(pattern="x", variants=())])

from xyberos.llm import CallableLLM
from xyberos.router import LLMResponder, ResponderChain
from xyberos.runtime.context import CognitiveContext


def test_llm_responder_generates_from_prompt():
    responder = LLMResponder(CallableLLM(lambda prompt: f"answer: {prompt}"))

    assert responder.respond(CognitiveContext("hello")) == "answer: hello"


def test_llm_responder_prefers_enriched_prompt():
    responder = LLMResponder(CallableLLM(lambda prompt: prompt))
    context = CognitiveContext("hello")
    context.enriched_prompt = "ENRICHED"

    assert responder.respond(context) == "ENRICHED"


def test_llm_responder_always_confident():
    responder = LLMResponder(CallableLLM(lambda prompt: prompt))
    assert responder.confidence(CognitiveContext("x")) == 1.0


def test_llm_responder_is_terminal_tier_in_chain():
    chain = ResponderChain(
        [("llm", LLMResponder(CallableLLM(lambda prompt: "llm: " + prompt)))],
        fallback=lambda context: "degraded",
    )

    assert chain.respond(CognitiveContext("anything")) == "llm: anything"

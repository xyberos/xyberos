from xyberos.contracts import Template
from xyberos.knowledge import VectorKnowledge
from xyberos.llm import CallableLLM
from xyberos.memory import VectorMemory
from xyberos.router import (
    CacheResponder,
    DegradedResponder,
    KnowledgeResponder,
    LLMResponder,
    MemoryResponder,
    ResponderChain,
    TemplateResponder,
    ToolResponder,
    build_router,
)
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import ToolRunner
from xyberos.vector import CosineVectorStore


def test_build_router_orders_tiers_cheapest_first():
    chain = build_router(
        llm=CallableLLM(lambda prompt: "llm"),
        tool_runner=ToolRunner(),
        knowledge=VectorKnowledge(CosineVectorStore(), embedder=lambda t: [1.0]),
        memory=VectorMemory(CosineVectorStore(), embedder=lambda t: [1.0]),
        cache_store=CosineVectorStore(),
        cache_embedder=lambda t: [1.0],
        templates=[Template(pattern="hello", variants=("Hi!",))],
    )

    names = [name for name, _ in chain.responders]
    assert names == ["template", "tool", "knowledge", "memory", "cache", "llm"]


def test_build_router_with_no_deps_has_degraded_fallback():
    chain = build_router()
    assert chain.responders == ()
    assert isinstance(chain.fallback, DegradedResponder)


def test_build_router_llm_tier_answers_everything():
    chain = build_router(llm=CallableLLM(lambda prompt: "llm: " + prompt))
    assert chain.respond(CognitiveContext("anything")) == "llm: anything"


def test_build_router_degraded_fallback_fires_without_llm():
    chain = build_router(degrade="refusal", capabilities=["help"])
    message = chain.respond(CognitiveContext("anything"))
    assert "help" in message


def test_build_router_accepts_custom_fallback():
    chain = build_router(fallback=lambda context: "custom fallback")
    assert chain.respond(CognitiveContext("anything")) == "custom fallback"


def test_build_router_uses_provided_cache_instance():
    cache = CacheResponder()
    cache.teach("hours", "9-5")
    chain = build_router(cache=cache)
    assert chain.respond(CognitiveContext("hours")) == "9-5"

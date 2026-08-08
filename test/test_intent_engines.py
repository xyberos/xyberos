"""Tests for the Phase 1 trainable intent engines (RFC-0016)."""

from xyberos.contracts import Intent
from xyberos.intent import (
    CascadeIntentEngine,
    EmbeddingIntentEngine,
    LLMIntentEngine,
)
from xyberos.llm import CallableLLM
from xyberos.runtime.context import CognitiveContext
from xyberos.vector import CosineVectorStore

_VOCAB = ("refund", "policy", "joke", "hello", "order", "hours", "shipping", "rules", "greeting")


def _embedder(text):
    vector = [0.0] * len(_VOCAB)
    for word in text.lower().split():
        for index, term in enumerate(_VOCAB):
            if term in word or word in term:
                vector[index] += 1.0
    return vector


class _FakeEngine:
    def __init__(self, name, confidence):
        self._name = name
        self._confidence = confidence

    def classify(self, context):
        return Intent(name=self._name, confidence=self._confidence)


def test_llm_intent_engine_parses_structured_output():
    llm = CallableLLM(
        lambda prompt: (
            '{"name": "refund", "confidence": 0.9, "target": "refund_tool", '
            '"params": {"order": "A-1"}}'
        )
    )
    engine = LLMIntentEngine(llm)

    intent = engine.classify(CognitiveContext("I want a refund"))

    assert intent.name == "refund"
    assert intent.confidence == 0.9
    assert intent.target == "refund_tool"
    assert intent.params == {"order": "A-1"}


def test_llm_intent_engine_falls_back_on_unparseable_output():
    llm = CallableLLM(lambda prompt: "not json at all")
    engine = LLMIntentEngine(llm, fallback="general")

    intent = engine.classify(CognitiveContext("hello"))

    assert intent.name == "general"
    assert intent.confidence == 0.0


def test_embedding_intent_engine_learns_and_classifies():
    engine = EmbeddingIntentEngine(CosineVectorStore(), embedder=_embedder)
    engine.learn("refund", "please refund my order")
    engine.learn("greeting", "hello there, nice to meet you")

    intent = engine.classify(CognitiveContext("i want a refund please"))

    assert intent.name == "refund"
    assert intent.confidence > 0.0


def test_embedding_intent_engine_falls_back_when_no_examples():
    engine = EmbeddingIntentEngine(CosineVectorStore(), embedder=_embedder, fallback="general")

    intent = engine.classify(CognitiveContext("anything"))

    assert intent.name == "general"
    assert intent.confidence == 0.0


def test_cascade_returns_first_confident_engine():
    cascade = CascadeIntentEngine(_FakeEngine("low", 0.2), _FakeEngine("high", 0.9))

    intent = cascade.classify(CognitiveContext("x"))

    assert intent.name == "high"


def test_cascade_falls_back_when_nothing_is_confident():
    cascade = CascadeIntentEngine(
        _FakeEngine("low", 0.2), confidence_threshold=0.8, fallback="general"
    )

    intent = cascade.classify(CognitiveContext("x"))

    assert intent.name == "general"

import pytest

from xyberos.router import CacheResponder, ResponderChain
from xyberos.runtime.context import CognitiveContext
from xyberos.vector import CosineVectorStore


def _embedder(text):
    vocab = ("refund", "hours")
    vector = [0.0] * len(vocab)
    for word in text.lower().split():
        for index, term in enumerate(vocab):
            if term in word or word in term:
                vector[index] += 1.0
    return vector


def test_cache_responder_exact_mode_serves_taught_answer():
    cache = CacheResponder()
    cache.teach("what are your hours", "We're open 9-5.")

    assert cache.respond(CognitiveContext("what are your hours")) == "We're open 9-5."


def test_cache_responder_exact_mode_miss_returns_none():
    cache = CacheResponder()
    cache.teach("what are your hours", "9-5")

    assert cache.respond(CognitiveContext("unrelated question")) is None


def test_cache_responder_teach_batch_pre_seeds():
    cache = CacheResponder()
    assert cache.teach_batch([("a", "1"), ("b", "2")]) == 2
    assert cache.size == 2
    assert cache.respond(CognitiveContext("a")) == "1"
    assert cache.respond(CognitiveContext("b")) == "2"


def test_cache_responder_store_mode_serves_near_exact():
    cache = CacheResponder(CosineVectorStore(), embedder=_embedder)
    cache.teach("how do I get a refund", "File a claim.")

    assert cache.respond(CognitiveContext("how do I get a refund")) == "File a claim."


def test_cache_responder_store_mode_miss_returns_none():
    cache = CacheResponder(CosineVectorStore(), embedder=_embedder)
    cache.teach("how do I get a refund", "File a claim.")

    assert cache.respond(CognitiveContext("what is the weather")) is None


def test_cache_responder_requires_embedder_with_store():
    with pytest.raises(ValueError, match="embedder"):
        CacheResponder(CosineVectorStore())


def test_cache_responder_confidence_reflects_hit():
    cache = CacheResponder()
    cache.teach("hello", "Hi!")
    assert cache.confidence(CognitiveContext("hello")) == 1.0
    assert cache.confidence(CognitiveContext("novel")) == 0.0


def test_cache_responder_in_chain_answers_before_llm():
    cache = CacheResponder()
    cache.teach("hello", "Hi there!")
    chain = ResponderChain([("cache", cache)], fallback=lambda context: "llm")

    assert chain.respond(CognitiveContext("hello")) == "Hi there!"
    assert chain.respond(CognitiveContext("novel request")) == "llm"

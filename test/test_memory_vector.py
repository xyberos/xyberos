"""Tests for the Phase 1 memory engines (RFC-0016)."""

from xyberos.llm import CallableLLM
from xyberos.memory import ConsolidatingMemory, VectorMemory
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


def test_vector_memory_returns_recent_entries_without_embedder():
    memory = VectorMemory(CosineVectorStore())
    memory.store(CognitiveContext("one", response="r1"))
    memory.store(CognitiveContext("two", response="r2"))

    entries = memory.retrieve(CognitiveContext("query"))

    assert [entry.response for entry in entries] == ["r2", "r1"]


def test_vector_memory_retrieves_semantically_similar_history():
    memory = VectorMemory(CosineVectorStore(), embedder=_embedder, top_k=2, alpha=1.0)
    memory.store(CognitiveContext("what is the refund policy", response="policy text"))
    memory.store(CognitiveContext("tell me a joke", response="ha ha"))

    entries = memory.retrieve(CognitiveContext("refund rules please"))

    assert entries[0].prompt == "what is the refund policy"


def test_vector_memory_clear_drops_everything():
    memory = VectorMemory(CosineVectorStore(), embedder=_embedder)
    memory.store(CognitiveContext("hello", response="hi"))
    memory.clear()

    assert memory.retrieve(CognitiveContext("hello")) == []


def test_vector_memory_validates_arguments():
    import pytest

    with pytest.raises(ValueError):
        VectorMemory(CosineVectorStore(), top_k=0)
    with pytest.raises(ValueError):
        VectorMemory(CosineVectorStore(), alpha=2.0)


def test_consolidating_memory_summarizes_old_turns_without_llm():
    memory = ConsolidatingMemory(interval=5, keep=2)
    for index in range(5):
        memory.store(CognitiveContext(f"q{index}", response=f"a{index}"))

    entries = memory.retrieve(CognitiveContext("x"))

    assert len(entries) == 3
    assert any(getattr(entry, "prompt", None) == "[consolidated]" for entry in entries)


def test_consolidating_memory_uses_llm_summary():
    llm = CallableLLM(lambda prompt: "SUMMARY TEXT")
    memory = ConsolidatingMemory(interval=3, keep=1, llm=llm)
    for index in range(3):
        memory.store(CognitiveContext(f"q{index}", response=f"a{index}"))

    entries = memory.retrieve(CognitiveContext("x"))

    assert len(entries) == 2
    assert any(getattr(entry, "response", None) == "SUMMARY TEXT" for entry in entries)


def test_consolidating_memory_validates_arguments():
    import pytest

    with pytest.raises(ValueError):
        ConsolidatingMemory(interval=2, keep=5)

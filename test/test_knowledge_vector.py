"""Tests for the Phase 1 knowledge engines (RFC-0016)."""

from xyberos.knowledge import IngestingKnowledge, VectorKnowledge
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


def test_vector_knowledge_queries_semantic_facts():
    knowledge = VectorKnowledge(CosineVectorStore(), embedder=_embedder)
    knowledge.add("hours", "open 9am to 6pm")
    knowledge.add("refunds", "refunds within 30 days")

    facts = knowledge.query(CognitiveContext("how do refunds work"))

    assert "refunds" in facts
    assert "30 days" in facts


def test_vector_knowledge_returns_empty_when_no_match():
    knowledge = VectorKnowledge(CosineVectorStore(), embedder=_embedder)

    assert knowledge.query(CognitiveContext("anything")) == ""


def test_vector_knowledge_clear_drops_facts():
    knowledge = VectorKnowledge(CosineVectorStore(), embedder=_embedder)
    knowledge.add("hours", "open 9am to 6pm")
    knowledge.clear()

    assert knowledge.query(CognitiveContext("hours")) == ""


def test_ingesting_knowledge_chunks_and_indexes():
    knowledge = IngestingKnowledge(CosineVectorStore(), embedder=_embedder)

    count = knowledge.ingest(
        "Paragraph one about refunds.\n\nParagraph two about shipping.",
        chunk_size=50,
    )

    assert count == 2
    assert knowledge.query(CognitiveContext("refunds")) != ""


def test_ingesting_knowledge_handles_empty_text():
    knowledge = IngestingKnowledge(CosineVectorStore(), embedder=_embedder)

    assert knowledge.ingest("   ") == 0

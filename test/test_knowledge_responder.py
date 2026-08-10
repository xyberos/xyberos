from xyberos.knowledge import VectorKnowledge
from xyberos.router import KnowledgeResponder, ResponderChain
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


def _knowledge(*facts):
    knowledge = VectorKnowledge(CosineVectorStore(), embedder=_embedder)
    for key, value in facts:
        knowledge.add(key, value)
    return knowledge


def test_knowledge_responder_answers_when_top_fact_clears_gate():
    knowledge = _knowledge(("refund policy", "Returns accepted within 30 days"))
    responder = KnowledgeResponder(knowledge)

    assert responder.respond(CognitiveContext("what is the refund policy")) == "Returns accepted within 30 days"


def test_knowledge_responder_returns_none_below_threshold():
    knowledge = _knowledge(("refund policy", "Returns accepted within 30 days"))
    responder = KnowledgeResponder(knowledge)

    assert responder.respond(CognitiveContext("what are your opening hours")) is None


def test_knowledge_responder_returns_none_when_knowledge_is_empty():
    responder = KnowledgeResponder(_knowledge())
    assert responder.respond(CognitiveContext("what is the refund policy")) is None


def test_knowledge_responder_confidence_is_top_score():
    knowledge = _knowledge(("refund policy", "Returns accepted within 30 days"))
    responder = KnowledgeResponder(knowledge)

    assert responder.confidence(CognitiveContext("what is the refund policy")) == 1.0
    assert responder.confidence(CognitiveContext("unrelated words here")) == 0.0


def test_knowledge_responder_escalates_without_scored_support():
    class PlainKnowledge:
        def query(self, context):
            return "facts"

    responder = KnowledgeResponder(PlainKnowledge())
    assert responder.respond(CognitiveContext("anything")) is None


def test_knowledge_responder_in_chain_answers_before_llm():
    knowledge = _knowledge(("refund policy", "Returns accepted within 30 days"))
    chain = ResponderChain(
        [("knowledge", KnowledgeResponder(knowledge))],
        fallback=lambda context: "llm",
    )

    assert chain.respond(CognitiveContext("what is the refund policy")) == "Returns accepted within 30 days"
    assert chain.respond(CognitiveContext("nothing relevant")) == "llm"


def test_knowledge_responder_rejects_invalid_threshold():
    try:
        KnowledgeResponder(_knowledge(), threshold=1.5)
    except ValueError as exc:
        assert "threshold" in str(exc)
    else:
        raise AssertionError("expected ValueError for out-of-range threshold")

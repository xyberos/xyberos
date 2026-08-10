from xyberos.memory import VectorMemory
from xyberos.router import MemoryResponder, ResponderChain
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


def _memory(*turns):
    memory = VectorMemory(CosineVectorStore(), embedder=_embedder)
    for prompt, response in turns:
        memory.store(CognitiveContext(prompt, response=response))
    return memory


def test_memory_responder_answers_when_past_turn_clears_gate():
    memory = _memory(("how do I get a refund", "File a claim under Settings."))
    responder = MemoryResponder(memory)

    assert responder.respond(CognitiveContext("how do I get a refund")) == "File a claim under Settings."


def test_memory_responder_returns_none_below_threshold():
    memory = _memory(("how do I get a refund", "File a claim under Settings."))
    responder = MemoryResponder(memory)

    assert responder.respond(CognitiveContext("what are your opening hours")) is None


def test_memory_responder_returns_none_when_memory_is_empty():
    responder = MemoryResponder(_memory())
    assert responder.respond(CognitiveContext("how do I get a refund")) is None


def test_memory_responder_confidence_is_top_score():
    memory = _memory(("how do I get a refund", "File a claim under Settings."))
    responder = MemoryResponder(memory)

    assert responder.confidence(CognitiveContext("how do I get a refund")) == 1.0
    assert responder.confidence(CognitiveContext("unrelated words here")) == 0.0


def test_memory_responder_escalates_without_scored_support():
    class PlainMemory:
        def retrieve(self, context):
            return []

    responder = MemoryResponder(PlainMemory())
    assert responder.respond(CognitiveContext("anything")) is None


def test_memory_responder_in_chain_answers_before_llm():
    memory = _memory(("how do I get a refund", "File a claim under Settings."))
    chain = ResponderChain(
        [("memory", MemoryResponder(memory))],
        fallback=lambda context: "llm",
    )

    assert chain.respond(CognitiveContext("how do I get a refund")) == "File a claim under Settings."
    assert chain.respond(CognitiveContext("nothing relevant")) == "llm"


def test_memory_responder_rejects_invalid_threshold():
    try:
        MemoryResponder(_memory(), threshold=1.5)
    except ValueError as exc:
        assert "threshold" in str(exc)
    else:
        raise AssertionError("expected ValueError for out-of-range threshold")

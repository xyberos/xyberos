from xyberos.memory import InMemoryMemory, StratifiedMemory, extract_facts_deterministic
from xyberos.runtime.context import CognitiveContext
from xyberos.vector import CosineVectorStore


def _embedder(text):
    vocab = ("name", "coffee", "location")
    vector = [0.0] * len(vocab)
    for word in text.lower().split():
        for index, term in enumerate(vocab):
            if term in word or word in term:
                vector[index] += 1.0
    return vector


def _stratified(*, extract_facts=None):
    return StratifiedMemory(
        InMemoryMemory(),
        CosineVectorStore(),
        embedder=_embedder,
        extract_facts=extract_facts,
    )


def test_deterministic_extractor_captures_durable_facts():
    # The deterministic extractor processes one turn's prompt at a time;
    # users state durable facts across turns.
    assert "user name: alice" in extract_facts_deterministic("My name is Alice", None)
    assert "user favorite coffee: a latte" in extract_facts_deterministic(
        "My favorite coffee is a latte", None
    )
    assert "user location: manila" in extract_facts_deterministic("I am from Manila", None)


def test_deterministic_extractor_ignores_plain_questions():
    assert extract_facts_deterministic("What is the weather today?", None) == []


def test_stratified_memory_indexes_facts_and_keeps_episodes():
    memory = _stratified()
    memory.store(CognitiveContext("My name is Bob", response="Nice to meet you, Bob."))

    facts = memory.facts(CognitiveContext("what is your name"))
    assert "user name: bob" in facts

    episodes = memory.retrieve(CognitiveContext("My name is Bob"))
    assert len(episodes) == 1
    assert episodes[0].response == "Nice to meet you, Bob."


def test_stratified_memory_uses_custom_extractor():
    def extract(prompt, response):
        return ["custom fact"] if prompt == "mark this" else []

    memory = _stratified(extract_facts=extract)
    memory.store(CognitiveContext("mark this", response="ok"))

    assert memory.facts(CognitiveContext("mark this")) == ["custom fact"]


def test_stratified_memory_facts_are_namespaced():
    memory = _stratified()
    memory.store(CognitiveContext("My name is Carol", response="Hello Carol."))

    # A related query retrieves the fact; an unrelated one is gated out.
    assert memory.facts(CognitiveContext("what is my name")) == ["user name: carol"]
    assert memory.facts(CognitiveContext("totally unrelated topic"), threshold=0.5) == []


def test_stratified_memory_clear_facts():
    memory = _stratified()
    memory.store(CognitiveContext("My name is Dave", response="Hi Dave."))
    memory.clear_facts()

    assert memory.facts(CognitiveContext("what is your name")) == []


def test_stratified_memory_requires_store():
    try:
        StratifiedMemory(InMemoryMemory(), None)
    except ValueError as exc:
        assert "store" in str(exc)
    else:
        raise AssertionError("expected ValueError when store is missing")

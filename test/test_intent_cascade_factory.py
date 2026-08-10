from xyberos.intent import (
    CascadeIntentEngine,
    EmbeddingIntentEngine,
    HeuristicIntentEngine,
    IntentRule,
    build_intent_cascade,
)
from xyberos.llm import CallableLLM, HashEmbedder
from xyberos.vector import CosineVectorStore


def _embedder(text):
    vocab = ("refund", "hello")
    vector = [0.0] * len(vocab)
    for word in text.lower().split():
        for index, term in enumerate(vocab):
            if term in word or word in term:
                vector[index] += 1.0
    return vector


class Context:
    def __init__(self, prompt):
        self.prompt = prompt


def test_build_intent_cascade_assembles_all_three_tiers():
    cascade = build_intent_cascade(
        store=CosineVectorStore(),
        embedder=_embedder,
        llm=CallableLLM(lambda prompt: prompt),
    )

    assert isinstance(cascade, CascadeIntentEngine)
    assert len(cascade.engines) == 3
    assert isinstance(cascade.engines[0], HeuristicIntentEngine)
    assert isinstance(cascade.engines[1], EmbeddingIntentEngine)


def test_build_intent_cascade_omits_llm_tier_when_no_llm():
    cascade = build_intent_cascade(store=CosineVectorStore(), embedder=_embedder)

    assert isinstance(cascade, CascadeIntentEngine)
    assert len(cascade.engines) == 2


def test_build_intent_cascade_degrades_to_heuristic_without_store_or_llm():
    engine = build_intent_cascade()
    assert isinstance(engine, HeuristicIntentEngine)


def test_build_intent_cascade_heuristic_tier_answers_obvious_phrasing():
    cascade = build_intent_cascade(store=CosineVectorStore(), embedder=_embedder)
    intent = cascade.classify(Context("hello there"))
    assert intent.name == "greeting"
    assert intent.confidence == 1.0


def test_build_intent_cascade_embedding_tier_answers_paraphrasing():
    store = CosineVectorStore()
    cascade = build_intent_cascade(store=store, embedder=_embedder, threshold=0.6)
    cascade.learn("refund", "please refund my order")

    intent = cascade.classify(Context("please refund"))

    assert intent.name == "refund"
    assert intent.confidence >= 0.6


def test_build_intent_cascade_respects_custom_rules():
    cascade = build_intent_cascade(
        rules=[IntentRule("support", ("i need an agent",))],
        store=CosineVectorStore(),
        embedder=_embedder,
    )

    assert cascade.classify(Context("i need an agent")).name == "support"
    assert cascade.classify(Context("hello")).name == "general"  # no default greeting rule


def test_build_intent_cascade_rejects_invalid_threshold():
    try:
        build_intent_cascade(threshold=1.5)
    except ValueError as exc:
        assert "threshold" in str(exc)
    else:
        raise AssertionError("expected ValueError for out-of-range threshold")


def test_build_intent_cascade_default_threshold_rejects_unrelated_noise():
    # The default HashEmbedder is biased high (~0.6-0.8 for unrelated phrases),
    # so the conservative default (0.9) must reject an unrelated query instead of
    # confidently misrouting it to the nearest learned example.
    store = CosineVectorStore()
    cascade = build_intent_cascade(store=store, embedder=HashEmbedder())
    cascade.learn("refund", "I want my money returned please")

    intent = cascade.classify(Context("explain quantum entanglement"))

    assert intent.name == "general"
    assert intent.confidence == 0.0


def test_build_intent_cascade_default_threshold_accepts_near_identical():
    store = CosineVectorStore()
    cascade = build_intent_cascade(store=store, embedder=HashEmbedder())
    cascade.learn("refund", "I want my money returned please")

    intent = cascade.classify(Context("I want my money returned please"))

    assert intent.name == "refund"
    assert intent.confidence >= 0.9


def test_cascade_learn_forwards_to_embedding_engine():
    store = CosineVectorStore()
    cascade = CascadeIntentEngine(
        HeuristicIntentEngine(),
        EmbeddingIntentEngine(store, embedder=_embedder),
    )

    cascade.learn("refund", "please refund my order")

    hits = store.query("intents", _embedder("please refund"), top_k=1)
    assert len(hits) == 1
    assert hits[0].payload.get("name") == "refund"

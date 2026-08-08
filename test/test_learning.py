"""Tests for the RFC-0016 learning layer: feedback, promote/demote, and loops."""

from xyberos import create_app
from xyberos.contracts import Episode, Intent
from xyberos.events import FEEDBACK_RECORDED
from xyberos.experience import InMemoryExperience
from xyberos.intent import EmbeddingIntentEngine
from xyberos.learning import ExamplePromoter, demote_failed, promote_successful, to_examples
from xyberos.llm import CallableLLM
from xyberos.planner import AdaptivePlanner
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


def test_app_feedback_records_rating_and_emits_event():
    experience = InMemoryExperience()
    app = create_app(
        llm=CallableLLM(lambda prompt: "ok"),
        experience=experience,
        config={"experience.enabled": True},
    )
    app.chat("hello")
    episode_id = experience.query(limit=1)[0].id
    seen = []
    app.events.subscribe(FEEDBACK_RECORDED, lambda event: seen.append(event.data))

    app.feedback(episode_id, 0.9)

    assert experience.query(limit=1)[0].feedback == 0.9
    assert seen and seen[0]["rating"] == 0.9


def test_promote_successful_and_demote_failed():
    store = InMemoryExperience()
    good = store.record(Episode(prompt="refund", response="handled", outcome="success"))
    rated = store.record(Episode(prompt="faq", response="answer"))
    store.record(Episode(prompt="x", response="y", outcome="failure"))
    store.feedback(good.id, 1.0)
    store.feedback(rated.id, 0.8)

    promoted = promote_successful(store)
    demoted = demote_failed(store)

    assert {episode.prompt for episode in promoted} == {"refund", "faq"}
    assert [episode.prompt for episode in demoted] == ["x"]


def test_to_examples_extracts_prompt_target_pairs():
    store = InMemoryExperience()
    store.record(Episode(prompt="refund", plan=["a", "b"], outcome="success"))
    store.record(Episode(prompt="no plan", outcome="failure"))

    episodes = promote_successful(store)
    examples = to_examples(episodes, field="plan")

    assert examples == [("refund", ["a", "b"])]


def test_feedback_promotion_feeds_intent_engine_learning_loop():
    store = CosineVectorStore()
    engine = EmbeddingIntentEngine(store, embedder=_embedder)
    experience = InMemoryExperience()

    episode = experience.record(
        Episode(prompt="I need a refund", response="refund processed", intent=Intent(name="refund"))
    )
    experience.feedback(episode.id, 1.0)

    for prompt, _ in to_examples(promote_successful(experience)):
        engine.learn("refund", prompt)

    intent = engine.classify(CognitiveContext("can I get a refund please"))

    assert intent.name == "refund"
    assert intent.confidence > 0.0


def test_example_promoter_feeds_intent_engine_and_planner():
    experience = InMemoryExperience()
    store = CosineVectorStore()
    intent_engine = EmbeddingIntentEngine(store, embedder=_embedder)
    planner = AdaptivePlanner(CallableLLM(lambda prompt: "step"), store=store, embedder=_embedder)
    promoter = ExamplePromoter(experience, intent_engine=intent_engine, planner=planner)

    episode = experience.record(
        Episode(
            prompt="I need a refund",
            intent=Intent(name="refund"),
            plan=["check order", "process refund"],
            outcome="success",
        )
    )
    experience.feedback(episode.id, 1.0)

    assert promoter.promote() == 2
    assert intent_engine.classify(CognitiveContext("refund please")).name == "refund"


def test_example_promoter_with_no_learners_is_safe():
    experience = InMemoryExperience()
    promoter = ExamplePromoter(experience)
    episode = experience.record(Episode(prompt="x", outcome="success"))

    assert promoter.promote() == 0
    assert episode.prompt == "x"

from xyberos.contracts import Episode
from xyberos.experience import InMemoryExperience
from xyberos.knowledge import VectorKnowledge
from xyberos.learning import KnowledgePromoter
from xyberos.runtime.context import CognitiveContext
from xyberos.vector import CosineVectorStore


def _embedder(text):
    vocab = ("return", "hours")
    vector = [0.0] * len(vocab)
    for word in text.lower().split():
        for index, term in enumerate(vocab):
            if term in word or word in term:
                vector[index] += 1.0
    return vector


def _make_promoter(experience):
    knowledge = VectorKnowledge(CosineVectorStore(), embedder=_embedder)
    return KnowledgePromoter(experience, knowledge), knowledge


def test_promoter_ingests_positively_rated_episodes():
    experience = InMemoryExperience()
    episode = experience.record(
        Episode(prompt="how do I return an item", response="Returns accepted within 30 days.")
    )
    experience.feedback(episode.id, 1.0)
    promoter, knowledge = _make_promoter(experience)

    assert promoter.promote() == 1
    hits = knowledge.query_scored(CognitiveContext("how do I return an item"), top_k=1)
    assert len(hits) == 1
    assert hits[0].payload.get("value") == "Returns accepted within 30 days."


def test_promoter_ingests_explicit_success_without_feedback():
    experience = InMemoryExperience()
    experience.record(
        Episode(prompt="how do I return an item", response="Returns accepted.", outcome="success")
    )
    promoter, knowledge = _make_promoter(experience)

    assert promoter.promote() == 1
    hits = knowledge.query_scored(CognitiveContext("how do I return an item"), top_k=1)
    assert len(hits) == 1


def test_promoter_skips_negative_and_unrated_episodes():
    experience = InMemoryExperience()
    experience.record(Episode(prompt="p1", response="a1", outcome="failure"))
    experience.record(Episode(prompt="p2", response="a2"))  # no outcome, no feedback
    promoter, _ = _make_promoter(experience)

    assert promoter.promote() == 0


def test_promoter_skips_episodes_without_response():
    experience = InMemoryExperience()
    experience.record(Episode(prompt="hello", response=None, outcome="success"))
    promoter, _ = _make_promoter(experience)

    assert promoter.promote() == 0


def test_promoter_is_idempotent_across_calls():
    experience = InMemoryExperience()
    episode = experience.record(
        Episode(prompt="how do I return an item", response="Returns accepted within 30 days.")
    )
    experience.feedback(episode.id, 1.0)
    promoter, knowledge = _make_promoter(experience)

    assert promoter.promote() == 1
    assert promoter.promote() == 0  # already ingested

    hits = knowledge.query_scored(CognitiveContext("how do I return an item"), top_k=1)
    assert len(hits) == 1  # no duplicates

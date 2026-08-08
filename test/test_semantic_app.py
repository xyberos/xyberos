"""Tests for create_semantic_app — the one-line persistent setup (RFC-0016)."""

from xyberos import create_semantic_app
from xyberos.intent import EmbeddingIntentEngine
from xyberos.knowledge import VectorKnowledge
from xyberos.llm import CallableLLM
from xyberos.memory import VectorMemory
from xyberos.planner import AdaptivePlanner
from xyberos.vector import CosineVectorStore, SqliteVectorStore

_VOCAB = ("refund", "hello")


def _embedder(text):
    vector = [0.0] * len(_VOCAB)
    for word in text.lower().split():
        for index, term in enumerate(_VOCAB):
            if term in word or word in term:
                vector[index] += 1.0
    return vector


def test_create_semantic_app_wires_vector_engines():
    app = create_semantic_app(
        llm=CallableLLM(lambda prompt: prompt),
        embedder=_embedder,
        store=CosineVectorStore(),
    )

    assert isinstance(app.intent, EmbeddingIntentEngine)
    assert isinstance(app.memory, VectorMemory)
    assert isinstance(app.knowledge, VectorKnowledge)
    assert isinstance(app.planner, AdaptivePlanner)


def test_create_semantic_app_enables_intent_by_default():
    app = create_semantic_app(
        llm=CallableLLM(lambda prompt: prompt),
        embedder=_embedder,
        store=CosineVectorStore(),
    )

    context = app.run("hello")

    assert context.intent is not None


def test_create_semantic_app_works_without_explicit_embedder():
    app = create_semantic_app(
        llm=CallableLLM(lambda prompt: prompt),
        store=CosineVectorStore(),
    )

    app.run("hello")  # must not raise; defaults to HashEmbedder


def test_create_semantic_app_defaults_to_persistent_sqlite_store(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    create_semantic_app(llm=CallableLLM(lambda prompt: prompt), embedder=_embedder)

    assert (tmp_path / "learning.db").exists()


def test_create_semantic_app_uses_provided_store():
    store = CosineVectorStore()
    app = create_semantic_app(
        llm=CallableLLM(lambda prompt: prompt),
        embedder=_embedder,
        store=store,
    )
    app.intent.learn("refund", "please refund my order")

    intent = app.run("please refund").intent

    assert intent is not None
    assert intent.name == "refund"


def test_create_semantic_app_persists_learned_examples(tmp_path):
    path = str(tmp_path / "learning.db")
    store = SqliteVectorStore(path)
    app = create_semantic_app(
        llm=CallableLLM(lambda prompt: prompt),
        embedder=_embedder,
        store=store,
    )
    app.intent.learn("refund", "please refund my order")
    store.close()

    reopened = SqliteVectorStore(path)
    hits = reopened.query("intents", _embedder("please refund"), top_k=1)

    assert len(hits) == 1
    assert hits[0].payload.get("name") == "refund"
    reopened.close()

"""Provider tests for the VectorStore contract (RFC-0016)."""

import importlib.util

import pytest

from xyberos.exceptions import ProviderError
from xyberos.vector import ChromaVectorStore, CosineVectorStore


def test_cosine_store_ranks_by_similarity():
    store = CosineVectorStore()
    store.upsert("ns", "a", [1.0, 0.0])
    store.upsert("ns", "b", [0.0, 1.0])
    store.upsert("ns", "c", [1.0, 1.0])

    hits = store.query("ns", [1.0, 0.0], top_k=3)

    assert [hit.id for hit in hits] == ["a", "c", "b"]
    assert hits[0].score > hits[1].score > hits[2].score


def test_cosine_store_respects_top_k_and_threshold():
    store = CosineVectorStore()
    store.upsert("ns", "a", [1.0, 0.0])
    store.upsert("ns", "b", [0.9, 0.1])

    assert len(store.query("ns", [1.0, 0.0], top_k=1)) == 1
    # b scores ~0.994, so a threshold of 0.95 keeps both; 0.995 keeps only "a".
    assert len(store.query("ns", [1.0, 0.0], threshold=0.95)) == 2
    assert len(store.query("ns", [1.0, 0.0], threshold=0.995)) == 1
    assert store.query("ns", [1.0, 0.0], threshold=1.1) == []


def test_cosine_store_payloads_delete_and_clear():
    store = CosineVectorStore()
    store.upsert("ns", "a", [1.0, 0.0], payload={"label": "x"})

    assert store.query("ns", [1.0, 0.0])[0].payload == {"label": "x"}

    store.delete("ns", "a")
    assert store.query("ns", [1.0, 0.0]) == []

    store.upsert("ns", "a", [1.0, 0.0])
    store.clear("ns")
    assert store.query("ns", [1.0, 0.0]) == []


def test_cosine_store_namespaces_are_isolated():
    store = CosineVectorStore()
    store.upsert("one", "a", [1.0, 0.0])
    store.upsert("two", "b", [0.0, 1.0])

    assert store.query("one", [1.0, 0.0])[0].id == "a"
    assert store.query("two", [1.0, 0.0])[0].id == "b"


def test_cosine_store_zero_vectors_do_not_raise():
    store = CosineVectorStore()
    store.upsert("ns", "a", [0.0, 0.0])

    assert store.query("ns", [1.0, 0.0])[0].score == 0.0


def test_chroma_store_requires_the_dependency_when_missing():
    if importlib.util.find_spec("chromadb") is not None:
        pytest.skip("chromadb is installed; cannot test the missing-dependency path")

    store = ChromaVectorStore()
    with pytest.raises(ProviderError, match="chromadb"):
        store.upsert("ns", "a", [1.0, 0.0])

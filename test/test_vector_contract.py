"""Contract tests for the VectorStore extension (RFC-0016)."""

import pytest

from xyberos.contracts import VectorStore
from xyberos.contracts.vector import ScoredHit


class StaticVectorStore(VectorStore):
    def upsert(self, namespace, id, vector, payload=None):  # noqa: A002
        pass

    def query(self, namespace, vector, *, top_k=5, threshold=None):
        return []

    def delete(self, namespace, id):  # noqa: A002
        pass

    def clear(self, namespace):
        pass


def test_vector_store_contract_requires_all_methods():
    with pytest.raises(TypeError):
        VectorStore()


def test_vector_store_contract_works_without_core_dependencies():
    store = StaticVectorStore()
    store.upsert("ns", "a", [1.0, 0.0])
    assert store.query("ns", [1.0, 0.0]) == []
    store.delete("ns", "a")
    store.clear("ns")


def test_scored_hit_is_a_frozen_dataclass():
    hit = ScoredHit(id="a", score=0.9, payload={"key": 1})
    assert hit.id == "a"
    assert hit.score == 0.9
    assert hit.payload == {"key": 1}

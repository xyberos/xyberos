"""Tests for the SQLite-backed persistent VectorStore (RFC-0016)."""

from xyberos.vector import SqliteVectorStore


def test_sqlite_vector_store_ranks_by_similarity():
    store = SqliteVectorStore()
    store.upsert("ns", "a", [1.0, 0.0])
    store.upsert("ns", "b", [0.0, 1.0])

    hits = store.query("ns", [1.0, 0.0], top_k=2)

    assert [hit.id for hit in hits] == ["a", "b"]
    assert hits[0].score > hits[1].score


def test_sqlite_vector_store_persists_across_reopen(tmp_path):
    path = str(tmp_path / "vectors.db")
    first = SqliteVectorStore(path)
    first.upsert("ns", "a", [1.0, 0.0], payload={"label": "x"})
    first.close()

    second = SqliteVectorStore(path)
    hits = second.query("ns", [1.0, 0.0])

    assert len(hits) == 1
    assert hits[0].id == "a"
    assert hits[0].payload == {"label": "x"}
    second.close()


def test_sqlite_vector_store_delete_and_clear(tmp_path):
    path = str(tmp_path / "vectors.db")
    store = SqliteVectorStore(path)
    store.upsert("ns", "a", [1.0, 0.0])
    store.upsert("ns", "b", [0.0, 1.0])

    store.delete("ns", "a")
    assert len(store.query("ns", [1.0, 0.0])) == 1

    store.clear("ns")
    assert store.query("ns", [1.0, 0.0]) == []
    store.close()


def test_sqlite_vector_store_namespaces_are_isolated():
    store = SqliteVectorStore()
    store.upsert("one", "a", [1.0, 0.0])
    store.upsert("two", "b", [0.0, 1.0])

    assert store.query("one", [1.0, 0.0])[0].id == "a"
    assert store.query("two", [1.0, 0.0])[0].id == "b"


def test_sqlite_vector_store_lifecycle_hooks(tmp_path):
    path = str(tmp_path / "vectors.db")
    store = SqliteVectorStore(path)
    store.start()
    store.upsert("ns", "a", [1.0, 0.0])
    store.stop()

    store.start()
    assert len(store.query("ns", [1.0, 0.0])) == 1
    store.stop()

"""SQLite-backed persistent VectorStore (RFC-0016, no dependencies)."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from typing import Any

from ..contracts.vector import ScoredHit, VectorStore
from ..utils.sqlite import ThreadLocalSQLite
from .cosine import cosine


def _create_vector_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS vector_entries (
            namespace TEXT NOT NULL,
            id TEXT NOT NULL,
            vector TEXT NOT NULL,
            payload TEXT,
            PRIMARY KEY (namespace, id)
        )
        """
    )
    connection.commit()


class SqliteVectorStore(VectorStore):
    """Persist vectors in a SQLite database using only the standard library.

    One row per ``(namespace, id)``; vectors are stored as JSON arrays and
    scored with exact cosine similarity on query. Like the other SQLite
    providers, connections open lazily, one per thread, and ``start``/``stop``
    participate in the kernel lifecycle so ``app.stop()`` releases the handle.

    Use this instead of :class:`CosineVectorStore` so runtime-learned examples
    (intent, planner, memory, knowledge) survive process restarts.
    """

    def __init__(self, path: str = ":memory:") -> None:
        # One connection per thread (sqlite3 connections are thread-bound).
        self._db = ThreadLocalSQLite(path, initialize=_create_vector_schema)

    def start(self) -> None:
        """Open the database connection (kernel lifecycle hook)."""
        self._db.connection()

    def stop(self) -> None:
        """Close the database connection (kernel lifecycle hook)."""
        self.close()

    def close(self) -> None:
        """Close the calling thread's database connection."""
        self._db.close()

    def upsert(
        self,
        namespace: str,
        id: str,
        vector: Sequence[float],
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        connection = self._db.connection()
        connection.execute(
            "INSERT OR REPLACE INTO vector_entries (namespace, id, vector, payload) "
            "VALUES (?, ?, ?, ?)",
            (
                namespace,
                id,
                json.dumps([float(value) for value in vector]),
                _dump(payload),
            ),
        )
        connection.commit()

    def query(
        self,
        namespace: str,
        vector: Sequence[float],
        *,
        top_k: int = 5,
        threshold: float | None = None,
    ) -> list[ScoredHit]:
        connection = self._db.connection()
        rows = connection.execute(
            "SELECT id, vector, payload FROM vector_entries WHERE namespace = ?",
            (namespace,),
        ).fetchall()
        query_vector = [float(value) for value in vector]
        scored: list[ScoredHit] = []
        for item_id, raw_vector, raw_payload in rows:
            similarity = cosine(query_vector, json.loads(raw_vector))
            if threshold is not None and similarity < threshold:
                continue
            scored.append(ScoredHit(id=item_id, score=similarity, payload=_load(raw_payload)))
        scored.sort(key=lambda hit: hit.score, reverse=True)
        return scored[:top_k]

    def delete(self, namespace: str, id: str) -> None:
        connection = self._db.connection()
        connection.execute(
            "DELETE FROM vector_entries WHERE namespace = ? AND id = ?",
            (namespace, id),
        )
        connection.commit()

    def clear(self, namespace: str) -> None:
        connection = self._db.connection()
        connection.execute(
            "DELETE FROM vector_entries WHERE namespace = ?",
            (namespace,),
        )
        connection.commit()

    def clear_all(self) -> None:
        """Drop every namespace and every vector."""
        connection = self._db.connection()
        connection.execute("DELETE FROM vector_entries")
        connection.commit()


def _dump(value: Mapping[str, Any] | None) -> str | None:
    if value is None:
        return None
    return json.dumps(dict(value), default=str)


def _load(raw: str | None) -> Mapping[str, Any] | None:
    if raw is None:
        return None
    return json.loads(raw)

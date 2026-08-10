"""SQLite-backed persistent VectorStore (RFC-0016, no dependencies)."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from typing import Any

from ..contracts.vector import ScoredHit, VectorStore
from .cosine import cosine


class SqliteVectorStore(VectorStore):
    """Persist vectors in a SQLite database using only the standard library.

    One row per ``(namespace, id)``; vectors are stored as JSON arrays and
    scored with exact cosine similarity on query. Like the other SQLite
    providers, the connection opens lazily and ``start``/``stop`` participate in
    the kernel lifecycle so ``app.stop()`` releases the handle.

    Use this instead of :class:`CosineVectorStore` so runtime-learned examples
    (intent, planner, memory, knowledge) survive process restarts.
    """

    def __init__(self, path: str = ":memory:") -> None:
        self._path = path
        self._connection: sqlite3.Connection | None = None
        self._ensure_connection()

    def _ensure_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            connection = sqlite3.connect(self._path)
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
            self._connection = connection
        return self._connection

    def start(self) -> None:
        """Open the database connection (kernel lifecycle hook)."""
        self._ensure_connection()

    def stop(self) -> None:
        """Close the database connection (kernel lifecycle hook)."""
        self.close()

    def close(self) -> None:
        """Close the underlying database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def upsert(
        self,
        namespace: str,
        id: str,
        vector: Sequence[float],
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        connection = self._ensure_connection()
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
        connection = self._ensure_connection()
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
        connection = self._ensure_connection()
        connection.execute(
            "DELETE FROM vector_entries WHERE namespace = ? AND id = ?",
            (namespace, id),
        )
        connection.commit()

    def clear(self, namespace: str) -> None:
        connection = self._ensure_connection()
        connection.execute(
            "DELETE FROM vector_entries WHERE namespace = ?",
            (namespace,),
        )
        connection.commit()

    def clear_all(self) -> None:
        """Drop every namespace and every vector."""
        connection = self._ensure_connection()
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

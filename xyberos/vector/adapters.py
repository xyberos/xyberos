"""Optional third-party vector-store adapters (lazy imports, no required deps).

Each adapter imports its backend dependency lazily on first use and raises a
clear :class:`~exceptions.provider.ProviderError` when it is not installed.
Install them via the ``vectors`` extra: ``pip install xyberos[vectors]``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, cast

from ..contracts.vector import ScoredHit, VectorStore
from ..llm.adapters import require


class ChromaVectorStore(VectorStore):
    """ChromaDB-backed :class:`VectorStore` (optional dependency: ``chromadb``).

    Each namespace maps to a Chroma collection of the same name.
    """

    def __init__(
        self,
        *,
        client: Any | None = None,
        persist_directory: str | None = None,
    ) -> None:
        self._client = client
        self._persist_directory = persist_directory

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        chromadb = require("chromadb")
        if self._persist_directory:
            self._client = chromadb.PersistentClient(path=self._persist_directory)
        else:
            self._client = chromadb.Client()
        return self._client

    def _collection(self, namespace: str) -> Any:
        return self._get_client().get_or_create_collection(name=namespace)

    def upsert(
        self,
        namespace: str,
        id: str,
        vector: Sequence[float],
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        self._collection(namespace).upsert(
            ids=[id],
            embeddings=[list(vector)],
            metadatas=[dict(payload)] if payload is not None else None,
        )

    def query(
        self,
        namespace: str,
        vector: Sequence[float],
        *,
        top_k: int = 5,
        threshold: float | None = None,
    ) -> list[ScoredHit]:
        collection = self._collection(namespace)
        if collection.count() == 0:
            return []
        result = collection.query(query_embeddings=[list(vector)], n_results=max(top_k, 1))
        ids = cast(list[list[str]], result.get("ids") or [[]])
        distances = cast(list[list[float]], result.get("distances") or [[]])
        metadatas = cast(list[list[Mapping[str, Any] | None]], result.get("metadatas") or [[]])
        hits: list[ScoredHit] = []
        for item_id, distance, metadata in zip(ids[0], distances[0], metadatas[0]):
            # Chroma returns a distance (L2 by default); invert it to a similarity.
            score = 1.0 - float(distance)
            if threshold is not None and score < threshold:
                continue
            hits.append(ScoredHit(id=item_id, score=score, payload=metadata))
        return hits

    def delete(self, namespace: str, id: str) -> None:
        self._collection(namespace).delete(ids=[id])

    def clear(self, namespace: str) -> None:
        try:
            self._get_client().delete_collection(name=namespace)
        except Exception:
            pass


class PgVectorStore(VectorStore):
    """PostgreSQL + ``pgvector`` backed :class:`VectorStore`.

    Optional dependencies: ``psycopg`` and ``pgvector`` (or ``psycopg[binary]``).
    Requires a running Postgres server with the ``vector`` extension available;
    the table is created lazily on first use with the configured dimension.
    """

    def __init__(
        self,
        connection_string: str,
        *,
        table: str = "xyberos_vectors",
        dim: int = 1536,
    ) -> None:
        if not connection_string:
            raise ValueError("connection_string must be provided")
        if dim <= 0:
            raise ValueError("dim must be a positive integer")
        self._dsn = connection_string
        self._table = table
        self._dim = dim
        self._connection: Any | None = None

    def _get_connection(self) -> Any:
        if self._connection is not None:
            return self._connection
        psycopg = require("psycopg")
        register_vector = require("pgvector.psycopg").register_vector
        connection = psycopg.connect(self._dsn)
        register_vector(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                f'CREATE TABLE IF NOT EXISTS "{self._table}" ('
                "namespace TEXT NOT NULL, "
                "id TEXT NOT NULL, "
                f"embedding vector({self._dim}), "
                "payload JSONB, "
                "PRIMARY KEY (namespace, id))"
            )
        connection.commit()
        self._connection = connection
        return connection

    def upsert(
        self,
        namespace: str,
        id: str,
        vector: Sequence[float],
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        connection = self._get_connection()
        payload_text = json.dumps(dict(payload)) if payload is not None else None
        with connection.cursor() as cursor:
            cursor.execute(
                f'INSERT INTO "{self._table}" (namespace, id, embedding, payload) '
                "VALUES (%s, %s, %s::vector, %s::jsonb) "
                "ON CONFLICT (namespace, id) DO UPDATE SET "
                "embedding = EXCLUDED.embedding, payload = EXCLUDED.payload",
                (namespace, id, list(vector), payload_text),
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
        connection = self._get_connection()
        params: list[Any] = [namespace, list(vector)]
        sql = (
            f'SELECT id, 1 - (embedding <=> %s::vector) AS score, payload '
            f'FROM "{self._table}" WHERE namespace = %s'
        )
        if threshold is not None:
            sql += " AND 1 - (embedding <=> %s::vector) >= %s"
            params.extend([list(vector), threshold])
        sql += " ORDER BY embedding <=> %s::vector LIMIT %s"
        params.extend([list(vector), max(top_k, 1)])
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        return [ScoredHit(id=row[0], score=float(row[1]), payload=row[2]) for row in rows]

    def delete(self, namespace: str, id: str) -> None:
        connection = self._get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                f'DELETE FROM "{self._table}" WHERE namespace = %s AND id = %s',
                (namespace, id),
            )
        connection.commit()

    def clear(self, namespace: str) -> None:
        connection = self._get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                f'DELETE FROM "{self._table}" WHERE namespace = %s',
                (namespace,),
            )
        connection.commit()


__all__ = ["ChromaVectorStore", "PgVectorStore"]

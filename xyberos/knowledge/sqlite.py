"""SQLite-backed persistent implementation of the Knowledge contract."""

import json
import sqlite3
from typing import Any

from ..contracts.knowledge import Knowledge
from ..utils.sqlite import ThreadLocalSQLite


def _create_knowledge_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS knowledge_facts "
        "(keyword TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    connection.commit()


class SqliteKnowledge(Knowledge):
    """Persist keyword facts in a SQLite database.

    Mirrors :class:`~knowledge.in_memory.InMemoryKnowledge`: facts are keyed by
    keyword and ``query`` returns the facts whose keyword appears in the
    context prompt. Values are JSON-encoded so any JSON-serializable value
    round-trips. Connections are opened lazily, one per thread, and
    ``start``/``stop`` participate in the kernel lifecycle.
    """

    def __init__(self, path: str = ":memory:") -> None:
        # One connection per thread (sqlite3 connections are thread-bound).
        self._db = ThreadLocalSQLite(path, initialize=_create_knowledge_schema)

    def start(self) -> None:
        """Open the database connection (kernel lifecycle hook)."""
        self._db.connection()

    def stop(self) -> None:
        """Close the database connection (kernel lifecycle hook)."""
        self.close()

    def close(self) -> None:
        """Close the calling thread's database connection."""
        self._db.close()

    def query(self, context: object) -> dict[str, Any]:
        """Return facts whose keyword appears in the context prompt."""
        prompt = str(getattr(context, "prompt", ""))
        rows = self._db.connection().execute(
            "SELECT keyword, value FROM knowledge_facts"
        ).fetchall()
        return {key: json.loads(value) for key, value in rows if key in prompt}

    def add(self, key: str, value: Any) -> None:
        """Register a fact under a keyword, replacing any existing value."""
        connection = self._db.connection()
        connection.execute(
            "INSERT OR REPLACE INTO knowledge_facts (keyword, value) VALUES (?, ?)",
            (key, json.dumps(value, default=str)),
        )
        connection.commit()

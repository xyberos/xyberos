"""SQLite-backed persistent implementation of the Knowledge contract."""

import json
import sqlite3
from typing import Any

from ..contracts.knowledge import Knowledge


class SqliteKnowledge(Knowledge):
    """Persist keyword facts in a SQLite database.

    Mirrors :class:`~knowledge.in_memory.InMemoryKnowledge`: facts are keyed by
    keyword and ``query`` returns the facts whose keyword appears in the
    context prompt. Values are JSON-encoded so any JSON-serializable value
    round-trips. The connection is opened lazily and ``start``/``stop``
    participate in the kernel lifecycle.
    """

    def __init__(self, path: str = ":memory:") -> None:
        self._path = path
        self._connection: sqlite3.Connection | None = None
        self._ensure_connection()

    def _ensure_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            connection = sqlite3.connect(self._path)
            connection.execute(
                "CREATE TABLE IF NOT EXISTS knowledge_facts "
                "(keyword TEXT PRIMARY KEY, value TEXT NOT NULL)"
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

    def query(self, context: object) -> dict[str, Any]:
        """Return facts whose keyword appears in the context prompt."""
        prompt = str(getattr(context, "prompt", ""))
        rows = self._ensure_connection().execute(
            "SELECT keyword, value FROM knowledge_facts"
        ).fetchall()
        return {key: json.loads(value) for key, value in rows if key in prompt}

    def add(self, key: str, value: Any) -> None:
        """Register a fact under a keyword, replacing any existing value."""
        connection = self._ensure_connection()
        connection.execute(
            "INSERT OR REPLACE INTO knowledge_facts (keyword, value) VALUES (?, ?)",
            (key, json.dumps(value, default=str)),
        )
        connection.commit()

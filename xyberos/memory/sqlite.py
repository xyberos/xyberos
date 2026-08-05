"""SQLite-backed persistent implementation of the Memory contract."""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..contracts.memory import Memory


@dataclass
class MemoryEntry:
    """A reconstructable snapshot of one stored execution context."""

    prompt: str | None = None
    response: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    plan: Any | None = None
    error: str | None = None
    created_at: str = ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, default=str)


def _load(raw: str | None) -> Any:
    if raw is None:
        return None
    return json.loads(raw)


class SqliteMemory(Memory):
    """Persist execution contexts in a SQLite database.

    One row per ``store`` call; ``retrieve`` returns the stored rows as
    :class:`MemoryEntry` records in insertion order (oldest first). Data
    survives process restarts when a file path is used instead of ``:memory:``.
    The connection is opened lazily, and ``start``/``stop`` participate in the
    kernel lifecycle so ``app.stop()`` releases the database handle.
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
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt TEXT,
                    response TEXT,
                    metadata TEXT,
                    plan TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL
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

    def retrieve(self, context: object) -> list[MemoryEntry]:
        """Return all stored entries, oldest first."""
        connection = self._ensure_connection()
        rows = connection.execute(
            "SELECT prompt, response, metadata, plan, error, created_at "
            "FROM memory_entries ORDER BY id ASC"
        ).fetchall()
        return [
            MemoryEntry(
                prompt=row[0],
                response=row[1],
                metadata=_load(row[2]) or {},
                plan=_load(row[3]),
                error=row[4],
                created_at=row[5],
            )
            for row in rows
        ]

    def store(self, context: object) -> None:
        """Persist the supplied execution context as one row."""
        connection = self._ensure_connection()
        connection.execute(
            "INSERT INTO memory_entries (prompt, response, metadata, plan, error, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                getattr(context, "prompt", None),
                getattr(context, "response", None),
                _dump(getattr(context, "metadata", None) or {}),
                _dump(getattr(context, "plan", None)),
                _dump(getattr(context, "error", None)),
                _utc_now(),
            ),
        )
        connection.commit()

    def clear(self) -> None:
        """Remove all stored entries."""
        connection = self._ensure_connection()
        connection.execute("DELETE FROM memory_entries")
        connection.commit()

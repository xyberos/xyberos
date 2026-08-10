"""SQLite-backed persistent implementation of the Memory contract."""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..contracts.memory import Memory
from ..utils.sqlite import ThreadLocalSQLite


def _empty_metadata() -> dict[str, Any]:
    """Typed factory so Pylance infers ``dict[str, Any]``, not ``Unknown``."""
    return {}


@dataclass
class MemoryEntry:
    """A reconstructable snapshot of one stored execution context."""

    prompt: str | None = None
    response: str | None = None
    metadata: dict[str, Any] = field(default_factory=_empty_metadata)
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


def _create_memory_schema(connection: sqlite3.Connection) -> None:
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


class SqliteMemory(Memory):
    """Persist execution contexts in a SQLite database.

    One row per ``store`` call; ``retrieve`` returns the stored rows as
    :class:`MemoryEntry` records in insertion order (oldest first). Data
    survives process restarts when a file path is used instead of ``:memory:``.
    Connections are opened lazily, one per thread, and ``start``/``stop``
    participate in the kernel lifecycle so ``app.stop()`` releases the handle.
    """

    def __init__(self, path: str = ":memory:") -> None:
        # sqlite3 connections are bound to the thread that created them, so a
        # single shared handle crashes when a FastAPI/thread-pool touches it.
        self._db = ThreadLocalSQLite(path, initialize=_create_memory_schema)

    def start(self) -> None:
        """Open the database connection (kernel lifecycle hook)."""
        self._db.connection()

    def stop(self) -> None:
        """Close the database connection (kernel lifecycle hook)."""
        self.close()

    def close(self) -> None:
        """Close the calling thread's database connection."""
        self._db.close()

    def retrieve(self, context: object) -> list[MemoryEntry]:
        """Return all stored entries, oldest first."""
        connection = self._db.connection()
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
        connection = self._db.connection()
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
        connection = self._db.connection()
        connection.execute("DELETE FROM memory_entries")
        connection.commit()

"""SQLite-backed persistent implementation of the ExperienceStore contract."""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from ..contracts.experience import Episode, ExperienceStore
from ..contracts.intent import Intent
from ..utils.sqlite import ThreadLocalSQLite


def _dump(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, default=str)


def _load(raw: str | None) -> Any:
    if raw is None:
        return None
    return json.loads(raw)


def _create_experience_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS experience_episodes (
            id TEXT PRIMARY KEY,
            prompt TEXT NOT NULL,
            intent TEXT,
            intent_confidence REAL,
            plan TEXT,
            tool_calls TEXT,
            response TEXT,
            outcome TEXT,
            feedback REAL,
            metadata TEXT,
            created_at REAL NOT NULL
        )
        """
    )
    connection.commit()


class SqliteExperience(ExperienceStore):
    """Persist experience episodes in a SQLite database.

    One row per ``record`` call; episodes survive process restarts when a file
    path is used instead of ``:memory:``. Connections open lazily, one per
    thread, and ``start``/``stop`` participate in the kernel lifecycle so
    ``app.stop()`` releases the handle (mirrors
    :class:`~memory.sqlite.SqliteMemory`).
    """

    def __init__(self, path: str = ":memory:") -> None:
        # One connection per thread (sqlite3 connections are thread-bound).
        self._db = ThreadLocalSQLite(path, initialize=_create_experience_schema)

    def start(self) -> None:
        """Open the database connection (kernel lifecycle hook)."""
        self._db.connection()

    def stop(self) -> None:
        """Close the database connection (kernel lifecycle hook)."""
        self.close()

    def close(self) -> None:
        """Close the calling thread's database connection."""
        self._db.close()

    def record(self, episode: Episode) -> Episode:
        connection = self._db.connection()
        episode_id = episode.id or uuid4().hex
        if not episode.id:
            episode.id = episode_id
        connection.execute(
            "INSERT OR REPLACE INTO experience_episodes "
            "(id, prompt, intent, intent_confidence, plan, tool_calls, response, outcome, "
            "feedback, metadata, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                episode_id,
                episode.prompt,
                episode.intent.name if episode.intent is not None else None,
                episode.intent.confidence if episode.intent is not None else None,
                _dump(episode.plan),
                _dump(episode.tool_calls),
                episode.response,
                episode.outcome,
                episode.feedback,
                _dump(episode.metadata),
                episode.created_at,
            ),
        )
        connection.commit()
        return episode

    def query(
        self,
        *,
        intent: str | None = None,
        outcome: str | None = None,
        limit: int = 20,
    ) -> list[Episode]:
        connection = self._db.connection()
        clauses: list[str] = []
        params: list[Any] = []
        if intent is not None:
            clauses.append("intent = ?")
            params.append(intent)
        if outcome is not None:
            clauses.append("outcome = ?")
            params.append(outcome)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = connection.execute(
            "SELECT id, prompt, intent, intent_confidence, plan, tool_calls, response, outcome, "
            "feedback, metadata, created_at "
            f"FROM experience_episodes {where} ORDER BY created_at DESC LIMIT ?",
            [*params, max(limit, 1)],
        ).fetchall()
        return [_episode_from_row(row) for row in rows]

    def feedback(self, episode_id: str, rating: float, note: str | None = None) -> None:
        connection = self._db.connection()
        cursor = connection.execute(
            "UPDATE experience_episodes SET feedback = ? WHERE id = ?",
            (rating, episode_id),
        )
        if cursor.rowcount == 0:
            raise KeyError(f"no episode recorded with id {episode_id!r}")
        if note is not None:
            row = connection.execute(
                "SELECT metadata FROM experience_episodes WHERE id = ?",
                (episode_id,),
            ).fetchone()
            metadata = dict(_load(row[0]) or {})
            metadata["feedback_note"] = note
            connection.execute(
                "UPDATE experience_episodes SET metadata = ? WHERE id = ?",
                (_dump(metadata), episode_id),
            )
        connection.commit()

    def stats(self) -> Mapping[str, Any]:
        connection = self._db.connection()
        total = connection.execute("SELECT COUNT(*) FROM experience_episodes").fetchone()[0]
        by_outcome = {
            row[0]: row[1]
            for row in connection.execute(
                "SELECT outcome, COUNT(*) FROM experience_episodes GROUP BY outcome"
            ).fetchall()
        }
        by_intent = {
            row[0]: row[1]
            for row in connection.execute(
                "SELECT intent, COUNT(*) FROM experience_episodes "
                "WHERE intent IS NOT NULL GROUP BY intent"
            ).fetchall()
        }
        return {"total": total, "by_outcome": by_outcome, "by_intent": by_intent}


def _episode_from_row(row: tuple[Any, ...]) -> Episode:
    (
        episode_id,
        prompt,
        intent_name,
        intent_confidence,
        plan,
        tool_calls,
        response,
        outcome,
        feedback,
        metadata,
        created_at,
    ) = row
    intent = (
        Intent(name=intent_name, confidence=float(intent_confidence))
        if intent_name is not None
        else None
    )
    return Episode(
        id=episode_id,
        prompt=prompt,
        intent=intent,
        plan=_load(plan),
        tool_calls=list(_load(tool_calls) or []),
        response=response,
        outcome=outcome,
        feedback=feedback,
        metadata=dict(_load(metadata) or {}),
        created_at=float(created_at) if created_at is not None else time.time(),
    )

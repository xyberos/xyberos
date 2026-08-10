"""Disk checkpoints for pausable workflows."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from ..runtime.context import CognitiveContext
from ..utils.sqlite import ThreadLocalSQLite
from .graph import WorkflowRun


def run_to_dict(run: WorkflowRun) -> dict[str, Any]:
    """Serialize a :class:`WorkflowRun` to a JSON-friendly dict."""
    context = run.context
    return {
        "status": run.status,
        "node": run.node,
        "prompt": run.prompt,
        "steps": list(run.steps),
        "steps_taken": run.steps_taken,
        "context": {
            "prompt": context.prompt,
            "response": context.response,
            "metadata": context.metadata,
            "plan": context.plan,
            "error": str(context.error) if context.error is not None else None,
        },
    }


def run_from_dict(data: dict[str, Any]) -> WorkflowRun:
    """Reconstruct a :class:`WorkflowRun` from ``run_to_dict`` output."""
    context_data = data["context"]
    context = CognitiveContext(
        prompt=context_data["prompt"],
        response=context_data["response"],
        metadata=context_data["metadata"],
        error=None,
        plan=context_data["plan"],
    )
    return WorkflowRun(
        status=data["status"],
        context=context,
        node=data["node"],
        prompt=data["prompt"],
        steps=tuple(data["steps"]),
        steps_taken=data["steps_taken"],
    )


def _create_checkpoint_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS workflow_checkpoints "
        "(run_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
    )
    connection.commit()


class WorkflowCheckpoint:
    """Persist paused :class:`~workflows.graph.WorkflowRun` records to SQLite.

    Lets a paused graph be saved and resumed in a later process::

        checkpoint = WorkflowCheckpoint("runs.db")
        checkpoint.save(run_id, paused_run)      # pause session ends here
        ...
        restored = checkpoint.load(run_id)       # new process
        graph.resume(restored, value)
    """

    def __init__(self, path: str = ":memory:") -> None:
        # One connection per thread (sqlite3 connections are thread-bound).
        self._db = ThreadLocalSQLite(path, initialize=_create_checkpoint_schema)

    def close(self) -> None:
        """Close the calling thread's database connection."""
        self._db.close()

    def save(self, run_id: str, run: WorkflowRun) -> None:
        """Persist ``run`` under ``run_id``, replacing any existing record."""
        connection = self._db.connection()
        connection.execute(
            "INSERT OR REPLACE INTO workflow_checkpoints (run_id, payload) VALUES (?, ?)",
            (run_id, json.dumps(run_to_dict(run), default=str)),
        )
        connection.commit()

    def load(self, run_id: str) -> WorkflowRun:
        """Return the run stored under ``run_id``."""
        row = self._db.connection().execute(
            "SELECT payload FROM workflow_checkpoints WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"no checkpoint with run_id: {run_id}")
        return run_from_dict(json.loads(row[0]))

    def delete(self, run_id: str) -> None:
        """Remove the checkpoint stored under ``run_id``."""
        connection = self._db.connection()
        connection.execute(
            "DELETE FROM workflow_checkpoints WHERE run_id = ?", (run_id,)
        )
        connection.commit()

    def list_ids(self) -> tuple[str, ...]:
        """Return all stored checkpoint ids."""
        rows = self._db.connection().execute("SELECT run_id FROM workflow_checkpoints").fetchall()
        return tuple(row[0] for row in rows)

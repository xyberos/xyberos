"""Disk checkpoints for pausable workflows."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from ..runtime.context import CognitiveContext
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
        self._connection = sqlite3.connect(path)
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS workflow_checkpoints "
            "(run_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
        )
        self._connection.commit()

    def close(self) -> None:
        """Close the underlying database connection."""
        self._connection.close()

    def save(self, run_id: str, run: WorkflowRun) -> None:
        """Persist ``run`` under ``run_id``, replacing any existing record."""
        self._connection.execute(
            "INSERT OR REPLACE INTO workflow_checkpoints (run_id, payload) VALUES (?, ?)",
            (run_id, json.dumps(run_to_dict(run), default=str)),
        )
        self._connection.commit()

    def load(self, run_id: str) -> WorkflowRun:
        """Return the run stored under ``run_id``."""
        row = self._connection.execute(
            "SELECT payload FROM workflow_checkpoints WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"no checkpoint with run_id: {run_id}")
        return run_from_dict(json.loads(row[0]))

    def delete(self, run_id: str) -> None:
        """Remove the checkpoint stored under ``run_id``."""
        self._connection.execute(
            "DELETE FROM workflow_checkpoints WHERE run_id = ?", (run_id,)
        )
        self._connection.commit()

    def list_ids(self) -> tuple[str, ...]:
        """Return all stored checkpoint ids."""
        rows = self._connection.execute("SELECT run_id FROM workflow_checkpoints").fetchall()
        return tuple(row[0] for row in rows)

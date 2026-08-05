"""Errors and control-flow signals for workflow execution."""

from typing import Any


class WorkflowError(Exception):
    """Raised when a workflow cannot start or finish (e.g. max steps exceeded)."""


class WorkflowPaused(Exception):
    """Control-flow signal: a workflow step paused awaiting external input.

    A step raises this to pause the graph for human-in-the-loop input. The
    graph attaches the paused :class:`~workflows.graph.WorkflowRun` to ``run``
    so callers can inspect ``prompt`` and resume with a value.
    """

    def __init__(self, prompt: str = "") -> None:
        super().__init__(prompt or "workflow paused")
        self.prompt = prompt
        self.run: Any | None = None

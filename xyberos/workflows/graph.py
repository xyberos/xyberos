"""State-graph workflow engine with branches, loops, and pause/resume."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..contracts.workflow import Workflow
from ..exceptions.workflow import WorkflowError, WorkflowPaused
from ..runtime.context import CognitiveContext
from .sequential import WorkflowStep


# A conditional router: given the current context, return the next node name,
# or ``None`` to end execution.
NodeRoute = Callable[[CognitiveContext], str | None]


@dataclass
class WorkflowRun:
    """The outcome of a graph execution — either completed or paused."""

    status: str
    context: CognitiveContext
    node: str | None = None
    prompt: str | None = None
    steps: tuple[str, ...] = ()
    steps_taken: int = 0


class GraphWorkflow(Workflow):
    """A directed graph of named steps with fixed and conditional edges.

    Each node is a :data:`~workflows.sequential.WorkflowStep` (a callable that
    receives and optionally replaces the ``CognitiveContext``). A node may also
    define a ``route`` — a callable that returns the name of the next node (or
    ``None`` to end). Edges back to earlier nodes create loops; ``max_steps``
    guards against runaway iteration.

    A step may raise :class:`~exceptions.workflow.WorkflowPaused` to pause the
    graph awaiting external (human) input. ``execute`` returns a paused
    :class:`WorkflowRun`; ``resume`` re-runs the paused node with a value
    injected into ``context.metadata["workflow.resume_value"]`` and continues.
    ``run`` implements the :class:`~contracts.workflow.Workflow` contract: it
    returns the final context on completion and raises ``WorkflowPaused`` (with
    the run attached) when the graph pauses.

    Example::

        graph = GraphWorkflow("start")
        graph.add_node("start", start_step)
        graph.add_node("review", review_step)
        graph.add_edge("start", "review")

        run = graph.execute(CognitiveContext("task"))
        while run.status == "paused":
            value = input(run.prompt)
            run = graph.resume(run, value)
        print(run.context.response)
    """

    RESUME_KEY = "workflow.resume_value"

    def __init__(self, entry: str, *, max_steps: int = 100) -> None:
        if not isinstance(entry, str) or not entry.strip():  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
            raise ValueError("entry node must be a non-empty string")
        if max_steps < 1:
            raise ValueError("max_steps must be a positive integer")
        self._entry = entry
        self._max_steps = max_steps
        self._nodes: dict[str, WorkflowStep] = {}
        self._edges: dict[str, str] = {}
        self._routes: dict[str, NodeRoute] = {}

    @property
    def entry(self) -> str:
        """The node where execution begins."""
        return self._entry

    @property
    def nodes(self) -> tuple[str, ...]:
        """Registered node names in registration order."""
        return tuple(self._nodes)

    def add_node(self, name: str, step: WorkflowStep) -> "GraphWorkflow":
        """Register a named step and return the graph for chaining."""
        if not isinstance(name, str) or not name.strip():  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
            raise ValueError("node name must be a non-empty string")
        if name in self._nodes:
            raise ValueError(f"node already registered: {name}")
        if not callable(step):
            raise TypeError("node step must be callable")
        self._nodes[name] = step
        return self

    def add_edge(self, source: str, target: str) -> "GraphWorkflow":
        """Route from ``source`` to ``target`` unconditionally."""
        self._require_node(source)
        self._require_node(target)
        if source in self._routes or source in self._edges:
            raise ValueError(f"node '{source}' already has an edge or route")
        self._edges[source] = target
        return self

    def add_route(self, source: str, route: NodeRoute) -> "GraphWorkflow":
        """Route from ``source`` conditionally based on the context."""
        self._require_node(source)
        if not callable(route):
            raise TypeError("route must be callable")
        if source in self._edges or source in self._routes:
            raise ValueError(f"node '{source}' already has an edge or route")
        self._routes[source] = route
        return self

    def execute(self, context: object) -> WorkflowRun:
        """Run the graph and return a completed or paused :class:`WorkflowRun`."""
        return self._execute(context, self._entry)

    def run(self, context: object) -> CognitiveContext:
        """Run to completion and return the final context.

        Implements the :class:`~contracts.workflow.Workflow` contract. If the
        graph pauses, raises :class:`~exceptions.workflow.WorkflowPaused` with
        the paused run attached.
        """
        result = self._execute(context, self._entry)
        if result.status == "paused":
            pause = WorkflowPaused(prompt=result.prompt or "")
            pause.run = result
            raise pause
        return result.context

    def resume(self, run: WorkflowRun, value: Any = None) -> WorkflowRun:
        """Resume a paused run with external input and return the new run."""
        if run.status != "paused":
            raise ValueError("only a paused run can be resumed")
        if run.node is None:
            raise ValueError("paused run has no node to resume")
        self._require_node(run.node)
        run.context.metadata[self.RESUME_KEY] = value
        return self._execute(
            run.context,
            run.node,
            prior_steps=list(run.steps),
            prior_count=run.steps_taken,
        )

    def resume_from_checkpoint(self, checkpoint: Any, run_id: str, value: Any = None) -> WorkflowRun:
        """Resume a paused run restored from ``checkpoint`` under ``run_id``.

        ``checkpoint`` is any object exposing ``load(run_id) -> WorkflowRun``
        (e.g. :class:`~workflows.checkpoint.WorkflowCheckpoint`).
        """
        return self.resume(checkpoint.load(run_id), value)

    def _execute(
        self,
        context: object,
        node: str | None,
        *,
        prior_steps: list[str] | None = None,
        prior_count: int = 0,
    ) -> WorkflowRun:
        if not isinstance(context, CognitiveContext):
            raise TypeError("context must be a CognitiveContext")
        if node not in self._nodes:
            raise WorkflowError(f"entry node not found: {node}")

        steps = list(prior_steps or [])
        count = prior_count
        current = context

        while node is not None:
            step = self._nodes[node]
            count += 1
            if count > self._max_steps:
                raise WorkflowError(f"workflow exceeded max steps ({self._max_steps})")
            steps.append(node)

            try:
                result = step(current)
            except WorkflowPaused as pause:
                return WorkflowRun(
                    status="paused",
                    context=current,
                    node=node,
                    prompt=pause.prompt or None,
                    steps=tuple(steps),
                    steps_taken=count,
                )

            if result is not None:
                if not isinstance(result, CognitiveContext):  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
                    raise TypeError("workflow steps must return a CognitiveContext or None")
                current = result

            node = self._next(node, current)

        return WorkflowRun(
            status="completed",
            context=current,
            node=steps[-1] if steps else None,
            steps=tuple(steps),
            steps_taken=count,
        )

    def _next(self, node: str, context: CognitiveContext) -> str | None:
        if node in self._routes:
            next_node = self._routes[node](context)
            if next_node is not None and next_node not in self._nodes:
                raise WorkflowError(f"route returned unknown node: {next_node}")
            return next_node
        return self._edges.get(node)

    def _require_node(self, name: str) -> None:
        if name not in self._nodes:
            raise ValueError(f"unknown node: {name}")

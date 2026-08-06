RFC-0011 — Workflows

Title: Workflow Extension Contract

Status: Accepted

Summary

Defines the Workflows subsystem — composable execution graphs that orchestrate
multi-step processes with branching, looping, and human-in-the-loop pause/resume.

Motivation

Not every request is a single LLM call. Refunds need approval, onboarding needs
sequential steps, and diagnostics need branching logic. Workflows encode these
as directed graphs that the Brain runs before generating a final response.

Contract

```python
class Workflow(ABC):

    @abstractmethod
    def run(self, context: object) -> object:
        """Run the workflow and return its resulting context."""
```

Implementations

### SequentialWorkflow

A linear chain of ``WorkflowStep`` callables. Each step receives and optionally
replaces the ``CognitiveContext``. Steps run in insertion order.

### GraphWorkflow

A directed graph with named nodes, fixed edges, and conditional routes:

```python
graph = GraphWorkflow("start")
graph.add_node("start", start_step)
graph.add_node("review", review_step)
graph.add_edge("start", "review")
graph.add_route("review", decide_next)  # conditional: returns next node or None
```

Features:
- **Branches** — ``add_route`` lets a node dynamically pick the next step
- **Loops** — edges back to earlier nodes with ``max_steps`` guard
- **Pause/Resume** — a step raises ``WorkflowPaused`` to await human input;
  ``execute`` returns a ``WorkflowRun`` with ``status="paused"``
- **Checkpoints** — ``WorkflowCheckpoint`` persists paused runs to SQLite for
  cross-restart resume via ``resume_from_checkpoint``

### WorkflowRun

```python
@dataclass
class WorkflowRun:
    status: str        # "completed" | "paused"
    context: CognitiveContext
    node: str | None
    prompt: str | None   # human-readable prompt when paused
    steps: tuple[str, ...]
    steps_taken: int
```

Pipeline Integration

Workflows run first in the Brain pipeline. A step that sets ``context.response``
causes the pipeline to short-circuit — no LLM call is made:

```text
Workflow (optional, runs first)
  ↓
Memory (retrieve) → Knowledge → Planner → Tools → LLM
```

If the workflow pauses, the Brain and Runtime propagate the pause (not an
error), so ``app.run()`` / ``app.chat()`` surfaces it cleanly.

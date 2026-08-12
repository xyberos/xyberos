# 8. Give It Plans & Workflows

[**← Previous**](07-tools.md) · [**Next →**](09-plugins.md)

## What You'll Learn

- What a workflow is
- Simple / sequential workflows
- Conditional workflows (branches)
- Loops
- Human-in-the-loop (pause/resume)
- Planning vs. workflow
- Planners (sequential, LLM, adaptive, reflective)
- Custom planner

---

## What is a workflow?

A **workflow** is a predefined process — an ordered sequence of steps that
transform a request.

```text
Input → Step 1 → Step 2 → Step 3 → Output
```

> **Workflow vs. Planning**
>
> - **Workflow** = a predefined process (you wrote the steps).
> - **Planning** = a process dynamically determined by the system (the planner
>   decides the steps at runtime).

## Sequential workflow

```python
from xyberos.runtime.context import CognitiveContext
from xyberos.workflows import SequentialWorkflow

def annotate(context):
    context.metadata["annotated"] = True

def respond(context):
    context.response = f"processed: {context.prompt}"
    return context

workflow = SequentialWorkflow([annotate, respond])
result = workflow.run(CognitiveContext("hello"))
print(result.response)   # processed: hello
```

Step behavior:

- return `None` to keep the current context
- return a new `CognitiveContext` to replace it
- raise an exception to stop execution

## Conditional workflows (graph)

`GraphWorkflow` builds a directed graph of named steps with fixed edges and
conditional routes — branches and loops:

```python
from xyberos.workflows import GraphWorkflow

graph = GraphWorkflow("research_flow")
graph.add_node("analyze", analyze_step)
graph.add_node("answer", answer_step)
graph.add_edge("analyze", "answer")          # fixed path
graph.add_route("analyze", lambda ctx: "answer")  # conditional routing
```

```text
Request
 ↓
Is this a research task?
 ├── Yes → Research workflow
 └── No  → Normal response
```

## Human-in-the-loop (pause/resume)

A step raises `WorkflowPaused` to pause for a human decision; `resume` continues:

```python
from xyberos.exceptions import WorkflowPaused
from xyberos.workflows import GraphWorkflow

def verify(context):
    if GraphWorkflow.RESUME_KEY in context.metadata:
        decision = context.metadata[GraphWorkflow.RESUME_KEY]
        context.response = "approved" if decision == "yes" else "rejected"
        return context
    raise WorkflowPaused(prompt="Approve this refund? Reply yes or no.")

graph = GraphWorkflow("verify")
graph.add_node("verify", verify)

run = graph.execute(CognitiveContext("refund A-100"))
print(run.status)     # paused
print(run.prompt)     # Approve this refund? Reply yes or no.

run = graph.resume(run, "yes")
print(run.context.response)   # approved
```

Pause a run **across restarts** with a checkpoint:

```python
from xyberos.workflows import WorkflowCheckpoint

checkpoint = WorkflowCheckpoint("runs.db")
run = graph.execute(CognitiveContext("refund B-300"))
checkpoint.save("run-1", run)          # persist the pause
# ...server restarts...
restored = checkpoint.load("run-1")
graph.resume(restored, "no")           # -> context.response == "rejected"
```

## Planning

Planning produces an ordered plan for a request. The default
`SequentialPlanner` returns a fixed step list:

```python
from xyberos.planner import SequentialPlanner
from xyberos.runtime.context import CognitiveContext

planner = SequentialPlanner()
print(planner.plan(CognitiveContext("ship the feature")))
```

Custom steps:

```python
planner = SequentialPlanner(("analyze", "draft", "verify"))
```

## LLM-driven planning

`LLMPlanner` asks the model to break a request into ordered steps:

```python
from xyberos.planner import LLMPlanner
from xyberos.llm import CallableLLM

planner = LLMPlanner(CallableLLM(lambda p: "research\ndraft\nreview"))
print(planner.plan(CognitiveContext("build a report")))   # ['research', 'draft', 'review']
```

Feed the plan to the model prompt with `config={"brain.inject_plan": True}`:

```python
from xyberos import create_app

app = create_app(
    config={"brain.inject_plan": True},
    planner=LLMPlanner(your_llm),
)
```

## Adaptive & reflective planning

- **`AdaptivePlanner`** — few-shot planning: retrieves the most similar past
  `request → plan` examples and follows that style. `learn(request, plan)`
  records new examples, so it improves by accumulation.
- **`ReflectivePlanner`** — scores plan confidence and revises the plan before
  execution.

```python
from xyberos.planner import AdaptivePlanner

planner = AdaptivePlanner(app.llm, store=store, embedder=embedder)
planner.learn("refund an order", ["check order", "process refund", "confirm"])
```

## Plan execution

`PlanExecutor` closes the loop — executes plan steps through tools/callables,
verifies each, and re-plans on failure:

```python
from xyberos.planner import PlanExecutor

result = executor.execute(ctx, plan)
```

## Custom planner

Implement the `Planner` contract (`plan(context) -> list[str]`):

```python
from xyberos.contracts.planner import Planner

class MyPlanner(Planner):
    def plan(self, context):
        return ["step_a", "step_b"]

app = create_app(planner=MyPlanner())
```

## Default behavior

- `create_app()` wires a `SequentialWorkflow` and a `SequentialPlanner`.
- The brain runs the workflow's pre-steps first; a step that sets the response
  short-circuits the pipeline.

## Common mistakes

- **Confusing workflows and planning** — use a workflow for *known* steps;
  use a planner for *derived* steps.
- **Not handling `WorkflowPaused`** — a paused run isn't finished; drive it to
  completion with `resume`.
- **Expecting LLM planning without a model** — `LLMPlanner` needs an
  `LLMProvider`; the default `EchoLLM` won't decompose real tasks.

## Next Step

[**9. Skills & Plugins**](09-plugins.md) — package capabilities and let modules
register themselves.

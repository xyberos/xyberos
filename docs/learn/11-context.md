# 11. Context

[**← Previous**](10-brain.md) · [**Next →**](12-agents.md)

## What You'll Learn

- What context is
- Context sources
- Inspecting context
- Context assembly
- Metadata
- Custom context usage

---

## What is context?

**Context is the state object that flows through the whole pipeline.** Every
request gets a `CognitiveContext`; each subsystem reads from it and writes to
it. `app.run()` returns it; `app.chat()` returns just the text.

```python
from xyberos import create_app

app = create_app()
ctx = app.run("Hello, world!")

print(ctx.prompt)      # the input
print(ctx.response)    # the model's reply
print(ctx.succeeded)   # True when there was no error
print(ctx.error)       # the error, if any
print(ctx.plan)        # the plan produced by the planner
print(ctx.intent)      # the classified intent (when enabled)
print(ctx.metadata)    # open-ended dict you can attach anything to
```

## Context sources

The context carries data from many places:

```text
User Input     → context.prompt
Conversation   → memory retrieval
Knowledge      → relevant facts
Intent         → context.intent
Plan           → context.plan
Tools          → tool results
Workflow       → context.metadata
Response       → context.response
```

## Build a context manually

You can construct one directly — handy for tools and workflows:

```python
from xyberos.runtime.context import CognitiveContext

ctx = CognitiveContext("tell me about refunds")
ctx.metadata["user_id"] = "u-123"
```

## Context assembly

The `Brain._prepare` step runs the workflow, then enriches the prompt with
memory and knowledge, records the plan, and optionally runs the router — all
state lands on the context. The enriched prompt is surfaced on
`context.enriched_prompt`, so you can inspect exactly what the model saw:

```python
ctx = app.run("what are your hours?")
print(ctx.enriched_prompt)
```

## Metadata

`metadata` is an open-ended dict you can attach anything to — user IDs, request
IDs, flags. Workflows use it heavily (e.g. `GraphWorkflow.RESUME_KEY` holds the
resume value).

```python
ctx = app.run("hello", metadata={"user_id": "u-123"})
print(ctx.metadata["user_id"])
```

## Custom context providers

Context is not a plugin surface by itself — but you shape it through the
workflow pre-steps and providers that read/write it. For example, a workflow
step can enrich the context before the model runs:

```python
def stamp_user(context):
    context.metadata["user"] = "u-123"
    return context
```

## Default behavior

- `app.run(prompt, metadata=None)` creates a fresh `CognitiveContext` with your
  prompt and optional metadata.
- `chat()` / `achat()` return only `.response` (raising `RuntimeError` if the
  pipeline produced none).

## Common mistakes

- **Forgetting `run()` returns an object** — use `.response` for the text or
  `chat()` for convenience.
- **Mutating context in tools expecting no side effects** — steps may replace
  the context; keep transforms explicit.
- **Ignoring `succeeded` / `error`** — check them for robust error handling.

## Next Step

[**12. Multi-Agent Systems**](12-agents.md) — give your assistant teammates.

# 14. Observability & Debugging

[**← Previous**](13-configuration.md) · [**Next →**](15-security.md)

## What You'll Learn

- Logging
- Debugging requests (the context)
- Execution traces (events)
- Workflow inspection
- Tool execution logs
- Metrics / event recording
- Error handling & troubleshooting

---

## Logging

Log through `app.logger`:

```python
from xyberos import create_app

app = create_app()
app.logger.info("starting up")
```

## Debugging requests

`app.run()` returns the full `CognitiveContext` — the fastest debugging tool:

```python
ctx = app.run("what are your hours?")
print(ctx.succeeded)          # True / False
print(ctx.error)              # the error, if any
print(ctx.plan)               # the computed plan
print(ctx.intent)             # the classified intent (when enabled)
print(ctx.enriched_prompt)    # exactly what the model saw
print(ctx.metadata)           # anything attached along the way
```

## Execution traces (events)

Every layer publishes to the event bus (`app.events`). Subscribe to watch the
pipeline run:

```python
from xyberos.events import (
    REQUEST_STARTED,
    RESPONSE_PRODUCED,
    MEMORY_STORED,
    KNOWLEDGE_QUERIED,
    TOOL_DISPATCHED,
    BRAIN_ERROR,
)

app.events.subscribe(REQUEST_STARTED, lambda e: print("request:", e.data))
app.events.subscribe(RESPONSE_PRODUCED, lambda e: print("response:", e.data["response"]))
app.events.subscribe(BRAIN_ERROR, lambda e: print("failed:", e.data))
```

Canonical event names are exported from `xyberos.events`:

- **Lifecycle** — `kernel.started`, `kernel.stopped`, `plugin.loaded`
- **Request** — `runtime.request_started`, `runtime.request_completed`,
  `runtime.request_failed`
- **Brain** — `brain.workflow_run`, `brain.memory_retrieved`,
  `brain.memory_stored`, `brain.knowledge_queried`, `brain.plan_created`,
  `brain.tool_dispatched`, `brain.response_produced`, `brain.token_streamed`,
  `brain.error`
- **Trainable engines** — `brain.intent_classified`,
  `brain.episode_recorded`, `brain.feedback_recorded`
- **Router** — `brain.responder_hit`, `brain.escalated`, `brain.degraded`,
  `brain.cache_hit`
- **Security** — `security.kill_engaged`, `security.kill_disengaged`,
  `security.request_blocked`

A listener that raises is logged and isolated — it never breaks the pipeline.

## Record everything

`EventRecorder` records every event with per-name counts and exporters:

```python
from xyberos.events import EventRecorder, LoggingExporter

recorder = EventRecorder(limit=10_000).subscribe_to(app.events)
recorder.add_exporter(LoggingExporter(app.logger))

app.chat("hello")
print(recorder.counts())   # {'brain.response_produced': 1, ...}
```

Any callable `event -> None` can be an exporter, so wiring a metrics/tracing
backend is just a function.

## Workflow inspection

Workflow runs expose their state:

```python
run = graph.execute(context)
print(run.status)    # 'completed' or 'paused'
print(run.prompt)    # the pause prompt, when paused
print(run.steps)     # the trace of executed steps
```

## Tool execution logs

Tool dispatch is observable via the `brain.tool_dispatched` event and the
`ToolRunner` result. For fine-grained control, wrap tool execution:

```python
app.events.subscribe(TOOL_DISPATCHED, lambda e: print("tool:", e.data))
```

## Metrics

`xyberos.utils` also ships evaluation metrics for the learning layer:
`intent_accuracy`, `plan_success_rate`, and `retrieval_recall_at_k` (see
[Training Tutorial](22-training-tutorial.md)).

## Error handling

Prefer checking the context for expected failures:

```python
ctx = app.run("hello")
if not ctx.succeeded:
    print(ctx.error)
```

Domain exceptions are typed in `xyberos.exceptions` — `SecurityHaltError`,
`WorkflowPaused`, `ToolArgumentError`, `ProviderError`,
`StructuredOutputError`, `GuardrailTriggeredError`.

## Troubleshooting

- **"No response produced"** — `chat()` raised `RuntimeError`; check
  `ctx.succeeded` / `ctx.error` via `run()`.
- **Semantic tiers not matching** — you need a real embedder, not `HashEmbedder`.
- **Wrong model behavior** — inspect `ctx.enriched_prompt` to see what the
  model actually saw.
- **Providers not taking effect** — the brain captures providers at
  construction; rebuild the app or use plugins.

## Default behavior

- Logging is available via `app.logger`; events are published on every request.
- No metrics are exported by default — attach exporters as needed.

## Common mistakes

- **Relying on `print` inside the brain** — use events; they're the supported
  observation surface.
- **Forgetting a listener can be isolated** — subscribers that raise are
  logged and isolated, so debugging them requires reading the logs.
- **Inspecting `metadata` instead of `enriched_prompt`** — the enriched prompt
  is the ground truth for what the model saw.

## Next Step

[**15. Security**](15-security.md) — kill switch, guardrails, and audit.

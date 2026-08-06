RFC-0014 — Events

Title: Event Bus and Observability

Status: Accepted

Summary

Defines the Events subsystem — a publish/subscribe event bus for pipeline
observability, lifecycle hooks, and tracing that allows external consumers to
monitor and react to every stage of execution.

Motivation

Production systems need observability: what happened, when, in what order, and
with what outcome. An event bus lets logging, metrics, tracing, and custom
hooks observe the pipeline without coupling to internals.

Architecture

### EventBus

A lightweight pub/sub bus owned by the Kernel:

```python
bus = EventBus()
bus.subscribe("brain.response_produced", my_listener)
bus.emit("brain.response_produced", context=ctx, data={"response": "..."})
bus.unsubscribe("brain.response_produced", my_listener)
```

- Multiple listeners per event name
- Listener failures are logged and isolated — never break the pipeline
- Async-safe: listeners run synchronously on the emitting thread

### Event

```python
@dataclass
class Event:
    name: str
    context: CognitiveContext | None
    data: dict[str, Any]
    timestamp: float
```

Canonical Event Names

| Event | Emitted When |
|---|---|
| ``kernel.started`` | Kernel startup completes |
| ``kernel.stopped`` | Kernel shutdown begins |
| ``plugin.loaded`` | A plugin is successfully loaded |
| ``plugin.unloaded`` | A plugin is unloaded |
| ``runtime.request_started`` | A new request begins execution |
| ``runtime.request_completed`` | A request finishes successfully |
| ``runtime.request_failed`` | A request raises an exception |
| ``brain.workflow_run`` | The workflow step executes |
| ``brain.memory_retrieved`` | Memory is fetched for the context |
| ``brain.memory_stored`` | The turn is persisted |
| ``brain.knowledge_queried`` | Knowledge facts are queried |
| ``brain.plan_created`` | The planner produces a plan |
| ``brain.tool_dispatched`` | A tool is invoked |
| ``brain.response_produced`` | The LLM generates a response |
| ``brain.token_streamed`` | A token is emitted during streaming |
| ``brain.error`` | The brain pipeline encounters an error |

Tracing

### EventRecorder

A bounded in-memory recorder with per-name counts:

```python
recorder = EventRecorder(limit=10_000).subscribe_to(app.events)
recorder.count_for("brain.response_produced")  # → int
recorder.counts()  # → dict[str, int]
```

### LoggingExporter

Writes structured event log lines to the application logger:

```python
LoggingExporter().attach(app.events)
```

### Custom Exporters

Any ``Callable[[Event], None]`` can be attached as an exporter, enabling
forwarding to OpenTelemetry, Prometheus, JSON-lines files, etc.

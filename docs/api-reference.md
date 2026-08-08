# API Reference

A short reference to Xyberos' primary public objects. For each main class it
lists what the class is, **what it owns**, and **when to use it**.

## At a Glance

| Class | Owns | When to use it |
|-------|------|----------------|
| `Xyberos` | kernel, brain, runtime, agents | default entry point to compose an app |
| `Kernel` | config, logger, registry, plugins | platform/lifecycle; service registration and DI |
| `ServiceRegistry` | named services and factories | manual registration, resolution, and injection |
| `Config` | configuration values | reading and writing settings |
| `CognitiveContext` | prompt, response, metadata, error, plan | passing state through the pipeline |
| `Runtime` | a brain | executing a context through the pipeline |
| `Brain` | LLM, optional tool runner, memory, knowledge, planner, workflow | orchestrating the automated cognitive pipeline |
| `RuntimeAgent` | one runtime | exposing a runtime as an agent |
| `MultiAgentRuntime` | named agents, message board | coordinated runs with messaging and handoffs |
| `Message` | sender, recipient, content | agent-to-agent communication |
| `RoleAgent` | name, role, handlers | role-based collaborative agents |
| `SequentialWorkflow` | ordered steps | composing pipeline steps |
| `GraphWorkflow` | named nodes, edges, routes | branching, looping, and pausing workflows |
| `WorkflowCheckpoint` | SQLite-persisted runs | resuming paused graphs across processes |
| `SequentialPlanner` | ordered plan steps | producing a plan for a context |
| `LLMPlanner` | an LLM and optional parser | deriving plan steps from the request |
| `InMemoryMemory` | stored contexts | dev/test memory provider |
| `SqliteMemory` | persistent context rows | durable memory provider |
| `InMemoryKnowledge` | keyword facts | dev/test knowledge provider |
| `SqliteKnowledge` | persistent keyword facts | durable knowledge provider |
| `ToolRegistry` | named tools | registering and executing tools |
| `ToolRunner` | a tool registry | selecting and dispatching tools |
| `PluginLoader` | loaded plugins, entry-point discovery, convention scan | loading, unloading, and auto-discovering extensions |
| `LLMProvider` | a model backend | providing text generation |
| `EchoLLM` | nothing (echoes the prompt) | default no-op model |
| `CallableLLM` | a wrapped callable | turning a function into an LLM |
| `StreamingLLM` | generate + stream callables | streaming token output |
| `AsyncLLM` | an async agenerate | async-only LLM provider |
| `StructuredLLM` | a provider + parser | parsing LLM output into data |
| `OpenAILLM` / `AnthropicLLM` / `GeminiLLM` | lazy SDK clients | official provider adapters |
| `OllamaLLM` | stdlib HTTP | local Ollama server |
| `OpenAICompatibleLLM` | stdlib HTTP | any /chat/completions endpoint |
| `FunctionTool` | a typed callable + schema | typed, validated tool results |
| `EventBus` | subscribers and published events | observing and extending the pipeline |

## Package Root

Import the facade helpers from the package root:

```python
from xyberos import Xyberos, chat, create_app
```

### `Xyberos`

- **What it is:** the application facade that composes the core layers.
- **What it owns:** a `Kernel`, a `Brain`, a `Runtime`, a default `RuntimeAgent`,
  and a `MultiAgentRuntime`. It also exposes the core services through typed
  properties: `config`, `logger`, `registry`, `plugins`, `llm`, `memory`,
  `knowledge`, `tools`, `tool_runner`, `planner`, `intent`, `experience`,
  `workflow`, `brain`, `runtime`, and `agents`.
- **When to use it:** when you want a ready-to-run application with service
  registration, dependency injection, plugin management, agent management, and
  request execution. Prefer `create_app()` unless you need to keep a reference
  around.

### `create_app(config=None, llm=None, memory=None, knowledge=None, tools=None, planner=None, workflow=None, tool_runner=None, intent=None, experience=None)`

Convenience constructor for a ready-to-use `Xyberos` application. Any provider
you omit is filled in with an in-memory default (`intent` defaults to an empty
`HeuristicIntentEngine`, `experience` to `InMemoryExperience`; both are inactive
unless enabled via config).

### `chat(prompt, config=None, llm=None, ...)`

One-shot helper for the common case where you only need a response string. It
accepts the same provider arguments as `create_app`.

## Core Classes

### `xyberos.kernel`

#### `Kernel`

- **What it owns:** configuration (`Config`), logging (`Logger`), the service
  registry (`ServiceRegistry`), plugin loading (`PluginLoader`), and the
  start/stop lifecycle.
- **When to use it:** rarely directly — `Xyberos` builds one for you. Reach for
  it when you need platform-level service registration or lifecycle control.

#### `Config`

- **What it owns:** a mutable key/value mapping.
- **When to use it:** reading and writing application settings, typically via
  `app.config`.

#### `ServiceRegistry`

- **What it owns:** named services and lazy factories, plus constructor
  dependency injection (`inject`).
- **When to use it:** manual service registration and resolution, or when you
  need DI beyond the facade.

#### `Logger`

- **What it owns:** level-aware log output.
- **When to use it:** logging from your own code, usually via `app.logger`.

### `xyberos.runtime`

#### `CognitiveContext`

- **What it owns:** a single request's `prompt`, `response`, `metadata`, `error`,
  and `plan` (the plan produced by the planner during processing), plus the
  `succeeded` flag.
- **When to use it:** the state object passed through the whole pipeline; build
  one to run a request manually.

#### `Runtime`

- **What it owns:** a configured `Brain`.
- **When to use it:** executing a `CognitiveContext` through the pipeline and
  returning the completed context.

### `xyberos.brain`

#### `Brain`

- **What it owns:** an `LLMProvider`, and optional `ToolRunner`, memory,
  knowledge, planner, and workflow providers.
- **When to use it:** validating input and generating a response; the brain
  orchestrates the automated pipeline. See [The cognitive pipeline](#the-cognitive-pipeline)
  below for the exact order.

##### The cognitive pipeline

For each request, `Brain.chat()` runs the configured subsystems in order:

1. **Workflow** — if configured, its steps run first; a step that sets the
   response short-circuits the pipeline.
2. **Memory** — past turns are retrieved and injected into the prompt.
3. **Knowledge** — matching facts are queried and injected into the prompt.
4. **Planner** — the plan is computed and recorded on `context.plan`.
5. **Tools** — a matching tool is dispatched via the `ToolRunner`.
6. **LLM** — the enriched prompt is sent to the model.
7. **Memory** — the completed turn is stored for future requests.

Every step is optional. A bare `Brain` behaves like a plain LLM wrapper, and
`create_app()` wires all of the in-memory defaults automatically.

### `xyberos.llm`

#### `LLMProvider`

- **What it owns:** the model backend contract (`generate`).
- **When to use it:** implementing a custom model backend for Xyberos.

#### `EchoLLM`

- **What it owns:** nothing; it echoes the prompt back.
- **When to use it:** the default no-op model, useful for smoke tests.

#### `CallableLLM`

- **What it owns:** a wrapped plain callable.
- **When to use it:** turning a simple `prompt -> response` function into an
  `LLMProvider`.

#### `StreamingLLM`

- **What it owns:** a `generate` callable and a `stream(prompt, on_token)` callable.
- **When to use it:** providing streaming token output; the Brain emits each
  token as the `brain.token_streamed` event.

#### `AsyncLLM`

- **What it owns:** an async `agenerate` coroutine.
- **When to use it:** async-only providers used with `app.achat` / `app.arun`.
  Not usable from the synchronous API (a clear `TypeError` is raised).

#### `StructuredLLM`

- **What it owns:** a wrapped `LLMProvider` and a parser (JSON by default).
- **When to use it:** converting LLM text output into structured data via
  `parse(prompt)`; raises `StructuredOutputError` on parse failure. The
  `structured(llm, prompt, parser=None)` helper is the one-shot form.

#### `EmbeddingLLM`

- **What it owns:** a wrapped `LLMProvider` plus an embedder callable.
- **When to use it:** adding the duck-typed `embed(text) -> list[float]`
  capability to a plain generator; raises `ProviderError` when no embedder is
  configured (RFC-0016).

#### `HashEmbedder`

- **What it owns:** deterministic, dependency-free embeddings (BLAKE2b).
- **When to use it:** local development and tests before a real embedding
  model is wired in.

#### Provider adapters

- `OpenAILLM(model, api_key, base_url, timeout, client)` — official OpenAI SDK (lazy import).
- `AnthropicLLM(model, api_key, client)` — official Anthropic SDK (lazy import).
- `GeminiLLM(model, api_key, client)` — official Google Gemini SDK (lazy import).
- `OllamaLLM(model, base_url)` — local Ollama server over stdlib HTTP.
- `OpenAICompatibleLLM(model, base_url, api_key)` — any `/chat/completions`
  endpoint over stdlib HTTP.
- `OpenAIEmbeddingLLM(model, base_url, api_key)` — any OpenAI-compatible
  `/embeddings` endpoint over stdlib HTTP (exposes `embed`).

All are `LLMProvider`s. The SDK-based adapters raise a clear `ProviderError`
when the underlying package is not installed, keeping the core dependency-free.

### `xyberos.agents`

#### `RuntimeAgent`

- **What it owns:** a single `Runtime`.
- **When to use it:** exposing an existing runtime as a named agent in a
  multi-agent pipeline.

#### `MultiAgentRuntime`

- **What it owns:** named `Agent` instances and a running message board.
- **When to use it:** running agents over one shared context with inter-agent
  messaging, handoffs, and roles. Each agent runs at most once per `run()` call;
  a `handoff` message runs its recipient next.
- **Useful members:** `names`, `messages`, `register`, `get`, `remove`, `role`,
  `send(message)`, `run(context, agent_names=None)`.

#### `Message`

- **What it owns:** an immutable `sender`, `recipient`, `content`, `kind`, and `metadata`.
- **When to use it:** agent-to-agent communication. `recipient="*"` broadcasts;
  `kind == "handoff"` transfers control to the recipient.
- **Helpers:** `post(context, message)` queues a message for the runtime;
  `handoff(target, content=None, sender="")` builds a handoff.

#### `RoleAgent`

- **What it owns:** a `name`, `role`, optional `run` handler, and optional `receive` handler.
- **When to use it:** building role-based collaborative agents without subclassing.

### `xyberos.workflows`

#### `SequentialWorkflow`

- **What it owns:** an ordered list of steps.
- **When to use it:** composing pipeline operations that each receive and return
  the context.

#### `GraphWorkflow`

- **What it owns:** named nodes (steps), fixed edges, conditional routes, and a
  max-steps guard.
- **When to use it:** branching, looping, or pausing workflows. A step raises
  `WorkflowPaused` to pause; `execute(context)` returns a `WorkflowRun`, and
  `resume(run, value)` continues with the value in
  `context.metadata["workflow.resume_value"]`.
- **Useful methods:** `add_node(name, step)`, `add_edge(source, target)`,
  `add_route(source, route)`, `execute(context)`, `resume(run, value)`,
  `resume_from_checkpoint(checkpoint, run_id, value)`, `run(context)` (contract
  method — returns the final context, raises `WorkflowPaused` on pause).

#### `WorkflowCheckpoint`

- **What it owns:** SQLite-persisted `WorkflowRun` records.
- **When to use it:** saving a paused graph and resuming it in a later process.
  Methods: `save(run_id, run)`, `load(run_id)`, `delete(run_id)`, `list_ids()`, `close()`.

#### `WorkflowRun`

- **What it owns:** a `status` (`"completed"` or `"paused"`), the current
  `context`, the current `node`, an optional `prompt` (when paused), and a
  `steps` trace.
- **When to use it:** driving a human-in-the-loop loop:

```python
run = graph.execute(context)
while run.status == "paused":
    run = graph.resume(run, input(run.prompt))
```

#### `WorkflowStep`

- **What it owns:** a callable type alias, `(CognitiveContext) -> CognitiveContext | None`.
- **When to use it:** typing your workflow step functions.

### `xyberos.planner`

#### `SequentialPlanner`

- **What it owns:** an ordered set of plan step names.
- **When to use it:** producing a simple ordered plan for a context.

#### `LLMPlanner`

- **What it owns:** an `LLMProvider` and an optional `parse` callable.
- **When to use it:** deriving plan steps by asking the LLM to break down the
  request (one step per line by default; pass `parse` for JSON or other shapes).
- **Note:** combine with `config={"brain.inject_plan": True}` to have the Brain
  append the plan to the model prompt.

### `xyberos.memory` / `xyberos.knowledge`

#### `InMemoryMemory` / `InMemoryKnowledge` / `SqliteMemory` / `SqliteKnowledge`

- **What they own:** in-process context storage / keyword-keyed facts; the
  SQLite variants persist rows to a database file (stdlib `sqlite3`).
- **When to use them:** in-memory for dev/tests; SQLite for durable storage —
  pass them to `create_app(memory=..., knowledge=...)`. Metadata, plans, and
  values are JSON-encoded, so any JSON-serializable payload round-trips.

### `xyberos.intent`

#### `IntentEngine`

- **What it owns:** the `classify(context) -> Intent` contract (RFC-0016).
- **When to use it:** routing a request to a planner mode, tool, agent, or
  workflow before generation. `Intent(name, confidence, params, target)` is a
  frozen dataclass; `target` names a tool/agent/workflow when relevant.

#### `HeuristicIntentEngine`

- **What it owns:** ordered `IntentRule(name, patterns, target)` rules matched
  case-insensitively against the prompt.
- **When to use it:** deterministic intent routing without an LLM; the first
  matching rule wins with full confidence, otherwise a fallback intent is
  returned. Enable via `create_app(intent=..., config={"brain.intent": True})`.

### `xyberos.vector`

#### `VectorStore`

- **What it owns:** the `upsert`/`query`/`delete`/`clear` namespace contract
  for vectors (RFC-0016), plus the `ScoredHit` result dataclass.
- **When to use it:** the semantic substrate behind retrieval-based memory,
  knowledge, and learning.

#### `CosineVectorStore`

- **What it owns:** a dependency-free in-memory store using exact cosine
  similarity; `query` returns hits ranked best-first.
- **When to use it:** local development and tests.

`ChromaVectorStore` and `PgVectorStore` adapters are optional (install
`xyberos[vectors]`); they lazy-import their backend and raise a clear
`ProviderError` when it is missing.

### `xyberos.experience`

#### `ExperienceStore`

- **What it owns:** the `record`/`query`/`feedback`/`stats` contract over
  `Episode` records (RFC-0016).
- **When to use it:** capturing runtime outcomes so intent/planner/memory/
  knowledge providers can learn. The Brain records one `Episode` per completed
  turn when enabled via `config={"experience.enabled": True}`.

#### `InMemoryExperience` / `SqliteExperience`

- **What they own:** in-memory vs. SQLite-persisted episode stores.
- **When to use them:** in-memory for dev/tests; SQLite for durable learning
  data across restarts.

### `xyberos.tools`

#### `ToolRegistry`

- **What it owns:** named `Tool` instances.
- **When to use it:** registering, looking up, and executing tools.

#### `ToolRunner`

- **What it owns:** a `ToolRegistry`.
- **When to use it:** choosing a tool by name heuristic and dispatching it
  against a `CognitiveContext`.

#### `FunctionTool`

- **What it owns:** a typed callable, its JSON schema, and argument coercion.
- **When to use it:** wrapping a plain typed function as a `Tool`. `schema`
  describes the parameters; `execute` validates/coerces arguments and raises
  `ToolArgumentError` for missing, unknown, or mistyped arguments.

### `xyberos.plugins`

#### `PluginLoader`

- **What it owns:** loaded `Plugin` instances, a reference to the platform
  kernel, and auto-discovery machinery (`importlib.metadata.entry_points`).
- **When to use it:** loading, unloading, and auto-discovering plugins.

##### Methods

- `load(plugin)` — register and retain one plugin instance.
- `load_from_module(module_name, attribute="plugin")` — import a module and
  load its plugin export.
- `load_entry_points(group="xyberos.plugins")` — auto-discover every plugin
  declared under the given entry-point group via `importlib.metadata`. Entry
  point values are `module:attribute` (or a bare module whose `plugin` export
  is used).

### App creation with custom providers

```python
from xyberos import create_app
from xyberos.llm import CallableLLM
from xyberos.knowledge import InMemoryKnowledge

app = create_app(
    llm=CallableLLM(lambda prompt: f"answer: {prompt}"),
    knowledge=InMemoryKnowledge({"hours": "9am-6pm"}),
)
print(app.chat("What are your hours?"))
```

### Service registration and dependency injection

```python
app = create_app(config={"env": "production"})
app.register("cache", {})
app.register_factory("adapter", lambda config, cache: (config, cache))
adapter = app.resolve("adapter")
```

### Auto-discovering plugins

Two styles — no manual wiring required.

**Convention scan** (drop a module in a folder):

```python
app = create_app()
app.load_plugins_from("app.plugins")   # every Plugin subclass in app/plugins is loaded
```

**Entry points** (declared in package metadata):

```python
app = create_app()
app.load_entry_points()   # every installed "xyberos.plugins" entry point is loaded
```

### Custom LLM provider

```python
from xyberos.contracts.llm import LLMProvider

class MyLLM(LLMProvider):
    def generate(self, prompt: str) -> str:
        return f"response to: {prompt}"

app = create_app(llm=MyLLM())
```
- `load_from_package(package)` — convention-based auto-discovery: walk a
  package and load every concrete (non-abstract) `Plugin` subclass found.
- `get(name)` / `unload(name)` — retrieve / unregister by name.

`load_entry_points` and `load_from_package` are idempotent when called with
`skip_existing=True` (the default) — re-running discovery never double-registers
a plugin.

These are also exposed on the facade:

- `app.load_entry_points(group="xyberos.plugins")`
- `app.load_plugins_from("app.plugins")`

### `xyberos.events`

#### `EventBus`

- **What it owns:** named listeners, wildcard listeners, and the publish/emit loop.
- **When to use it:** subscribing to pipeline and lifecycle events for
  observability, tracing, or automation; reachable as `app.events`.
- **Useful methods:** `subscribe(event, listener)`, `subscribe_any(listener)`,
  `unsubscribe(event, listener)`, `emit(name, context=None, **data)`,
  `publish(event)`, `has_listeners(event)`.

#### `Event`

- **What it owns:** an immutable `name`, optional `context`, and a `data` mapping.
- **When to use it:** the payload delivered to every listener.

Canonical event names are exported from `xyberos.events` (e.g. `REQUEST_STARTED`,
`RESPONSE_PRODUCED`, `BRAIN_ERROR`); see `xyberos/events/names.py` for the full list.

RFC-0016 adds `INTENT_CLASSIFIED` (`brain.intent_classified`, data: `intent`,
`confidence`) and `EPISODE_RECORDED` (`brain.episode_recorded`), plus the
future-facing `FEEDBACK_RECORDED`, `ENGINE_TRAINED`, and `ENGINE_REFRESHED`.

```python
from xyberos import create_app
from xyberos.events import BRAIN_ERROR, RESPONSE_PRODUCED

app = create_app()
app.events.subscribe(RESPONSE_PRODUCED, lambda e: print(e.data["response"]))
app.events.subscribe(BRAIN_ERROR, lambda e: print("request failed"))
```

A listener that raises is logged and isolated — it never breaks the pipeline.

#### `EventRecorder`

- **What it owns:** a bounded event history, per-name counts, and attached exporters.
- **When to use it:** recording every event for inspection, dashboards, or
  forwarding to metrics/tracing backends. Attach with `subscribe_to(app.events)`.

#### `LoggingExporter`

- **What it owns:** a logger and the export logic.
- **When to use it:** writing one structured log line per event.

Any callable `event -> None` can be an `Exporter`, so integrating a metrics or
tracing backend is just a function.

### `xyberos.diagnostics`

- `doctor()` - build a developer-focused runtime report
- `DiagnosticReport` - structured diagnostics payload

**When to use it:** debugging an app or inspecting its runtime state.

### `xyberos.utils`

- `retry(func, max_attempts=3, backoff=0.1, retry_on=Exception, on_retry=None)` - call `func` with exponential backoff.
- `RateLimiter(calls_per_second, burst=1)` - a token-bucket limiter with `acquire()` / `try_acquire()`.
- `with_timeout(seconds, func)` - run `func` with a best-effort timeout (daemon thread).
- `RetryError` - raised when retries are exhausted.

**When to use it:** wrapping LLM or tool calls for resilience, or via the Brain
config keys (`brain.max_attempts`, `brain.retry_backoff`, `brain.rate_limit`,
`brain.timeout`).

## Common Patterns

### Build the app

```python
from xyberos import create_app

app = create_app()
```

### Inject dependencies

```python
result = app.inject(lambda logger, config: (logger, config))
```

### Register services

```python
app.register("answer", 42)
app.register_factory("dynamic", lambda answer: f"answer={answer}")
```

### Run the pipeline

```python
context = app.run("hello")
text = app.chat("hello")
```

### Run the pipeline asynchronously

```python
import asyncio

context = asyncio.run(app.arun("hello"))
text = asyncio.run(app.achat("hello"))
```

### Stream LLM output

```python
from xyberos.events import TOKEN_STREAMED

app.events.subscribe(TOKEN_STREAMED, lambda e: print(e.data["token"], end=""))
```


# API Reference

Xyberos' primary public objects. Every entry follows a consistent template:

- **Primary entry points** (package root: `create_app`, `create_semantic_app`,
  `chat`, `achat`, the `Xyberos` facade, `doctor`) get the **full template** —
  What it does · Signature · Parameters · Returns · Default behavior · Basic
  example · Configuration example · Alternative · Custom implementation ·
  Workaround · Common mistakes · Related APIs.
- **Classes & providers** (Kernel, Brain, LLMs, memory, knowledge, etc.) use the
  compact **"what it owns / when to use it"** format — they're swappable behind
  contracts, so the interesting parts are the contract and the use cases.

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
| `OllamaEmbeddingLLM` | stdlib HTTP | local Ollama `/api/embed` (exposes `embed`) |
| `FunctionTool` | a typed callable + schema | typed, validated tool results |
| `SchemaToolCaller` | an LLM + tool registry | schema-driven LLM tool selection |
| `Router` / `ResponderChain` | confidence-gated responder tiers | LLM-free fast answers with escalation |
| `CacheResponder` / `CacheTeacher` | taught prompt→answer cache | answering repeated requests without the LLM |
| `PlanExecutor` | plan steps, verify, replan | closing the plan→execution loop |
| `Trainer` | offline distillation | training intent engines from recorded episodes |
| `StratifiedMemory` | durable facts + episodic history | separating what to remember from what to recall |
| `GroundingCheck` | reference-knowledge verification | keeping responses grounded in facts |
| `EventBus` | subscribers and published events | observing and extending the pipeline |

## Package Root

Import the facade helpers from the package root:

```python
from xyberos import (
    Xyberos,
    achat,
    chat,
    create_app,
    create_semantic_app,
    doctor,
)
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

---

### `create_app()`

**What it does**

Build a ready-to-use `Xyberos` application, filling in an in-memory default for
every provider you omit.

**Signature**

```python
create_app(
    config=None,        # Mapping[str, Any] | None
    llm=None,           # LLMProvider | None
    memory=None,        # MemoryProvider | None
    knowledge=None,     # KnowledgeProvider | None
    tools=None,         # ToolRegistry | None
    planner=None,       # Planner | None
    workflow=None,      # Workflow | None
    tool_runner=None,   # ToolRunner | None
    intent=None,        # IntentEngine | None
    experience=None,    # ExperienceStore | None
    router=None,        # Router | None
) -> Xyberos
```

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | `Mapping[str, Any]` | `None` | Dotted-key settings (e.g. `brain.intent`, `brain.max_attempts`) |
| `llm` | `LLMProvider` | `None` → `EchoLLM` | The model backend |
| `memory` | `MemoryProvider` | `None` → `InMemoryMemory` | Conversation history provider |
| `knowledge` | `KnowledgeProvider` | `None` → `InMemoryKnowledge` | Domain facts provider |
| `tools` | `ToolRegistry` | `None` → empty registry | Named capabilities |
| `planner` | `Planner` | `None` → `SequentialPlanner` | Produces a step plan |
| `workflow` | `Workflow` | `None` → `SequentialWorkflow` | Pre-steps before the pipeline |
| `tool_runner` | `ToolRunner` | `None` → wraps `tools` | Dispatches tools |
| `intent` | `IntentEngine` | `None` → empty `HeuristicIntentEngine` | Classifies intent (inactive unless enabled) |
| `experience` | `ExperienceStore` | `None` → `InMemoryExperience` | Records episodes (inactive unless enabled) |
| `router` | `Router` | `None` | Confidence-gated responder chain (see [xyberos.router](#xyberosrouter)) |

**Returns**

A wired `Xyberos` instance with `.run()`, `.chat()`, `.achat()`, `.arun()`,
and every subsystem exposed as a property.

### Default behavior

If you call `create_app()` with no arguments, you get:

- `EchoLLM` — echoes your prompt (zero setup, zero API keys)
- in-memory memory, knowledge, planner, tools, workflow, intent, experience
- a fully automated brain pipeline
- a default `RuntimeAgent` inside a `MultiAgentRuntime`
- `intent` and `experience` wired but **inactive** until enabled via config

### Basic example

```python
from xyberos import create_app

app = create_app()
print(app.chat("Hello, world!"))   # -> Hello, world!
```

### Configuration example

```python
from xyberos import create_app
from xyberos.llm import OllamaLLM
from xyberos.memory import SqliteMemory
from xyberos.knowledge import SqliteKnowledge

app = create_app(
    llm=OllamaLLM(model="llama3.2"),
    memory=SqliteMemory("chat.db"),
    knowledge=SqliteKnowledge("facts.db"),
    config={
        "brain.intent": True,      # enable intent classification
        "brain.max_attempts": 3,   # retry transient failures
        "brain.timeout": 30,       # seconds per LLM call
    },
)
```

### Alternative

- **`create_semantic_app()`** — one-call persistent setup where intent, memory,
  knowledge, and planner share a single vector store (see below).
- **`Xyberos(...)` directly** — full control, no defaults injected:

  ```python
  from xyberos import Xyberos
  app = Xyberos(config={"brain.intent": True})
  ```

- **`chat()` / `achat()`** — one-shot helpers that build a default app, run,
  and return only the text.

### Custom implementation

Pass any object that satisfies the relevant contract — no subclassing required:

```python
from xyberos import create_app
from xyberos.llm import CallableLLM

app = create_app(llm=CallableLLM(lambda prompt: f"answer: {prompt}"))
```

### Workaround

> If you don't want one of the default providers, pass your own (or `None`
> won't disable it — pass a no-op provider). To *disable* intent/experience,
> simply leave them off; they're inactive until enabled via config.

### Common mistakes

```python
# ❌ Replacing a provider after create_app() doesn't affect the built brain
app = create_app()
app.kernel.register("llm", my_llm, replace=True)   # resolve() sees it, brain doesn't

# ✅ Build a fresh app, or use plugins (load_entry_points() re-syncs the brain)
app = create_app(llm=my_llm)
```

### Related APIs

- `create_semantic_app()`
- `Xyberos.chat()` / `Xyberos.run()`
- `chat()` / `achat()` (package-level one-shots)
- `Configuring Services` → [learn/18-configuring-services.md](learn/18-configuring-services.md)

---

### `create_semantic_app()`

**What it does**

Build a ready-to-use app backed by **one shared, persistent `VectorStore`**:
intent, memory, and knowledge all share a single `SqliteVectorStore`
(`learning.db` by default), so everything learned survives restarts with zero
extra configuration.

**Signature**

```python
create_semantic_app(
    config=None,        # Mapping[str, Any] | None
    llm=None,           # LLMProvider | None
    embedder=None,      # Any with embed(text) -> list[float]
    store=None,         # VectorStore | None  (default SqliteVectorStore("learning.db"))
    *,
    experience=None,    # ExperienceStore | None
    tools=None,         # ToolRegistry | None
    workflow=None,      # Workflow | None
    tool_runner=None,   # ToolRunner | None
    router=None,        # Router | str | None   ("hybrid" auto-builds the responder chain)
    templates=None,     # Iterable[Template] | None  (pre-seeds the hybrid template tier)
) -> Xyberos
```

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | `Mapping[str, Any]` | `None` | Dotted-key settings; `brain.intent` defaults to `True` |
| `llm` | `LLMProvider` | `None` | The model backend |
| `embedder` | any `embed(text)` | `HashEmbedder` | Powers semantic matching |
| `store` | `VectorStore` | `SqliteVectorStore("learning.db")` | Shared semantic backend |
| `experience` | `ExperienceStore` | `None` | Episode store (inactive unless enabled) |
| `tools` | `ToolRegistry` | `None` | Named capabilities |
| `workflow` | `Workflow` | `None` | Pre-steps before the pipeline |
| `tool_runner` | `ToolRunner` | `None` | Dispatches tools |
| `router` | `Router` \| `str` | `None` | `"hybrid"` auto-wires a self-teaching responder chain + `CacheTeacher` |
| `templates` | `Iterable[Template]` | `None` | Pre-seeds the hybrid router's template tier |

**Returns**

A wired `Xyberos` with `VectorMemory`, `VectorKnowledge`, an embedding→LLM
intent cascade, and an `AdaptivePlanner` — all over the shared store.

### Default behavior

- Everything is **persistent by default** (`learning.db`) — learned facts,
  cache, and examples survive restarts.
- Intent is **enabled** (`brain.intent` defaults to `True`).
- The intent cascade's confidence gate is set via `intent.threshold`
  (default `0.9`).
- With no `router=`, no hybrid chain is installed (the brain still runs its
  normal LLM path).

### Basic example

```python
from xyberos import create_semantic_app
from xyberos.llm import OllamaLLM, OllamaEmbeddingLLM

app = create_semantic_app(
    llm=OllamaLLM(model="llama3.2"),
    embedder=OllamaEmbeddingLLM(model="nomic-embed-text"),  # real semantics
    router="hybrid",
)
```

### Configuration example

```python
from xyberos import create_semantic_app
from xyberos.llm import OllamaEmbeddingLLM
from xyberos.vector import SqliteVectorStore

app = create_semantic_app(
    llm=llm,
    embedder=OllamaEmbeddingLLM(model="nomic-embed-text"),
    store=SqliteVectorStore("learning.db"),
    router="hybrid",
)
```

### Alternative

Swap the backend without touching the engines:

```python
from xyberos.vector import ChromaVectorStore, PgVectorStore

app = create_semantic_app(embedder=embedder, store=ChromaVectorStore())  # pip install xyberos[vectors]
app = create_semantic_app(embedder=embedder, store=PgVectorStore())
```

### Workaround

> If you need `IngestingKnowledge` (document/file/URL ingestion), note that
> `create_semantic_app` builds its own plain `VectorKnowledge`. Build with
> `create_app(knowledge=kb, ...)` when you need the `ingest()` capability — see
> [21. Knowledge Ingestion](learn/21-knowledge-ingestion.md).

### Common mistakes

- **Using the default `HashEmbedder` for real matching** — it only matches
  near-identical text. Pass a semantic embedder (`OllamaEmbeddingLLM`,
  `SentenceTransformerEmbedder`, or `OpenAIEmbeddingLLM`) for paraphrase
  matching.
- **Forgetting persistence** — the default `SqliteVectorStore("learning.db")`
  accumulates state across runs. Pass `store=CosineVectorStore()` for a clean
  in-memory session in demos and tests.

### Related APIs

- `create_app()`
- `xyberos.vector` — `VectorStore`, `SqliteVectorStore`, `CosineVectorStore`
- `xyberos.router` — `build_router`, `ResponderChain`, `CacheTeacher`

---

### `chat(prompt, *, config=None, llm=None, memory=None, knowledge=None, tools=None, planner=None, workflow=None, tool_runner=None)`

**What it does**

One-shot helper: build a default app, run one prompt, return only the response
text. Accepts the same provider arguments as `create_app`.

**Signature**

```python
chat(prompt: str, *, config=None, llm=None, memory=None, knowledge=None,
     tools=None, planner=None, workflow=None, tool_runner=None) -> str
```

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | `str` | required | The user input |
| `config` / providers | same as `create_app` | `None` | Overrides for the one-shot app |

**Returns**

`str` — the generated response text.

### Default behavior

Builds a default app (same defaults as `create_app`) and returns
`app.chat(prompt)`. Raises `RuntimeError` if the pipeline produced no response.

### Basic example

```python
from xyberos import chat
print(chat("Hello!"))   # -> Hello!
```

### Configuration example

```python
from xyberos import chat
from xyberos.llm import CallableLLM

print(chat("hello", llm=CallableLLM(lambda p: f"answer: {p}")))  # -> answer: hello
```

### Alternative

- **`achat()`** — the async one-shot:

  ```python
  import asyncio
  from xyberos import achat

  print(asyncio.run(achat("Hello!")))
  ```

- **`app = create_app()` then `app.chat()`** — when you want to reuse the app.

### Related APIs

- `achat()`
- `create_app()`
- `Xyberos.chat()` / `Xyberos.achat()`

---

### `Xyberos` facade methods

Beyond the properties listed above, the facade exposes the full platform. Each
method follows the same template.

#### `run(prompt, *, metadata=None) -> CognitiveContext`

**What it does** — run one prompt and return the complete cognitive context
(prompt, response, plan, intent, metadata, succeeded, error).

**Basic example**

```python
ctx = app.run("hello")
print(ctx.response, ctx.succeeded)
```

**Alternative** — `arun(prompt)` for the async pipeline.

#### `chat(prompt, *, metadata=None) -> str`

**What it does** — convenience wrapper over `run()` returning only the text.

**Basic example**

```python
print(app.chat("hello"))
```

**Note** — raises `RuntimeError` if the pipeline produced no response.

#### `achat(prompt, *, metadata=None) -> str` / `arun(prompt, *, metadata=None) -> CognitiveContext`

**What it does** — async variants of `chat()` / `run()` for use inside
FastAPI / asyncio apps.

```python
response = await app.achat("hello")
```

#### `run_agents(prompt, *, metadata=None, agent_names=None) -> CognitiveContext`

**What it does** — run all (or a selected subset of) registered agents over a
fresh context, honoring handoffs and messaging.

```python
result = app.run_agents("I need a human", agent_names=["supervisor", "support_worker"])
```

#### `register(name, service, *, replace=False)` / `resolve(name)`

**What they do** — register a named service in the kernel and resolve it by
name (with optional `replace=True`).

```python
app.register("answer", 42)
assert app.resolve("answer") == 42
```

#### `register_factory(name, factory, *, singleton=True, replace=False)`

**What it does** — register a lazy factory; dependencies are injected by
parameter name.

```python
app.register_factory("llm", build_llm, replace=True)
```

#### `inject(target, **overrides)`

**What it does** — construct or invoke any callable, resolving its parameters
by name from registered services.

```python
def build_message(logger, config): ...
msg = app.inject(build_message)
```

#### Plugin management

```python
app.load_plugin(plugin)                       # load one plugin
app.unload_plugin(name)                       # unload by name
app.load_entry_points(group="xyberos.plugins")# discover installed entry points
app.load_plugins_from("app.plugins")          # convention scan a package
```

#### Agent management

```python
app.register_agent(agent)     # add an agent to the multi-agent runtime
app.remove_agent(name)        # remove by name
```

#### Learning

```python
app.feedback(episode_id, 1.0, note="great answer")  # rating -1.0..1.0
```

Attaches a rating to a recorded episode and emits `FEEDBACK_RECORDED`.

#### Lifecycle

```python
app.start()          # idempotent
app.stop()           # idempotent
app.started          # bool
```

### `doctor()`

**What it does** — build a lightweight `DiagnosticReport` snapshot of the
local runtime and package state (version, Python, kernel services, plugins).

**Basic example**

```python
from xyberos import doctor
report = doctor()
print(report.as_dict())
```

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
  knowledge, planner, workflow, intent, experience, router, and security
  providers.
- **When to use it:** validating input and generating a response; the brain
  orchestrates the automated pipeline. See [The cognitive pipeline](#the-cognitive-pipeline)
  below for the exact order.

##### The cognitive pipeline

For each request, `Brain.chat()` runs the configured subsystems in order:

1. **Workflow** — if configured, its steps run first; a step that sets the
   response short-circuits the pipeline.
2. **Cheap-first router** — when a router is installed and `brain.cheap_first`
   is on (the default for LLM-free routers), its LLM-free tiers
   (template → tool → knowledge → memory → cache) may answer before any LLM
   call is spent on intent/planning.
3. **Memory** — past turns are retrieved and injected into the prompt.
4. **Knowledge** — matching facts are queried and injected into the prompt.
5. **Intent** — if enabled (`brain.intent`), the request is classified and the
   result recorded on `context.intent` (may steer tool dispatch).
6. **Planner** — the plan is computed and recorded on `context.plan`.
7. **Router** — a configured `Router` gets a chance to answer; a confident tier
   short-circuits, otherwise processing falls through.
8. **Tools** — a matching tool is dispatched via the `ToolRunner`.
9. **LLM** — the enriched prompt is sent to the model.
10. **Memory** — the completed turn is stored for future requests.

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

- `OpenAILLM(model="gpt-4o-mini", *, api_key=None, base_url=None, timeout=60.0, client=None)` — official OpenAI SDK (lazy import).
- `AnthropicLLM(model="claude-3-5-sonnet-latest", *, api_key=None, client=None)` — official Anthropic SDK (lazy import).
- `GeminiLLM(model="gemini-1.5-flash", *, api_key=None, client=None)` — official Google Gemini SDK (lazy import).
- `OllamaLLM(model="llama3.2", *, base_url="http://localhost:11434", timeout=60.0, post=None)` — local Ollama server over stdlib HTTP. The `timeout` bounds every socket operation, so an unreachable server fails fast instead of hanging.
- `OllamaEmbeddingLLM(model="nomic-embed-text", *, base_url="http://localhost:11434", timeout=60.0, post=None)` — local Ollama `/api/embed` over stdlib HTTP (exposes `embed`; pairs with `OllamaLLM` for a fully-local semantic stack).
- `OpenAICompatibleLLM(model, *, base_url, api_key=None, timeout=60.0, post=None)` — any `/chat/completions` endpoint over stdlib HTTP.
- `OpenAIEmbeddingLLM(model, *, base_url, api_key=None, timeout=60.0, post=None)` — any OpenAI-compatible `/embeddings` endpoint over stdlib HTTP (exposes `embed`).
- `FallbackLLM(primary, *fallbacks, retry_on=...)` — tries the primary model, falling back to the next provider on `ProviderError` (e.g. a cloud outage degrades to a local Ollama model); RFC-0017.
- `SentenceTransformerEmbedder(model_name)` — real semantic embedder backed by `sentence-transformers` (install `xyberos[embeddings]`).

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

#### `AdaptivePlanner`

- **What it owns:** an LLM planner plus an optional `VectorStore`/embedder of
  past `request -> plan` examples.
- **When to use it:** few-shot planning that mirrors how similar requests were
  handled; `learn(request, plan)` records new examples so it improves by
  accumulation.

#### `ReflectivePlanner`

- **What it owns:** a base planner and an optional reflection LLM.
- **When to use it:** scoring plan confidence (recorded on
  `context.metadata["plan.confidence"]`) and revising the plan before execution.

#### `PlanExecutor` / `PlanResult`

- **What it owns:** execution of plan steps through tools/callables, per-step
  verification, and re-planning on failure (bounded by `max_steps`/`max_replans`).
- **When to use it:** closing the plan loop — a step can be a tool name, a
  `{"tool": name, "args": {...}}` mapping, or a callable; `verify` decides
  success and `replan` decides recovery. Emits `brain.plan_step_executed`,
  `brain.plan_step_failed`, and `brain.plan_replanned`.

### `xyberos.memory` / `xyberos.knowledge`

#### `InMemoryMemory` / `InMemoryKnowledge` / `SqliteMemory` / `SqliteKnowledge`

- **What they own:** in-process context storage / keyword-keyed facts; the
  SQLite variants persist rows to a database file (stdlib `sqlite3`).
- **When to use them:** in-memory for dev/tests; SQLite for durable storage —
  pass them to `create_app(memory=..., knowledge=...)`. Metadata, plans, and
  values are JSON-encoded, so any JSON-serializable payload round-trips.

#### `VectorMemory` / `ConsolidatingMemory` / `StratifiedMemory` / `VectorKnowledge` / `IngestingKnowledge`

- **What they own:** semantic/hybrid memory (`VectorMemory`, with
  `retrieve_scored`), LLM-summarizing memory (`ConsolidatingMemory`, with
  `consolidate_now`), durable-facts-plus-episodes memory (`StratifiedMemory`,
  separating `facts` from conversational history), embedding-retrieved
  knowledge (`VectorKnowledge`, with `query_scored`), and chunked document
  ingestion (`IngestingKnowledge`).
- **When to use them:** retrieval-based, "learn by accumulation" memory and
  knowledge over a `VectorStore`; pass an `embedder` (callable or any object
  with `embed(text)`). `StratifiedMemory` pairs with
  `extract_facts_deterministic(prompt, response)` (RFC-0018 M7) to lift durable
  facts out of a conversation.

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

#### `LLMIntentEngine`

- **What it owns:** an `LLMProvider` and structured-JSON intent parsing.
- **When to use it:** open-ended intent classification; returns
  `{name, confidence, params, target}` and falls back to a configured label on
  parse failure so it composes safely in a cascade.

#### `EmbeddingIntentEngine`

- **What it owns:** a `VectorStore` plus an embedder of labeled examples.
- **When to use it:** intent that "learns by accumulation" — `learn(name,
  example)` adds an example, `classify` returns the nearest neighbor.

#### `CascadeIntentEngine`

- **What it owns:** an ordered list of `IntentEngine`s and a confidence threshold.
- **When to use it:** cheap engines first, stronger engines on low confidence,
  with a deterministic fallback.

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

#### `SqliteVectorStore`

- **What it owns:** a dependency-free persistent store (stdlib `sqlite3`) using
  exact cosine similarity; `start`/`stop` join the kernel lifecycle.
- **When to use it:** persisting runtime-learned examples (intent, planner,
  memory, knowledge indexes) across restarts with no extra dependencies.

`ChromaVectorStore` and `PgVectorStore` adapters are optional (install
`xyberos[vectors]`); they lazy-import their backend and raise a clear
`ProviderError` when it is missing. All cosine stores expose `clear_all()` to
drop every namespace and vector.

#### Rerankers

- `Reranker` — the abstract `rerank(query, hits)` contract.
- `ScoreReranker` — a no-op reranker that preserves similarity order.
- `LexicalReranker` — an optional TF-IDF reranker (install `xyberos[rerank]`)
  that boosts hits sharing lexical terms with the query.

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

### `xyberos.learning`

- **What it owns:** `promote_successful(experience)`, `demote_failed(experience)`,
  `to_examples(episodes, field=...)` helpers, `ExamplePromoter`, and
  `KnowledgePromoter`.
- **When to use it:** turning recorded episodes into training examples for the
  trainable providers. `ExamplePromoter(experience, intent_engine=..., planner=...)`
  automates `promote()` — feeding successful episodes into the intent engine and
  adaptive planner via `learn`. `KnowledgePromoter(experience, knowledge)`
  auto-ingests positively-rated `prompt → response` pairs into a
  `VectorKnowledge` (idempotent per episode).

### `xyberos.router`

The hybrid responder chain (RFC-0017): a confidence-gated sequence of tiers
that answers cheap requests without the LLM and escalates the rest. It is a
pure optimization layer — when every tier declines, the Brain falls through to
its normal LLM path.

#### `build_router(llm=None, tool_runner=None, knowledge=None, memory=None, cache=None, cache_store=None, cache_embedder=None, templates=None, fallback=None, degrade="refusal", capabilities=None)`

Assembles a `ResponderChain` from whatever dependencies you supply — a tier is
only added when its provider is present. Cheapest tier first: template → tool →
knowledge → memory → cache → LLM, with a `DegradedResponder` fallback when no
LLM tier exists.

#### `ResponderChain`

- **What it owns:** an ordered list of `Responder`s, a confidence threshold,
  and an optional fallback.
- **When to use it:** routing a request through the tiers — `respond(context)`
  returns the first confident answer, `respond_cheap(context)` runs only the
  LLM-free tiers, and `is_llm_free` reports whether any tier needs a model.
  `get_threshold(name)` / `set_threshold(name, value)` tune per-tier gates.

#### Responders

- `TemplateResponder` — pattern/template matches, zero model calls.
- `ToolResponder` — a genuine tool match (intent target or name in prompt).
- `KnowledgeResponder` — a top knowledge fact clearing a confidence gate.
- `MemoryResponder` — the most-similar past Q→A clearing a gate.
- `CacheResponder(store=None, embedder=None, threshold=0.9, top_k=1)` — answers
  near-identical taught `prompt → answer` pairs; `teach` / `teach_batch` grow
  the cache, `size` reports it.
- `LLMResponder` — enriched-prompt LLM generation (always answers).
- `DegradedResponder` — final fallback with `"offline"` / `"refusal"` /
  `"human"` policies when no LLM tier is present.

#### Learning & tuning

- `CacheTeacher(cache, events=None)` — warms the cache from `RESPONSE_PRODUCED`
  and LLM `RESPONDER_HIT` events (`cache`, `taught`).
- `TierMonitor(events=None, tuner=None, window=100)` — per-tier hit/escalation
  dashboard (`summary`, `hit_rate`, `cheap_hit_rate`).
- `TuningLoop(monitor, experience, interval=30.0)` — background gate tuning from
  recorded feedback (`start` / `stop`).
- `EscalationTuner(chain, ...)` — bandit-style gate tuning (`record_hit`, `tune`).
- `CalibratedResponder(responder, calibrator)` — calibrates a tier's confidence
  (RFC-0018 M13).
- `GroundingResponder(responder, checker)` — escalates ungrounded answers
  (RFC-0018 M12).

Wire it with `create_app(router=build_router(...))` or
`create_semantic_app(router="hybrid")` (the string form also wires a
`CacheTeacher`).

### `xyberos.trainer`

- **What it owns:** `export_dataset(experience)`, `Trainer` (embedding/sklearn
  distillation + `save`/`load` artifact registry), and `engine_from_config(config)`.
- **When to use it:** offline training/distillation. `export_dataset` pulls
  `(prompt, intent)` rows from successful episodes; `Trainer(...).train_intent_embedding(embedder)`
  is dependency-free, while `train_intent_sklearn(embedder)` requires
  `pip install xyberos[train]`. Load a saved model at startup via the
  `learning.model` / `learning.algorithm` config keys.

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
  `ToolArgumentError` for missing, unknown, or mistyped arguments. The helpers
  `build_json_schema(func)` and `coerce_arguments(func, arguments)` expose the
  schema generation and coercion directly.

#### `SchemaToolCaller`

- **What it owns:** an `LLMProvider` and a `ToolRegistry`.
- **When to use it:** schema-driven LLM tool selection (RFC-0018 M9) — the LLM
  picks a tool and arguments from the registered tools' JSON schemas, then the
  caller validates and executes it (`select(prompt, context)`, `run(prompt,
  context)`).

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
`confidence`), `EPISODE_RECORDED` (`brain.episode_recorded`), `FEEDBACK_RECORDED`
(`brain.feedback_recorded`), and the plan-loop events `PLAN_STEP_EXECUTED`,
`PLAN_STEP_FAILED`, and `PLAN_REPLANNED`; `ENGINE_TRAINED`/`ENGINE_REFRESHED`
remain future-facing. RFC-0017 adds the router events `RESPONDER_HIT`
(`brain.responder_hit`), `ESCALATED` (`brain.escalated`), `DEGRADED`
(`brain.degraded`), and `CACHE_HIT` (`brain.cache_hit`).

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

### `xyberos.security`

#### `Security`

- **What it owns:** the kill switch, content guardrails, and the audit log.
- **When to use it:** gating every request; reachable as `app.security`. Audit
  events (kill engagements, guardrail triggers, blocked requests) are recorded
  in the configured audit store, accessible via `security.audit_log`.

#### `SqliteAuditStore` / `InMemoryAuditStore` / `AuditStore`

- **What they own:** the audit destination behind `Security.audit_log`.
  `InMemoryAuditStore` is the default; `SqliteAuditStore` (stdlib `sqlite3`)
  persists the audit trail across restarts with no extra dependencies.
- **When to use them:** enable persistence with
  `create_app(config={"security.audit_path": "audit.db"})` (registers the store
  as the `"security.audit_store"` service, so `app.stop()` closes it), or
  construct `Security(audit_store=SqliteAuditStore("audit.db"))` directly and
  inspect it via the `Security.audit_store` property. Any object with
  `append(entry)` / `entries()` can be a custom store (plugin or remote). The
  `Security` facade also exposes `engage_kill_switch(reason, mode=...)` and
  `disengage_kill_switch()` helpers that audit and emit `security.*` events.

### `xyberos.diagnostics`

- `doctor()` - build a developer-focused runtime report
- `DiagnosticReport` - structured diagnostics payload

**When to use it:** debugging an app or inspecting its runtime state.

`DiagnosticReport` is a frozen dataclass with `package_version`,
`python_version`, `app_created`, `kernel_started`, `kernel_services` (a tuple
of registered service names), and `plugin_names` (loaded plugins);
`report.as_dict()` returns a JSON-serializable mapping for logging or
submitting to support.

### Optional extras

The core is dependency-free, but optional capabilities install via extras:

- `pip install xyberos[train]` — scikit-learn + joblib (sklearn intent training).
- `pip install xyberos[vectors]` — chromadb, pgvector, psycopg (optional stores).
- `pip install xyberos[rerank]` — scikit-learn (TF-IDF reranking).
- `pip install xyberos[embeddings]` — sentence-transformers (`SentenceTransformerEmbedder`).
- `pip install xyberos[dev]` — pytest + coverage.

The package ships a `py.typed` marker, so type checkers see the inline types.

### `xyberos.utils`

- `retry(func, max_attempts=3, backoff=0.1, retry_on=Exception, on_retry=None)` - call `func` with exponential backoff.
- `RateLimiter(calls_per_second, burst=1)` - a token-bucket limiter with `acquire()` / `try_acquire()`.
- `with_timeout(seconds, func)` - run `func` with a best-effort timeout (daemon thread).
- `RetryError` - raised when retries are exhausted.
- `GroundingCheck(reference, ...)` / `GroundingResult` - verify a response
  against reference knowledge (`verify(prompt, response)` returns
  `GroundingResult(grounded, confidence, reason)`); RFC-0018 M12.
- `ScoreCalibrator` - Platt-scale score→confidence calibration
  (`fit`, `calibrate`, `is_fitted`, `coefficients`); RFC-0018 M13.

Evaluation helpers (RFC-0016, Phase 2):
- `intent_accuracy(engine, dataset)` - top-1 intent classification accuracy over
  `(prompt, expected_intent)` pairs.
- `retrieval_recall_at_k(store, embedder, dataset, k=5)` - fraction of
  `(query, expected_id)` pairs where the expected id is in the top-k.
- `plan_success_rate(executor, dataset)` - fraction of `(context, plan)` pairs
  executed without an unrecoverable error.

**When to use it:** wrapping LLM or tool calls for resilience, or via the Brain
config keys (`brain.max_attempts`, `brain.retry_backoff`, `brain.rate_limit`,
`brain.timeout`); evaluating whether the trainable engines actually improve.
All SQLite-backed providers use `utils.sqlite.ThreadLocalSQLite` under the hood,
which keeps one `sqlite3` connection per thread so they are safe to call from
FastAPI/thread pools.

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


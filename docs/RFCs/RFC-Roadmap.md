v0.1
[x] Core

v0.2
[x] Service Registry
[x] Dependency Injection

v0.3
[x] Memory Interface

v0.4
[x] Tool Interface

v0.5
[x] Planner

v0.6
[x] Knowledge

v0.7
[x] Workflow

v0.8
[x] Plugin System

v0.9
[x] Multi-Agent Runtime

v1.0
[ ] Stable Architecture

---

# Current Implementation Status (v0.9.0)

All subsystems from v0.1–v0.9 are implemented. The `Brain` orchestrates them
through an automated pipeline for every request:

```text
Workflow (optional)
  ↓
Memory (retrieve)
  ↓
Knowledge (query)
  ↓
Planner (record plan)
  ↓
Tools (dispatch)
  ↓
LLM (generate)
  ↓
Memory (store)
```

The default `create_app()` wires in-memory providers for every subsystem, so a
default app remembers conversations, grounds prompts in knowledge, records a
plan on the context, and dispatches tools automatically. The repository test
suite (105 tests, 98% coverage) is the authoritative description of current
behavior.

---

# Enhancement Backlog

The framework is a working foundation, not yet a production orchestrator. The
following enhancements are planned, roughly in priority order. None of them
change the `Runtime` request/response interface.

## 1. Events and observability (`events/`)

Status: core implemented in v0.9.0.

- [x] Event bus and listener infrastructure in `xyberos/events/` — `EventBus`,
      `Event`, and canonical event names in `events/names.py`.
- [x] Lifecycle events: `kernel.started`, `kernel.stopped`, `plugin.loaded`, `plugin.unloaded`.
- [x] Pipeline events: `runtime.request_started/completed/failed`,
      `brain.workflow_run`, `brain.memory_retrieved/stored`,
      `brain.knowledge_queried`, `brain.plan_created`, `brain.tool_dispatched`,
      `brain.response_produced`, `brain.error`.
- [x] Listener isolation — a failing listener is logged and never breaks the pipeline.
- [x] Tracing hooks: `EventRecorder` (bounded history + per-name counts) and
      `LoggingExporter` (structured event log lines); arbitrary `Exporter`
      callables can be attached to forward events to metrics/tracing backends.
- [ ] Optional: bundled adapters for concrete backends (e.g. OpenTelemetry,
      Prometheus, JSON-lines files).

## 2. Persistent memory and knowledge backends

Status: SQLite implemented in v0.9.0.

- [x] `SqliteMemory` and `SqliteKnowledge` providers under `memory/` and
      `knowledge/` (stdlib `sqlite3`, no runtime dependencies). File-backed
      databases survive process restarts; `start`/`stop` participate in the
      kernel lifecycle so `app.stop()` releases the database handle.
- [x] Existing `contracts/memory.py` and `contracts/knowledge.py` interfaces unchanged.
- [x] Configure via `create_app(memory=SqliteMemory("chat.db"),
      knowledge=SqliteKnowledge("facts.db"))` or plugin registration.
- [ ] Redis (`redis.py`) and vector (`vector.py`) providers — deferred: they
      require optional third-party dependencies and a retrieval/embedding
      strategy. The existing contracts already allow them.

## 3. Branching workflows and state graphs

Status: implemented in v0.9.0.

- [x] `GraphWorkflow` — a directed graph of named steps with fixed `add_edge`
      and conditional `add_route` routing, supporting branches and loops (with
      a `max_steps` guard).
- [x] Pause/resume — a step raises `WorkflowPaused` to pause; `execute` returns
      a `WorkflowRun` and `resume(run, value)` continues with the value injected
      into `context.metadata["workflow.resume_value"]`.
- [x] Human-in-the-loop checkpoints — `WorkflowPaused` carries a `prompt` for
      external input; the Brain and Runtime propagate it as a pause (not an
      error), so it works through `app.run()` / `app.chat()`.
- [x] The existing `contracts/workflow.py` contract is unchanged;
      `GraphWorkflow` implements it (`run` returns the final context and raises
      `WorkflowPaused` on pause).
- [ ] Optional: automatic checkpoints that persist paused runs to disk and
      resume across processes (build on the SQLite providers from item 2).

## 4. Streaming and async

Status: implemented in v0.9.0.

- [x] Async variants — `app.arun` / `app.achat` (plus a module-level `achat`
      helper) flow through `Runtime.arun` and `Brain.achat`. An LLM with an
      async `agenerate` (or `astream`) is awaited; otherwise the sync `generate`
      is used as a fallback.
- [x] Streaming — an LLM may implement `stream(prompt, on_token)` (sync) or
      `astream(...)` (async); the Brain publishes each token as the
      `brain.token_streamed` event.
- [x] LLM helpers — `StreamingLLM` (generate + stream) and `AsyncLLM`
      (async-only `agenerate`).
- [x] Sync stays the default; async is opt-in via `achat` / `arun`.
- [ ] Optional: async variants for `run_agents` and async plugins, plus
      backpressure/rate limiting for streaming.

## 5. Multi-agent collaboration

Status: implemented in v0.9.0.

- [x] Agent-to-agent message contract — `Message` (sender, recipient, content,
      kind, metadata) in `xyberos/agents/messages.py`, with `post(context, msg)`
      and `handoff(target)` helpers.
- [x] Inter-agent messaging — `MultiAgentRuntime` records every message
      (`runtime.messages`), delivers them to recipients that implement
      `receive(message)`, supports `"*"` broadcast, and isolates delivery
      failures. `send(message)` posts directly from application code.
- [x] Handoffs — a `handoff` message runs the recipient next (chained, up to
      `max_handoffs`); each agent runs at most once per `run()` call, and
      `HandoffLoopError` bounds runaway chains.
- [x] Role-based coordination — `RoleAgent(name, role, run, receive)` and
      `runtime.role(name)`.
- [x] Works through the facade (`app.agents`, `app.run_agents`).
- [ ] Optional: async agent collaboration, agent-to-agent conversation state,
      and a dedicated supervisor/re-planning loop.

## 6. LLM-driven planning

Status: implemented in v0.9.0.

- [x] `LLMPlanner` in `xyberos/planner/` — asks the LLM to break the request
      into one-step-per-line, with a custom `parse` callable for other shapes
      (e.g. JSON).
- [x] Config-gated plan injection — `config["brain.inject_plan"] = True` makes
      the Brain append the plan to the model prompt; default stays off so
      default output is unchanged.
- [ ] Optional: a plan execution/verification loop (execute steps, re-plan on
      failure) and confidence/reflection on the plan.

## 7. Structured outputs and typed tool results

Status: implemented in v0.9.0.

- [x] Structured LLM output — `StructuredLLM` and a `structured(llm, prompt)`
      helper in `xyberos/llm/`; `extract_json` tolerates prose and code fences.
      Parse failures raise `StructuredOutputError`.
- [x] Typed tool results — `FunctionTool(name, func)` derives a JSON schema from
      the callable's signature, validates/coerces arguments before invocation,
      and raises `ToolArgumentError` for missing/unknown/mistyped arguments.
- [x] Typed exceptions — `LLMOutputError`/`StructuredOutputError` and
      `ToolArgumentError` exported from `xyberos.exceptions`.
- [ ] Optional: schema-driven LLM function calling (auto-generate tool calls
      from `FunctionTool.schema`) and async structured output.

## 8. Production hardening

Status: implemented in v0.9.0.

- [x] Resilience helpers — `retry` (exponential backoff, configurable `retry_on`),
      `RateLimiter` (token bucket), and `with_timeout` in `xyberos/utils/resilience.py`.
- [x] Config-driven tuning — the Brain reads `brain.max_attempts`,
      `brain.retry_backoff`, `brain.rate_limit`, and `brain.timeout` from
      `Config`. All default to off, so default behavior is unchanged.
- [x] Checkpointing — `WorkflowCheckpoint` persists paused `GraphWorkflow` runs
      to SQLite; `graph.resume_from_checkpoint(...)` resumes across processes.
- [ ] Optional: circuit breakers, jittered backoff, async retries/timeouts, and
      rate limiting for the async path.

## 9. Model adapter catalog

Status: implemented in v0.9.0.

- [x] Dependency-light adapters in `xyberos/llm/adapters.py`:
      `OpenAICompatibleLLM` (any `/chat/completions` endpoint, stdlib HTTP),
      `OllamaLLM` (local server, stdlib HTTP), and lazy-SDK `OpenAILLM`,
      `AnthropicLLM`, `GeminiLLM` (import the SDK only when used and raise a
      clear `ProviderError` if missing).
- [x] The core package keeps zero runtime dependencies.
- [ ] Optional: streaming/async variants for each adapter, and a registry of
      pre-configured provider presets.

## v1.0 — Stable Architecture

- Freeze the public API and contracts.
- Stabilize the enhancement backlog items that prove out in real usage.



For **v0.3**, I would focus on making Xyberos **extensible** rather than adding AI capabilities. The directory structure should reflect that philosophy.

## Repository Structure

```text
Xyberos_v2/
│
├── docs/
│
├── test/
│
├── xyberos/
│
├── README.md
├── pyproject.toml
├── pytest.ini
└── .gitignore
```

The repository root contains project documentation, RFCs, examples, tests, and the Python package.

---

# Python Package

```text
xyberos/
│
├── __init__.py
├── version.py
├── xyberos.py
│
├── kernel/
│   ├── __init__.py
│   ├── kernel.py
│   ├── config.py
│   ├── logger.py
│   └── registry.py
│
├── runtime/
│   ├── __init__.py
│   ├── runtime.py
│   └── context.py
│
├── brain/
│   ├── __init__.py
│   ├── brain.py
│   └── llm.py
│
├── contracts/
│   ├── __init__.py
│   ├── agent.py
│   ├── knowledge.py
│   ├── llm.py
│   ├── memory.py
│   ├── planner.py
│   ├── plugin.py
│   ├── service.py
│   ├── tool.py
│   └── workflow.py
│
├── agents/
│   ├── __init__.py
│   ├── multi_runtime.py
│   └── runtime_agent.py
│
├── workflows/
│   ├── __init__.py
│   └── sequential.py
│
├── plugins/
│   ├── __init__.py
│   └── loader.py
│
├── events/
│   └── __init__.py
│
├── memory/
│   └── in_memory.py
├── knowledge/
│   └── in_memory.py
├── planner/
│   └── sequential.py
├── tools/
│   └── registry.py
│
├── exceptions/
│   ├── __init__.py
│   ├── agent.py
│   ├── kernel.py
│   ├── plugin.py
│   ├── provider.py
│   ├── registry.py
│   └── runtime.py
│
└── utils/
    ├── __init__.py
    └── typing.py
```

---

# Purpose of Each Package

## `kernel/`

Owns the platform.

```text
Kernel
├── Config
├── Logger
└── Registry
```

Nothing in this package performs reasoning.

---

## `runtime/`

Owns execution.

```text
Context

↓

Brain

↓

Context
```

The Runtime should remain largely unchanged as the framework grows.

---

## `brain/`

Owns cognition.

Today (v0.9):

```text
Prompt

↓

Workflow (optional)

↓

Memory (retrieve)

↓

Knowledge (query)

↓

Planner (record plan)

↓

Tools (dispatch)

↓

LLM (generate)

↓

Memory (store)

↓

Response
```

Every subsystem is optional, so a bare Brain is still a plain LLM wrapper.
Future versions may add LLM-driven planning, reflection, streaming, and
structured outputs internally without changing the Runtime interface.

---

## `contracts/`

This becomes the most important package in v0.3.

```text
contracts/

Agent
Knowledge
LLMProvider
Memory
Planner
Plugin
Service
Tool
Workflow
```

Every future implementation depends on these contracts.

Example:

```python
class Memory(ABC):

    @abstractmethod
    def retrieve(self, context):
        ...

    @abstractmethod
    def store(self, context):
        ...
```

No concrete implementation belongs here.

---

## `exceptions/`

Framework-specific exceptions.

```text
KernelError

RegistryError

ProviderError

RuntimeError
```

Avoid raising generic `Exception`.

---

## `utils/`

Keep this intentionally small.

Only place truly shared helpers here, such as:

```text
typing.py

validators.py

constants.py
```

If a helper only serves one package, keep it in that package instead.

---

## `agents/`

Multi-agent coordination. `MultiAgentRuntime` runs named agents sequentially
against one canonical `CognitiveContext`; `RuntimeAgent` adapts an existing
`Runtime` into an `Agent`.

## `workflows/`

Composable execution. `SequentialWorkflow` applies ordered steps to a context,
where each step may mutate the context in place or return a replacement.

## `plugins/`

Discovery and lifecycle. `PluginLoader` imports, auto-discovers, and manages
plugins — both via `load_entry_points()` (Python entry-point groups, the same
mechanism pytest uses) and `load_from_package()` (convention-based package
scanning for `Plugin` subclasses). Plugins are given controlled access to the
platform kernel through `register`/`unregister`.

## `events/`

Observability. `EventBus` publishes lifecycle and pipeline events (kernel,
plugin, runtime, and brain); applications subscribe to canonical names in
`events/names.py`. Listeners are isolated so a failing hook never breaks the
pipeline.

---

# Dependency Rules

One of the most valuable additions in v0.3 is documenting allowed dependencies.

```text
                Kernel
                    ▲
                    │
      ┌─────────────┼─────────────┐
      │             │             │
 Runtime         Brain       Contracts
      │             │
      └──────► Context
                    │
                    ▼
                  LLM
```

Allowed imports:

```text
Runtime  → Brain

Brain    → Contracts

Kernel   → Contracts

Runtime  → Context
```

Forbidden imports:

```text
Brain → Runtime

Kernel → Brain

Contracts → Runtime

Contracts → Kernel
```

This prevents circular dependencies and preserves a layered architecture.

---

# Future Growth

The structure scales cleanly without reorganizing the project.

```text
xyberos/

kernel/
runtime/
brain/
contracts/
agents/
workflows/
plugins/
events/

memory/
knowledge/
planner/
tools/
```

The `kernel/`, `runtime/`, `brain/`, `contracts/`, `agents/`, `workflows/`,
`plugins/`, `memory/`, `knowledge/`, `planner/`, and `tools/` subsystems are
implemented. The initial `memory/`, `knowledge/`, `planner/`, and `tools/`
providers are minimal in-memory references; production backends can replace
them while keeping the same `contracts/` interfaces.

For example:

```text
xyberos/

contracts/
    memory.py

memory/
    __init__.py
    in_memory.py
    sqlite.py
    redis.py
    vector.py
```

The `memory/` package provides implementations, while `contracts/memory.py` defines the interface they all satisfy.

---

## Long-term Vision

If you continue following this architecture, the framework naturally evolves into:

```text
xyberos/
│
├── kernel/        # Platform services
├── runtime/       # Execution engine
├── brain/         # Cognitive engine
├── contracts/     # Public extension API
├── memory/        # Memory providers
├── knowledge/     # Knowledge providers
├── planner/       # Planning engines
├── tools/         # Tool implementations
├── events/        # Event bus
├── plugins/       # Plugin loader
├── workflows/     # Workflow engine
└── agents/        # Multi-agent support
```

This organization has a consistent pattern:

* **Core packages** (`kernel`, `runtime`, `brain`) define the platform.
* **Contracts** define stable extension points.
* **Feature packages** implement those contracts.
* **Repository-level RFCs** govern how the architecture evolves.

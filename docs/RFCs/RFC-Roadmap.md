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
[x] Stable Architecture

---

# Current Implementation Status (v1.0.x)

All subsystems from v0.1–v1.0 (RFC-0001…RFC-0015) are implemented, and the
RFC-0016 trainable engines and RFC-0017/0018 hybrid router are shipped on top.
The `Brain` orchestrates them through an automated pipeline for every request:

```text
Workflow (optional)
  ↓
Cheap-first router tiers (template → tool → knowledge → memory → cache)
  ↓
Memory (retrieve)
  ↓
Knowledge (query)
  ↓
Intent (classify, if enabled)
  ↓
Planner (record plan)
  ↓
Router (confident tier short-circuits)
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
suite (533 tests, 89% coverage) is the authoritative description of current
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
- [x] Vector providers (`vector.py`) — shipped in RFC-0016: `CosineVectorStore`
      (dependency-free) plus optional `ChromaVectorStore`/`PgVectorStore`
      adapters (`xyberos[vectors]`). Redis (`redis.py`) remains deferred: it
      requires an optional third-party dependency.

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
- [x] Automatic checkpoints that persist paused runs to disk and resume across
      processes — `WorkflowCheckpoint` + `GraphWorkflow.resume_from_checkpoint(...)`
      (builds on the SQLite providers from item 2).

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
- [x] Optional: a plan execution/verification loop (execute steps, re-plan on
      failure) and confidence/reflection on the plan — shipped in RFC-0016
      (`PlanExecutor`, `ReflectivePlanner`).

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
- [x] Schema-driven LLM function calling — `SchemaToolCaller` auto-generates
      tool calls from registered `FunctionTool.schema`s (RFC-0018 M9).
- [ ] Optional: async structured output.

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
      `OllamaLLM` (local server, stdlib HTTP), `OllamaEmbeddingLLM` (local
      `/api/embed`, stdlib HTTP, exposes `embed`), and lazy-SDK `OpenAILLM`,
      `AnthropicLLM`, `GeminiLLM` (import the SDK only when used and raise a
      clear `ProviderError` if missing).
- [x] The core package keeps zero runtime dependencies.
- [ ] Optional: streaming/async variants for each adapter, and a registry of
      pre-configured provider presets.

## v1.0 — Stable Architecture  ✅

With the addition of the Security service (RFC-0015), Xyberos v1.0 is a
**complete cognitive platform**. Every RFC-0001 subsystem is implemented,
tested, and integrated:

| # | Subsystem | Status |
|---|---|---|
| RFC-0001 | Architecture | ✅ |
| RFC-0002 | Kernel | ✅ |
| RFC-0003 | Runtime | ✅ |
| RFC-0004 | Brain | ✅ |
| RFC-0005 | Context | ✅ |
| RFC-0006 | LLM Provider | ✅ |
| RFC-0007 | Memory | ✅ |
| RFC-0008 | Knowledge | ✅ |
| RFC-0009 | Planner | ✅ |
| RFC-0010 | Tools | ✅ |
| RFC-0011 | Workflows | ✅ |
| RFC-0012 | Agents | ✅ |
| RFC-0013 | Plugins | ✅ |
| RFC-0014 | Events | ✅ |
| RFC-0015 | Security | ✅ |
| RFC-0016 | Trainable Cognitive Engines | ✅ |
| RFC-0017 | LLM-as-Fallback & Self-Routing | ✅ |
| RFC-0018 | Smarter Learning | ✅ |

The public API, contracts, and event names are stable. The core stays on the 1.x
line and is **extended additively** — new contracts and providers may be added
without changing existing ones, while plugins remain the primary way to ship
capabilities (see RFC-0016).

> **RFC-0016 (Implemented)** — *Trainable Cognitive Engines*: adds small additive seams for
> an **intent engine**, **embeddings/vector retrieval**, and an **experience/learning
> layer**, then implements trainable (few-shot / semantic / outcome-based) providers for
> intent, planner, memory, and knowledge. Runtime adaptation is the default "training";
> fine-tuning is an optional Phase-3 plugin. Phases 0–3 complete. See
> `docs/RFCs/RFC-0016-trainable-cognitive-engines.md`.

> **RFC-0017 (Implemented)** — *LLM-as-Fallback & Self-Routing*: a confidence-gated
> `xyberos.router` package — `ResponderChain`, `build_router`, the template/tool/
> knowledge/memory/cache/LLM/degraded responders, `CacheTeacher`, `TierMonitor`,
> `TuningLoop`, `EscalationTuner`, `CalibratedResponder`, and `GroundingResponder` —
> so the LLM becomes the last resort and teacher instead of the primary generator.
> Wire it with `create_app(router=...)` or `create_semantic_app(router="hybrid")`;
> all default-off. See `docs/RFCs/RFC-0017-llm-fallback-router.md`.

> **RFC-0018 (Implemented)** — *Smarter Learning*: auto-outcome signals and the eval
> workflow (`xyberos.utils.eval`), immediate reinforcement (`ExamplePromoter`,
> `KnowledgePromoter`), schema-driven tool calling (`SchemaToolCaller`), self-expanding
> knowledge, memory stratification (`StratifiedMemory`, `extract_facts_deterministic`),
> grounding (`GroundingCheck`, `GroundingResponder`), reranking (`LexicalReranker`), and
> confidence calibration (`ScoreCalibrator`, `CalibratedResponder`). See
> `docs/RFCs/RFC-0018-smarter-learning.md`.

> **Build order (RFC-0017 + RFC-0018)** — one shared, ordered milestone sequence
> **M0 → M12** lives in both RFCs (identical). Follow it in order to avoid missteps:
> M0 done (`FallbackLLM`) → M1–M3 signals & measurement → M4 router skeleton
> (inactive) → M5–M7 store-filling/capability → M8 activate routing → M9–M10 quality &
> calibration → M11–M12 escalation learning & degrade.

---

# What Can You Build on Xyberos Now?

Xyberos is a general-purpose cognitive runtime. It provides the **how**
(pipeline, memory, planning, tools, agents, security) and leaves the **what**
to plugins and applications. Here are the categories of systems it can power:

## 1. AI-Powered IDEs and Developer Tools

Xyberos already has the primitives: streaming tokens, multi-agent
collaboration, typed tools, and observability. An IDE plugin could:

- **Code assistant agent** — a `RuntimeAgent` that reads files, runs lint,
  suggests fixes, and streams results
- **Code review agent** — supervisors hand off to specialist reviewers
  (security, style, performance)
- **Refactoring workflow** — a `GraphWorkflow` that plans → applies → tests →
  reverts on failure, with human-in-the-loop approval at each step
- **Documentation generator** — a tool that reads source, queries a knowledge
  base of project conventions, and produces docs

The `Tool` contract maps naturally to IDE capabilities: `read_file`,
`run_test`, `git_diff`, `search_codebase`. The `Guardrail` system can block
destructive operations before they execute.

## 2. Robotics and Embodied AI

The multi-agent runtime and workflow engine make Xyberos suitable for
robotics control loops:

- **Perception → Plan → Act loop** — the Brain pipeline already does this;
  swap the LLM for a vision-language model and tools for motor commands
- **Hierarchical agents** — a supervisor agent delegates to navigation,
  manipulation, and safety agents via handoffs
- **Human-in-the-loop** — `GraphWorkflow` pause/resume is purpose-built for
  "robot wants to grab something, human approves"
- **Safety kill switch** — the `KillSwitch` in `Security` is a literal
  emergency stop; engage it and ALL motor commands halt immediately
- **Sensor fusion** — each sensor is a `KnowledgeProvider`; the Brain queries
  them all before planning

## 3. Customer Support and Service Desks

The `support_assistant` example already demonstrates this:

- **Intent routing** — tools match order IDs, ticket creation, FAQ lookups
- **Escalation** — supervisor agent hands off to human agents
- **Refund workflows** — pause for approval, resume with decision
- **Persistent memory** — SQLite-backed conversation history survives restarts
- **Audit trail** — every security event, tool dispatch, and handoff is logged

## 4. Autonomous Research Assistants

- **Multi-step research** — `LLMPlanner` decomposes "summarize the state of X"
  into search → read → synthesize → cite
- **Tool chain** — web search, paper retrieval, citation formatting as
  `FunctionTool`s
- **Knowledge accumulation** — `SqliteKnowledge` grows with each query
- **Streaming output** — results stream token-by-token to the UI

## 5. Game NPCs and Interactive Fiction

- **Role-based agents** — each NPC is a `RoleAgent` with a persona, goals,
  and memory
- **Dynamic conversations** — agents message each other; the multi-agent
  runtime coordinates
- **World state as context** — `CognitiveContext.metadata` carries game state
- **Workflow-driven quests** — a `GraphWorkflow` encodes quest logic with
  branching, loops, and checkpoints

## 6. Data Pipelines and ETL with AI

- **LLM-driven transformations** — a tool that classifies, summarizes, or
  translates rows
- **Quality gates** — guardrails block malformed outputs
- **Observability** — every transformation emits events; tracing tracks the
  full pipeline
- **Plugin architecture** — each data source/sink is a plugin

## 7. Personal AI Assistants

- **Tool-rich** — calendar, email, notes, search, all as `FunctionTool`s
- **Persistent** — `SqliteMemory` and `SqliteKnowledge` across sessions
- **Safe** — guardrails block sharing sensitive data; kill switch disables
  the assistant entirely
- **Extensible** — new capabilities ship as plugins via entry points

---

# Plugin-First Philosophy

Xyberos is **open to plugins**, and the core may be extended **additively** — new
contracts and providers that do not change existing ones (see RFC-0016).
The platform provides:

| Platform Capability | Plugin Opportunity |
|---|---|
| `Tool` contract | Any API, database, or device |
| `Memory` contract | Redis, Postgres, vector DBs |
| `Knowledge` contract | Graph DBs, embedding stores, remote APIs |
| `Planner` contract | Specialized planners (ToT, ReAct, custom) |
| `Workflow` contract | DSLs, visual editors, BPMN |
| `Agent` contract | Domain-specific agents (code, legal, medical) |
| `Plugin` contract | Third-party packages via entry points |
| `Security` contract | Custom guardrails, external auth, WAF integration |
| `EventBus` | OpenTelemetry, Prometheus, Datadog exporters |

A plugin author only needs to implement one contract and declare an entry
point — the Kernel handles discovery, lifecycle, and dependency injection.

---

# Community Roadmap (Plugin Ideas)

These are not core features — they are **plugin opportunities** for the
community:

### Developer Tools
- VS Code / JetBrains extension using Xyberos as the agent runtime
- GitHub bot that reviews PRs with multi-agent collaboration
- CLI chat with streaming, tool calling, and persistent context

### Robotics
- ROS 2 integration — each ROS node as a `Tool` or `KnowledgeProvider`
- Sensor fusion — camera, lidar, IMU as knowledge providers feeding the Brain
- Motor control — tools with hardware-level safety guardrails

### Enterprise
- Slack / Teams bot with role-based escalation agents
- CRM integration — tools for Salesforce, HubSpot, Zendesk
- Compliance audit — every action logged, every decision traceable

### Creative
- Interactive storytelling engine — NPCs as agents, plot as workflow
- Music / art generation — tools wrap Stable Diffusion, MusicGen, etc.
- Game master AI — coordinates player actions, NPC reactions, world state

### Research
- Paper summarization pipeline — search → filter → read → synthesize
- Experiment runner — hypothesis → design → execute → analyze loop
- Literature review agent — multi-step research with citation graph

---

Xyberos is no longer a framework under construction — it is a **platform**
for building cognitive systems. The core is done. The rest is plugins.

---

This organization has a consistent pattern:

* **Core packages** (`kernel`, `runtime`, `brain`) define the platform.
* **Contracts** define stable extension points.
* **Feature packages** implement those contracts.
* **Repository-level RFCs** govern how the architecture evolves.

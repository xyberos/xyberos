# Xyberos

Xyberos is an experimental cognitive framework for building AI systems.
It provides a small layered core:

- `Kernel` for services, configuration, logging, lifecycle, and plugins
- `Runtime` for request execution
- `Brain` for response generation
- `LLM` for model/provider abstraction

## Status

Current version: `0.9.0`

Implemented:

- Kernel, service registry, dependency injection, and lifecycle management
- Runtime and cognitive context
- Brain and LLM abstraction, with an automated cognitive pipeline that wires
  memory, knowledge, planner, workflow, and tools into every request
- Contracts for agent, tool, memory, planner, knowledge, workflow, plugin, and service
- Sequential workflow engine
- Multi-agent runtime with a runtime adapter
- Event bus and pipeline observability (kernel, plugin, runtime, and brain events)
- Persistent SQLite memory and knowledge providers (stdlib, no dependencies)
- Plugin loading and unloading, with entry-point auto-discovery
- Typed exception hierarchy

The repository test suite is the best indicator of current behavior. At the time of this docs pass, the project test suite passes locally.

## Install

```bash
pip install -e .
```

For development tooling:

```bash
pip install -e ".[dev]"
```

## Quick Start

```python
from xyberos import create_app
from xyberos.llm import CallableLLM

# Default model is EchoLLM, which simply returns the prompt.
app = create_app()
print(app.chat("hello"))  # hello

# Provide your own model implementation.
app = create_app(llm=CallableLLM(lambda prompt: f"handled: {prompt}"))
print(app.chat("hi"))  # handled: hi
```

For a guided, single-script walkthrough that grows from this hello world into a
full-stack app, run
[`examples/hello_world_to_full_stack/app.py`](examples/hello_world_to_full_stack/app.py).

A real chat backend with FastAPI, SQLAlchemy, and pluggable auto-discovery lives
in [`examples/chat_app/`](examples/chat_app/README.md).

## Public API

Import the main facade from the package root:

```python
from xyberos import Xyberos, chat, create_app
```

### `create_app(config=None, llm=None, memory=None, knowledge=None, tools=None, planner=None, workflow=None, tool_runner=None)`

Builds a ready-to-use `Xyberos` application. Any provider you omit is filled in
with an in-memory default.

### `chat(prompt, config=None, llm=None, ...)`

Convenience helper that creates an app and returns the generated response text.
It accepts the same provider arguments as `create_app`.

### `Xyberos`

The application facade exposes the key runtime services:

- `config`
- `logger`
- `registry`
- `plugins`
- `events`
- `llm`
- `memory`
- `knowledge`
- `tools`
- `tool_runner`
- `planner`
- `workflow`
- `brain`
- `runtime`
- `agents`
- `started`

It also provides methods for service registration, dependency injection, plugin management,
agent management, and request execution.

## Core Concepts

### Kernel

The `Kernel` owns platform services and lifecycle management.

Typical responsibilities:

- store configuration
- expose logging
- register and resolve services
- inject constructor dependencies by parameter name
- start and stop lifecycle-aware services
- load and unload plugins

### Runtime

The `Runtime` executes a `CognitiveContext` by delegating to the configured `Brain`.

### Brain

The `Brain` is the cognitive orchestration layer. For every request it runs an
automated pipeline across the pluggable subsystems:

1. **Workflow** — run configured steps first; a step that sets the response is honored.
2. **Memory** — retrieve past turns and inject them into the prompt as history.
3. **Knowledge** — query relevant facts and inject them into the prompt.
4. **Planner** — run the planner and record its plan on `context.plan`.
5. **Tools** — dispatch a matching tool through the `ToolRunner`.
6. **LLM** — generate the response.
7. **Memory** — store the completed turn so future requests can recall it.

Every subsystem is optional; a bare `Brain` behaves like a plain LLM wrapper.
Concrete LLM services live under `xyberos.llm`.

### Cognitive Context

`CognitiveContext` carries:

- `prompt`
- `response`
- `metadata`
- `error`
- `plan` — the plan produced by the planner during processing

It is the canonical object passed through the runtime pipeline.

### Multi-Agent Runtime

`MultiAgentRuntime` runs registered agents sequentially against one context.
`RuntimeAgent` adapts an existing runtime into the agent contract.

### Workflow Engine

`SequentialWorkflow` executes a list of callables in order.
Each step may mutate the context in place or return a replacement context.

### Planner

`SequentialPlanner` is a simple ordered planning implementation.
It is intentionally small and can be replaced with a more sophisticated planner later.

### Memory and Knowledge

`InMemoryMemory` and `InMemoryKnowledge` are lightweight in-process providers for
tests and development. `SqliteMemory` and `SqliteKnowledge` persist data to a
SQLite database (stdlib `sqlite3`, no dependencies) and survive process
restarts:

```python
from xyberos import create_app
from xyberos.memory import SqliteMemory
from xyberos.knowledge import SqliteKnowledge

app = create_app(
    memory=SqliteMemory("chat.db"),
    knowledge=SqliteKnowledge("facts.db"),
)
```

### Tools

`ToolRegistry` registers named tools and executes them by name.
`ToolRunner` adds a small dispatch layer that chooses and executes a tool against a context.

### Plugins

`PluginLoader` loads plugin instances, imports them from modules, and supports two auto-discovery
styles so modules/services register themselves without manual wiring:

- **Entry points** (`app.load_entry_points()`): finds every plugin declared under `[project.entry-points."xyberos.plugins"]` via `importlib.metadata` — the same mechanism pytest and uvicorn use.
- **Convention scan** (`app.load_plugins_from("package")`): walks a package and loads every concrete `Plugin` subclass it finds. Drop a module in the folder and it is wired up.

Both are idempotent — re-running discovery never double-registers a plugin.

### Events and Observability

The kernel exposes an `EventBus` (also registered as the `events` service, and
reachable as `app.events`). The kernel, plugin loader, runtime, and brain
publish canonical lifecycle and pipeline events:

```python
from xyberos import create_app
from xyberos.events import RESPONSE_PRODUCED

app = create_app()
app.events.subscribe(RESPONSE_PRODUCED, lambda event: print(event.data["response"]))
```

Events cover `kernel.started/stopped`, `plugin.loaded/unloaded`,
`runtime.request_started/completed/failed`, and the brain pipeline steps
(`brain.workflow_run`, `brain.memory_retrieved/stored`,
`brain.knowledge_queried`, `brain.plan_created`, `brain.tool_dispatched`,
`brain.response_produced`, `brain.error`). A listener that raises is logged and
isolated — it never breaks the pipeline.

For analysis, attach an `EventRecorder` to capture every event with bounded
history and per-name counts, and forward them to exporters:

```python
from xyberos import create_app
from xyberos.events import EventRecorder, LoggingExporter

app = create_app()
recorder = EventRecorder(limit=1000).subscribe_to(app.events)
recorder.add_exporter(LoggingExporter(app.logger))
print(recorder.counts())  # events per name for dashboards
```

Any callable `event -> None` is an exporter, so integrating a metrics or
tracing backend is just a function.

## Examples

### Minimal Chat App

### Minimal Chat App

```python
from xyberos import create_app

app = create_app()
print(app.chat("Say hello"))
```

### Register a Service

```python
from xyberos import create_app

app = create_app()
app.register("answer", 42)
print(app.resolve("answer"))
```

### Dependency Injection

```python
from xyberos import create_app

app = create_app()

def build_message(logger, config):
    return f"{logger!r}:{config.as_dict()}"

message = app.inject(build_message)
```

### Multi-Agent Execution

```python
from xyberos import create_app

app = create_app()
result = app.run_agents("hello")
print(result.prompt)
```

## Exceptions

Xyberos exposes a structured exception hierarchy under `xyberos.exceptions` for:

- agents
- plugins
- tools
- registry / dependency resolution
- runtime / context execution
- kernel / provider errors

## Project Layout

```text
xyberos/
  agents/      multi-agent coordination
  brain/       brain orchestration and LLM adapters
  contracts/   extension contracts
  exceptions/  typed domain exceptions
  kernel/      config, logging, registry, lifecycle
  knowledge/   knowledge providers
  memory/      memory providers
  planner/     planning providers
  plugins/     plugin loading
  runtime/     context and runtime execution
  tools/       tool registry
  workflows/   workflow execution
  docs/        RFCs and documentation index
```

## Documentation

Start here:

- [Documentation Index](docs/README.md)
- [Architecture RFCs](docs/RFCs/)

## Testing

Run the test suite:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=xyberos
```

## Future Enhancements

The current implementation is a working foundation with a fully automated
cognitive pipeline. The enhancement backlog — events and observability,
persistent memory and knowledge backends, branching workflows, streaming,
multi-agent collaboration, and production hardening — is tracked in the
[Roadmap](docs/RFCs/RFC-Roadmap.md).

## Notes

- The package requires Python 3.10 or newer.
- The repository uses `setuptools` packaging.
- The public API is intentionally small and stable at the package root.

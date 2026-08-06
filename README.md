<p align="center">
  <h1 align="center">Xyberos</h1>
  <p align="center"><strong>The cognitive platform for AI systems.</strong></p>
</p>

---

**Xyberos** is a complete, layered platform for building AI applications —
agents, tools, workflows, multi-agent collaboration, streaming, memory,
knowledge, planning, plugins, observability, and security. Every subsystem
is swappable through stable contracts. The core has **zero runtime dependencies**.

```text
                 ┌──────────────────────────────┐
                 │          Kernel               │
                 │  Config · Logger · Registry   │
                 │  EventBus · Plugins · Security │
                 └──────────────┬───────────────┘
                                │
    ┌───────────────┐  ┌────────┴────────┐  ┌───────────────┐
    │    Runtime    │  │     Brain        │  │   Contracts   │
    │  sync · async │  │  Pipeline Engine │  │ 15 interfaces │
    └───────┬───────┘  └────────┬─────────┘  └───────────────┘
            │                   │
            └──── Context ──────┘
```

You bring **what** the system should do. Xyberos provides **how** — the
pipeline, the memory, the planning, the tools, the agents, the guardrails.

---

## Platform at a Glance

| Subsystem | What it does |
|---|---|
| **Kernel** | Config, logging, DI, lifecycle, event bus, plugin loader, security |
| **Runtime** | Executes cognitive requests — sync and async |
| **Brain** | Automated pipeline: workflow → memory → knowledge → plan → tools → LLM |
| **LLM** | OpenAI, Anthropic, Gemini, Ollama, any OpenAI-compatible endpoint |
| **Memory** | In-memory and SQLite providers — swap for Redis or vectors |
| **Knowledge** | Fact injection from in-memory dicts or SQLite |
| **Planner** | Sequential or LLM-driven plan generation |
| **Tools** | Typed function tools with JSON-schema signatures |
| **Workflows** | Sequential + graph-based with branches, loops, pause/resume |
| **Agents** | Multi-agent runtime with messaging, handoffs, roles |
| **Plugins** | Auto-discovery via entry points or package scanning |
| **Events** | Pub/sub bus with 19 canonical events, tracing, and exporters |
| **Security** | Kill switch, content guardrails, audit logging |

---

## Install

```bash
pip install xyberos
```

That's it. Zero runtime dependencies — the standard library is all it needs.

```bash
pip install xyberos[dev]     # pytest + coverage for development
```

Or install from source:

```bash
git clone https://github.com/xyberos/xyberos.git
cd xyberos
pip install -e .
```

---

## Quick Start

```python
from xyberos import create_app

app = create_app()
print(app.chat("Hello, world!"))  # "Hello, world!"
```

No API keys. No config. The default `EchoLLM` echoes your prompt — zero
dependencies, zero setup. Swap in a real model when you're ready:

```python
from xyberos.llm import OllamaLLM

app = create_app(llm=OllamaLLM(model="qwen2.5:1.5b"))
print(app.chat("Explain quantum computing in one sentence."))
```

---

## What You Can Build

### AI-Powered IDE or Dev Tool
Multi-agent code review with streaming, guardrails blocking destructive ops,
tools for `read_file` / `run_test` / `git_diff`. Each step is a workflow node
with human approval.

### Robotics Controller
Perception → Plan → Act loop. Hierarchical agents (supervisor → navigation →
manipulation). **Literal emergency stop** via `Security.engage_kill_switch()` —
all motor commands halt immediately.

### Customer Support Platform
Intent routing via typed tools, escalation through agent handoffs, refund
workflows that pause for human approval, persistent SQLite conversation
history, full audit trail.

### Autonomous Research Assistant
`LLMPlanner` decomposes "summarize the state of X" into search → read →
synthesize → cite. Every result streams token-by-token.

### Anything else
Every subsystem is a plugin surface. The platform is done — the rest is
building blocks.

---

## Core Concepts

### Security & Kill Switch

```python
app.security.engage_kill_switch("emergency maintenance")
app.chat("hello")  # raises SecurityHaltError

app.security.disengage_kill_switch()
app.chat("hello")  # works again

# Block harmful prompts
from xyberos import Guardrail
app.security.add_guardrail(
    Guardrail("no-hacks", lambda ctx: "hack" not in ctx.prompt)
)
```

### Multi-Agent Collaboration

```python
from xyberos.agents import RoleAgent, handoff, post

def supervisor(context):
    post(context, handoff("worker", sender="supervisor"))
    return context

def worker(context):
    context.response = f"Handled: {context.prompt}"
    return context

app.register_agent(RoleAgent("supervisor", "triage", run=supervisor))
app.register_agent(RoleAgent("worker", "resolver", run=worker))
app.run_agents("escalate this", agent_names=["supervisor", "worker"])
```

### Human-in-the-Loop Workflows

```python
from xyberos.workflows import GraphWorkflow
from xyberos.exceptions import WorkflowPaused

def approve(context):
    if context.metadata.get("approved"):
        context.response = "Approved!"
        return context
    raise WorkflowPaused("Approve this action? yes/no")

graph = GraphWorkflow("approve")
graph.add_node("approve", approve)

run = graph.execute(context)
while run.status == "paused":
    answer = input(run.prompt + " ")   # human decides
    run = graph.resume(run, answer)
```

### Streaming & Async

```python
# Stream tokens as they arrive
app.events.subscribe("brain.token_streamed", lambda e: print(e.data["token"], end=""))
app.chat("Write a haiku about code.")

# Async pipeline
response = await app.achat("Summarize this document.")
```

### Observability

```python
from xyberos.events import EventRecorder

recorder = EventRecorder(limit=10_000).subscribe_to(app.events)
app.chat("hello")
print(recorder.counts())
# {'brain.response_produced': 1, 'brain.memory_stored': 1, ...}
```

### LLM-Driven Planning

```python
app = create_app(
    config={"brain.inject_plan": True},
    planner=LLMPlanner(your_llm),
)
# The model sees: "Plan: 1. research 2. draft 3. review\n\nUser: ..."
```

### Persistent Memory & Knowledge

```python
app = create_app(
    memory=SqliteMemory("chat.db"),       # survives restarts
    knowledge=SqliteKnowledge("facts.db"), # curated domain facts
)
app.knowledge.add("hours", "Support is available 9am-6pm Mon-Fri.")
```

---

## Production Hardening

Built-in, config-driven, all off by default:

```python
app = create_app(config={
    "brain.max_attempts": 3,       # retry on failure
    "brain.retry_backoff": 0.5,    # exponential backoff
    "brain.rate_limit": 10.0,      # calls per second
    "brain.timeout": 30,           # seconds
})
```

- **Retries** with exponential backoff
- **Rate limiting** with token bucket
- **Timeouts** on LLM calls
- **Checkpointing** — paused workflows persist to SQLite across restarts
- **Kill switch** — emergency halt for all processing

---

## Tests

```bash
pip install xyberos[dev]
pytest
```

242 tests, 95% coverage. The test suite is the authoritative reference for
current behavior.

---

## Documentation

Full documentation at **[xyberos-docs.pages.dev](https://xyberos-docs.pages.dev)** (or `mkdocs serve` locally):

- [Tutorial](https://xyberos-docs.pages.dev/tutorial/)
- [API Reference](https://xyberos-docs.pages.dev/api-reference/)
- [Roadmap & Vision](https://xyberos-docs.pages.dev/RFCs/RFC-Roadmap/)
- [15 Architecture RFCs](https://xyberos-docs.pages.dev/RFCs/RFC-0001-architecture/)

Run locally:

```bash
pip install mkdocs mkdocs-material
mkdocs serve
```

---

## Examples

| Example | What it shows |
|---|---|
| [`examples/minimal_chat.py`](examples/minimal_chat.py) | Shortest possible chat |
| [`examples/configuring_services.py`](examples/configuring_services.py) | Three ways to wire services |
| [`examples/extended_app.py`](examples/extended_app.py) | Full app API walkthrough |
| [`examples/chat_app/`](examples/chat_app/README.md) | FastAPI + SQLAlchemy backend |
| [`examples/support_assistant/`](examples/support_assistant/README.md) | Every subsystem in one service |
| [`examples/hello_world_to_full_stack/`](examples/hello_world_to_full_stack/README.md) | One script, from one-liner to full stack |

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

<p align="center"><strong>Core done. Build anything.</strong></p>

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

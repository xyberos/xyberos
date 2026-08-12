# 1. What is Xyberos?

[**Next →**](02-getting-started.md)

## What You'll Learn

- What Xyberos is and what problem it solves
- Xyberos vs. building an AI app from scratch
- Xyberos vs. agent frameworks
- The core philosophy: flexible, extendible, swappable, composable
- What kinds of applications you can build

---

## What is Xyberos?

**Xyberos is a continuously evolving, layered platform for building AI
applications.** Its architecture is designed to support capabilities including
agents, tools, workflows, multi-agent collaboration, streaming, memory,
knowledge, planning, trainable intent and learning engines, plugins,
observability, and security as the platform develops. Every subsystem is built
around stable contracts, allowing components to be independently extended,
replaced, or improved over time. The core is designed with **zero runtime
dependencies**.

> **The core is zero-dependency.** It uses only the Python standard library.
> `pip install xyberos` — that's it.

You bring **what** the system should do. Xyberos provides **how** — the
pipeline, the memory, the planning, the tools, the agents, the guardrails.

```text
                 ┌────────────────────────────────┐
                 │          Kernel                │
                 │  Config · Logger · Registry    │
                 │  EventBus · Plugins · Security │
                 └──────────────┬─────────────────┘
                                │
    ┌───────────────┐  ┌────────┴─────────┐  ┌───────────────┐
    │    Runtime    │  │     Brain        │  │   Contracts   │
    │  sync · async │  │  Pipeline Engine │  │ 15 interfaces │
    └───────┬───────┘  └────────┬─────────┘  └───────────────┘
            │                   │
            └──── Context ──────┘
```

## Platform at a Glance

| Subsystem | What it does |
|---|---|
| **Kernel** | Config, logging, DI, lifecycle, event bus, plugin loader, security |
| **Runtime** | Executes cognitive requests — sync and async |
| **Brain** | Automated pipeline: workflow → cheap-first router → memory → knowledge → intent → plan → router → tools → LLM |
| **LLM** | OpenAI, Anthropic, Gemini, Ollama, any OpenAI-compatible endpoint + embeddings (incl. local `OllamaEmbeddingLLM`) |
| **Memory** | In-memory, SQLite, and vector providers; semantic + consolidating memory |
| **Knowledge** | Fact injection from dicts, SQLite, or vector retrieval |
| **Planner** | Sequential, LLM, adaptive (few-shot), reflective, and plan execution |
| **Intent** | Heuristic, LLM, embedding, and cascade engines with confidence routing |
| **Router** | Confidence-gated responder tiers — template → tool → knowledge → memory → cache → LLM |
| **Learning** | Experience store, feedback, example promotion, offline training (Trainer) |
| **Tools** | Typed function tools with JSON-schema signatures |
| **Workflows** | Sequential + graph-based with branches, loops, pause/resume |
| **Agents** | Multi-agent runtime with messaging, handoffs, roles |
| **Plugins** | Auto-discovery via entry points or package scanning |
| **Events** | Pub/sub bus with 32 canonical events, tracing, and exporters |
| **Security** | Kill switch, content guardrails, audit logging |

## What problem does it solve?

Building an AI assistant means solving a lot of problems that have nothing to
do with your idea:

- picking a model provider (and being able to swap it)
- remembering conversations
- injecting your domain knowledge
- planning multi-step tasks
- calling tools safely
- orchestrating multiple agents
- handling failures, rate limits, and security

Xyberos solves these once, behind stable **contracts**, so you only write the
parts that are specific to *your* assistant.

## Xyberos vs. building from scratch

| Concern | From scratch | With Xyberos |
|---|---|---|
| Model provider | wire OpenAI, then again for Ollama... | swap one `llm=` argument |
| Conversation memory | design a store | `SqliteMemory("chat.db")` |
| Domain facts | prompt-hacking | `knowledge.add(...)` + retrieval |
| Tool calling | build schema + dispatch | `FunctionTool` derives it |
| Multi-step tasks | hand-roll loops | `Workflow` / `Planner` |
| Multiple agents | message-passing infra | `MultiAgentRuntime` |
| Security | remember to check | `Security` gates every request |

## Xyberos vs. agent frameworks

Most agent frameworks give you *an agent loop*. Xyberos gives you the
**platform underneath** — Kernel, Runtime, Context, contracts, plugins — and
lets you compose assistants, agents, and workflows on top. Components are
interchangeable; the contracts are the stable part.

## Core philosophy

> **Build the assistant you want without rebuilding the infrastructure underneath it.**

- **Flexible** — every subsystem is a plugin surface.
- **Extendible** — implement a contract, register it, done.
- **Swappable** — default implementations are a convenience, not a prison.
- **Composable** — combine memory + knowledge + tools + agents freely.
- **Continuously developing** — new subsystems arrive without breaking the
  stable contracts.

## Core vs. plugins

```text
Xyberos Core
├── Kernel          (config, logging, registry, lifecycle)
├── Runtime         (request execution, sync + async)
├── Context         (the state object passed through the pipeline)
├── Brain           (automated cognitive pipeline)
├── Contracts       (the stable extension interfaces)
└── Security        (kill switch, guardrails, audit)

Plugins & providers (swappable)
├── LLM             (Echo, Callable, Ollama, OpenAI, Anthropic, Gemini, ...)
├── Memory          (in-memory, SQLite, vector, consolidating, stratified)
├── Knowledge       (in-memory, SQLite, vector, ingesting)
├── Planner         (sequential, LLM, adaptive, reflective)
├── Intent          (heuristic, LLM, embedding, cascade)
├── Router          (template → tool → knowledge → memory → cache → LLM)
├── Tools           (typed function tools)
├── Workflows       (sequential, graph, checkpoints)
├── Agents          (roles, messaging, handoffs)
├── Events          (pub/sub observability)
└── Learning        (experience, promotion, trainer)
```

## What can you build?

- **AI-Powered IDE or Dev Tool** — multi-agent code review with streaming,
  guardrails blocking destructive ops, tools for `read_file` / `run_test` /
  `git_diff`, and a workflow node with human approval per step.
- **Robotics Controller** — Perception → Plan → Act loop, hierarchical agents
  (supervisor → navigation → manipulation), and a **literal emergency stop** via
  `Security.engage_kill_switch()` that halts all motor commands.
- **Customer Support Platform** — intent routing via typed tools, escalation
  through agent handoffs, refund workflows that pause for human approval,
  persistent SQLite conversation history, and a full audit trail.
- **Autonomous Research Assistant** — `LLMPlanner` decomposes "summarize the
  state of X" into search → read → synthesize → cite, streaming token-by-token.
- **Personal AI assistants** — Jarvis-style assistants with a name, personality,
  knowledge, memory, planning, skills, and workflows.
- **Local AI applications** — fully offline with Ollama (chat + embeddings, no
  cloud, no SDK).

> **Anything else** — every subsystem is a plugin surface. The platform is
> done; the rest is building blocks.

## Try it yourself

```python
from xyberos import create_app

app = create_app()                     # zero config, zero API keys
print(app.chat("Hello, world!"))       # -> Hello, world!
```

## The mental model

> **Assistant = Personality + Knowledge + Memory + Reasoning + Skills + Workflows**

Keep this in mind as you go through the tutorial — each chapter adds one of
these capabilities to your assistant.

## Next Step

[**2. Getting Started**](02-getting-started.md) — install Xyberos and run
your first application.

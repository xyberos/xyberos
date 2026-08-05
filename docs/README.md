# Documentation Index

This directory contains the project documentation beyond the package code itself.

## Start Here

- [Repository README](../../README.md)
- [Using Extension Surfaces](extensions.md)
- [Configuring Services](configuring-services.md) — explicit, factory, and plugin approaches
- [Tutorial](tutorial.md)
- [API Reference](api-reference.md)
- [Lifecycle and Service Behavior](lifecycle.md)
- [Architecture RFCs](RFCs/)

## Examples

- [Hello World to Full Stack](../examples/hello_world_to_full_stack/README.md) - one runnable script that grows from a one-liner into a full-stack app
- [Chat App](../examples/chat_app/README.md) - a real FastAPI + SQLAlchemy backend with pluggable auto-discovery
- [`examples/minimal_chat.py`](../examples/minimal_chat.py) - the shortest possible chat
- [`examples/extended_app.py`](../examples/extended_app.py) - a broad walkthrough of the app API

## RFC Set

The RFCs describe the current architecture and the reasoning behind the core layers:

- `RFC-0001-architecture.md` - overall system architecture
- `RFC-0002-kernel.md` - kernel composition and platform services
- `RFC-0003-runtime.md` - runtime execution
- `RFC-0004-brain.md` - brain orchestration
- `RFC-0005-context.md` - cognitive context model
- `RFC-0006-llm-provider.md` - language model provider interface
- `RFC-Roadmap.md` - roadmap, current status, and future enhancement backlog

## Public API Map

Import the main facade from the package root:

```python
from xyberos import Xyberos, achat, chat, create_app
```

Useful supporting modules:

- `xyberos.kernel` - configuration, logging, registry, lifecycle, event bus
- `xyberos.runtime` - cognitive context and runtime execution (sync + async)
- `xyberos.brain` - automated cognitive pipeline
- `xyberos.agents` - multi-agent runtime, roles, messaging, and handoffs
- `xyberos.workflows` - sequential workflows, state graphs, and checkpoints
- `xyberos.plugins` - plugin loading and auto-discovery (entry points + convention scan)
- `xyberos.llm` - model providers, streaming/async, structured output, and adapters
- `xyberos.memory` / `xyberos.knowledge` - in-memory and SQLite providers
- `xyberos.planner` - fixed and LLM-driven planners
- `xyberos.tools` - registries, runners, and typed function tools
- `xyberos.events` - event bus, tracing, and exporters
- `xyberos.utils` - resilience helpers (retry, rate limiting, timeouts)
- `xyberos.contracts` - extension contracts
- `xyberos.exceptions` - typed domain exceptions

## Reading Order

If you are new to the project, read these in order:

1. `README.md`
2. `extensions.md`
3. `tutorial.md`
4. `api-reference.md`
5. `lifecycle.md`
6. `RFC-0001-architecture.md`
7. `RFC-0002-kernel.md`
8. `RFC-0003-runtime.md`
9. `RFC-0004-brain.md`
10. `RFC-0005-context.md`
11. `RFC-0006-llm-provider.md`

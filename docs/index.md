# Documentation

This is the documentation index for **Xyberos**. For the project overview, install
instructions, and quick start, see the [repository README](https://github.com/xyberos/xyberos/blob/main/README.md).

## Start Here

- [Using Extension Surfaces](extensions.md)
- [Configuring Services](configuring-services.md) — explicit, factory, and plugin approaches
- [Tutorial](tutorial.md)
- [Training Tutorial](training-tutorial.md) — capture, feedback, learn, evaluate, and distill
- [API Reference](api-reference.md)
- [Lifecycle and Service Behavior](lifecycle.md)
- [Architecture RFCs](RFCs/RFC-Roadmap.md)

## Examples

- [Hello World to Full Stack](https://github.com/xyberos/xyberos/blob/main/examples/hello_world_to_full_stack/README.md) - one runnable script that grows from a one-liner into a full-stack app
- [Chat App](https://github.com/xyberos/xyberos/blob/main/examples/chat_app/README.md) - a real FastAPI + SQLAlchemy backend with pluggable auto-discovery
- [`examples/minimal_chat.py`](https://github.com/xyberos/xyberos/blob/main/examples/minimal_chat.py) - the shortest possible chat
- [`examples/extended_app.py`](https://github.com/xyberos/xyberos/blob/main/examples/extended_app.py) - a broad walkthrough of the app API
- [`examples/support_assistant/`](https://github.com/xyberos/xyberos/blob/main/examples/support_assistant/README.md) - every subsystem in one service

## RFC Set

The RFCs describe the current architecture and the reasoning behind the core layers:

- `RFC-0001-architecture.md` - overall system architecture
- `RFC-0002-kernel.md` - kernel composition and platform services
- `RFC-0003-runtime.md` - runtime execution
- `RFC-0004-brain.md` - brain orchestration
- `RFC-0005-context.md` - cognitive context model
- `RFC-0006-llm-provider.md` - language model provider interface
- `RFC-0007-memory.md` - memory contract and providers
- `RFC-0008-knowledge.md` - knowledge contract and providers
- `RFC-0009-planner.md` - planner contract and providers
- `RFC-0010-tools.md` - tool contract and typed function tools
- `RFC-0011-workflows.md` - workflow contract and graph engine
- `RFC-0012-agents.md` - multi-agent contract and runtime
- `RFC-0013-plugins.md` - plugin contract and discovery
- `RFC-0014-events.md` - event bus and observability
- `RFC-0015-security.md` - kill switch, guardrails, and audit log
- `RFC-Roadmap.md` - roadmap, current status, and future enhancement backlog
- `RFC-0016-trainable-cognitive-engines.md` - trainable engines and the learning layer
- `RFC-0017-llm-fallback-router.md` - LLM-as-fallback tiered routing
- `RFC-0018-smarter-learning.md` - smarter learning: outcomes, eval, self-expanding knowledge

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
- `xyberos.llm` - model providers (incl. local `OllamaLLM` + `OllamaEmbeddingLLM`), streaming/async, structured output, and adapters
- `xyberos.memory` / `xyberos.knowledge` - in-memory, SQLite, vector, and consolidating providers
- `xyberos.planner` - fixed, LLM, adaptive, reflective planners, and plan execution
- `xyberos.intent` - heuristic, LLM, embedding, and cascade intent engines
- `xyberos.router` - hybrid responder chain (templates, tools, knowledge, memory, cache, LLM, degrade)
- `xyberos.vector` - vector store contract and providers (cosine, chroma, pgvector)
- `xyberos.experience` / `xyberos.learning` - episode store, promote/demote, example promotion
- `xyberos.trainer` - offline training/distillation and artifact registry
- `xyberos.tools` - registries, runners, and typed function tools
- `xyberos.events` - event bus, tracing, and exporters
- `xyberos.utils` - resilience helpers (retry, rate limiting, timeouts) + evaluation metrics
- `xyberos.contracts` - extension contracts
- `xyberos.exceptions` - typed domain exceptions

## Reading Order

If you are new to the project, read these in order:

1. `README.md` (the repository README)
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

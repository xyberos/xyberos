# Xyberos Documentation

Welcome! **Xyberos** is a cognitive platform for building AI systems — agents,
tools, workflows, multi-agent collaboration, streaming, memory, knowledge,
planning, plugins, observability, and security. The core is **zero-dependency**.

> **New here?** Follow the tutorial like a class — each chapter adds one
> capability to your assistant. Copy → Run → Modify → Build something.

## 📚 Learn — Build Your Own AI Assistant

The W3Schools-style tutorial. Each chapter builds on the last.

| # | Chapter | You learn to… |
|---|---|---|
| 1 | [What is Xyberos?](learn/01-what-is-xyberos.md) | the platform, its philosophy, what you can build |
| 2 | [Getting Started](learn/02-getting-started.md) | install, first app, config, logging |
| 3 | [Hello Assistant](learn/03-hello-assistant.md) | create, run, stream, async, handle errors |
| 4 | [Give It a Name & Personality](learn/04-name-and-personality.md) | identity, instructions, personality |
| 5 | [Give It Knowledge](learn/05-knowledge.md) | facts, documents, embeddings, retrieval |
| 6 | [Give It Memory](learn/06-memory.md) | conversation memory, providers, privacy |
| 7 | [Give It Skills — Tools](learn/07-tools.md) | function tools, registries, errors |
| 8 | [Give It Plans & Workflows](learn/08-workflows.md) | sequential & graph workflows, planners |
| 9 | [Skills & Plugins](learn/09-plugins.md) | packages, auto-discovery, swapping |
| 10 | [Give It a Brain](learn/10-brain.md) | the cognitive pipeline, intent, router |
| 11 | [Context](learn/11-context.md) | the state object through the pipeline |
| 12 | [Multi-Agent Systems](learn/12-agents.md) | roles, messaging, handoffs |
| 13 | [Configuration](learn/13-configuration.md) | defaults, precedence, secrets |
| 14 | [Observability & Debugging](learn/14-observability.md) | logging, events, traces, troubleshooting |
| 15 | [Security](learn/15-security.md) | kill switch, guardrails, audit log |
| 16 | [Testing](learn/16-testing.md) | mocking, contract tests, coverage |
| 17 | [Build Your First Jarvis](learn/17-build-your-jarvis.md) | combine everything into one app |
| 18 | [Configuring Services](learn/18-configuring-services.md) | explicit, factory, and plugin wiring |
| 19 | [Extension Surfaces](learn/19-extension-surfaces.md) | contracts, plugins, and customization |
| 20 | [Lifecycle & Services](learn/20-lifecycle.md) | start/stop and service behavior |
| 21 | [Knowledge Ingestion](learn/21-knowledge-ingestion.md) | index documents, files, and URLs |
| 22 | [Training Xyberos](learn/22-training-tutorial.md) | capture, feedback, learn, evaluate, and distill |
| 23 | [Build a Customer Support Assistant](learn/23-customer-support-tutorial.md) | a complete production-shaped app |

## 🛠 How-To & Recipes

- [How-To / Recipes](howto.md) — change the LLM, add memory, add knowledge,
  create tools/plugins/workflows, go offline, and more.

## 📖 API Reference

- [API Reference](api-reference.md) — every primary public object, what it
  owns, and when to use it.

## ❓ FAQ

- [Frequently Asked Questions](faq.md) — beginner, architecture, and production
  questions.

## 🧠 Architecture

- [Roadmap & Vision](RFCs/RFC-Roadmap.md) — current status and enhancement
  backlog.
- [Architecture RFCs](RFCs/RFC-0001-architecture.md) — the reasoning behind
  every layer (RFC-0001 through RFC-0018).

## 🤝 Contributing

- [Contributing Guide](contributing.md) — development environment, tests,
  coding standards, RFC process, and pull requests.

---

## Quick start

```python
from xyberos import create_app

app = create_app()
print(app.chat("Hello, world!"))   # -> Hello, world!
```

## Reading order

New to the project? Start here:

1. [Learn 1 — What is Xyberos?](learn/01-what-is-xyberos.md)
2. [Learn 2 — Getting Started](learn/02-getting-started.md)
3. [Learn 3 — Hello Assistant](learn/03-hello-assistant.md)
4. The rest of the [Learn series](learn/01-what-is-xyberos.md)
5. [API Reference](api-reference.md)
6. [RFC-0001 Architecture](RFCs/RFC-0001-architecture.md), then the remaining RFCs

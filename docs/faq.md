# FAQ

[**← Back to the tutorial**](learn/01-what-is-xyberos.md)

## Beginner

### What is Xyberos?

Xyberos is a cognitive platform for building AI systems — a layered platform
with a zero-dependency core (Kernel, Runtime, Brain, Contracts) and
replaceable subsystems (LLM, memory, knowledge, planner, intent, router,
tools, workflows, agents, plugins, events, security, learning).

### Is Xyberos an LLM?

No. Xyberos is a **platform** that *uses* LLMs. It ships with no-op and local
adapters, and you plug in the model of your choice (Ollama, OpenAI, Anthropic,
Gemini, or any OpenAI-compatible endpoint).

### Does Xyberos require OpenAI?

No. The default `EchoLLM` needs nothing; `OllamaLLM` runs fully locally; the
official SDK adapters are optional and lazy-imported.

### Can I run local models?

Yes — `OllamaLLM` and `OllamaEmbeddingLLM` talk to a local Ollama server over
plain stdlib HTTP. No SDK, no cloud, no API key.

### Do I need a GPU?

No. You can run with CPU-only local models, or use cloud providers.

### Can I build a chatbot?

Yes — that's the "Hello Assistant" starting point
([Learn 3](learn/03-hello-assistant.md)). From there you add knowledge,
memory, tools, workflows, and agents.

### Can I build a voice assistant?

Not out of the box — the current version has no built-in STT/TTS subsystem.
Voice input/output is an integration you'd build (or contribute) on top of the
plugin surface.

## Architecture

### Why are components replaceable?

Because every subsystem sits behind a **contract**. Swapping the backend
(in-memory → SQLite → vector) never changes your callers — you pass a different
provider to `create_app()` and everything else keeps working.

### Why use contracts?

Contracts make the system **extendible** and **testable**. You can implement a
contract, register it, and write contract tests that run against every
implementation. RFC-0001 explains the reasoning in depth.

### Why separate knowledge and memory?

They solve different problems:

```text
Knowledge = information the assistant can reference (facts, docs)
Memory    = information retained from interactions (conversation history)
```

### What is the cognitive engine?

The **Brain** — the orchestrator that runs the automated pipeline (workflow →
memory → knowledge → intent → plan → router/tools → LLM → memory) for each
request. See [Learn 10](learn/10-brain.md).

### Why are plugins outside the core?

The core is minimal and zero-dependency. Everything optional lives behind
contracts and is loaded by the plugin system — so the core stays stable while
the ecosystem grows.

### Can I create my own implementation?

Yes. Any subsystem is a contract — implement it and pass it in. See
[Configuring Services](learn/18-configuring-services.md) and
[Extension Surfaces](learn/19-extension-surfaces.md).

## Production

### Is Xyberos production ready?

The package is classified `Development Status :: 5 - Production/Stable`, with
a substantial test suite and built-in hardening (retries, rate limits,
timeouts, checkpoints, kill switch, audit log). As with any platform, review
the [Security](learn/15-security.md) and
[Testing](learn/16-testing.md) chapters before deploying.

### How do I deploy it?

It's a Python package — deploy like any Python service. The async API
(`app.achat`) works inside FastAPI, and the repo ships a production-shaped
[`examples/support_assistant/`](https://github.com/xyberos/xyberos/blob/master/examples/support_assistant/README.md)
FastAPI example.

### How do I secure tools?

Use guardrails to block harmful prompts, the kill switch for emergencies, and
the audit log for accountability. See [Learn 15 — Security](learn/15-security.md).

### How do I monitor it?

Subscribe to the event bus (`app.events`) and record events with
`EventRecorder` + exporters. See
[Learn 14 — Observability](learn/14-observability.md).

### How do I test it?

Fake the LLM with `CallableLLM`, test tools/workflows directly, and write
contract tests. See [Learn 16 — Testing](learn/16-testing.md).

### Can I run it completely offline?

Yes. `OllamaLLM` + `OllamaEmbeddingLLM` give you a fully-local chat *and*
semantic-embedding stack with zero cloud and zero SDKs.

---

## Still stuck?

- Browse the [How-To / recipes](howto.md)
- Read the [API Reference](api-reference.md)
- Open an issue at [github.com/xyberos/xyberos/issues](https://github.com/xyberos/xyberos/issues)

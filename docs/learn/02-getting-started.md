# 2. Getting Started

[**← Previous**](01-what-is-xyberos.md) · [**Next →**](03-hello-assistant.md)

## What You'll Learn

- Requirements (Python version, OS support)
- Installing Xyberos (pip, extras, from source)
- Creating your first project
- Your first Xyberos application
- Configuration basics
- Environment variables
- Debug mode and logging

---

## Requirements

- **Python 3.10 or newer** — check with `python --version`.
- Any OS (Windows, macOS, Linux).
- No GPU required. No cloud account required.
- The core is **zero-dependency** — the standard library is all it needs.

## Installation

```bash
pip install xyberos
```

That's it. Zero runtime dependencies — the standard library is all it needs.

```bash
pip install xyberos[dev]     # pytest + coverage for development
pip install xyberos[vectors] # optional ChromaDB / pgvector adapters
pip install xyberos[train]   # scikit-learn + joblib for offline training
pip install xyberos[embeddings] # sentence-transformers for local embeddings
```

Or install from source:

```bash
git clone https://github.com/xyberos/xyberos.git
cd xyberos
pip install -e .
```

## Create your first project

```text
my_assistant/
├── assistant.py
├── config.py
└── plugins/            # optional
```

## Your first Xyberos application

Put this in `assistant.py`:

```python
from xyberos import create_app

app = create_app()
print(app.chat("Hello, world!"))   # -> Hello, world!
```

Run it:

```bash
python assistant.py
```

What just happened?

- `create_app()` built a **fully-wired AI application** — model, memory,
  knowledge, planner, tools, security, and more. You didn't wire any of it by
  hand.
- `app.chat("...")` sent your text through the whole **cognitive pipeline**
  and returned the reply as a string.
- With no model configured, Xyberos uses `EchoLLM`, which simply echoes your
  prompt back. That's the "Hello, world!" of AI apps — **zero setup, zero
  cost, zero API keys.**

## Configuration

Pass configuration at construction time:

```python
from xyberos import create_app

app = create_app(config={
    "brain.inject_plan": True,   # feed the plan to the model
    "brain.max_attempts": 3,     # retry transient failures
    "brain.timeout": 30,         # seconds per LLM call
})
```

Read and write config at runtime through `app.config`:

```python
app.config.get("brain.intent", False)   # -> False
app.config.set("brain.intent", True)
```

You can also pass providers directly — the most common pattern:

```python
from xyberos import create_app
from xyberos.llm import OllamaLLM
from xyberos.memory import SqliteMemory

app = create_app(
    llm=OllamaLLM(model="llama3.2"),
    memory=SqliteMemory("chat.db"),
)
```

> See [Configuring Services](18-configuring-services.md) for the three ways to
> wire services (explicit, factory, plugin).

## Environment variables

Xyberos does not force a specific environment-variable scheme on you. You
decide how to load secrets — for example, with `os.environ`:

```python
import os
from xyberos import create_app
from xyberos.llm import OpenAILLM

app = create_app(llm=OpenAILLM(api_key=os.environ["OPENAI_API_KEY"]))
```

The provider adapters accept `api_key=` directly, so they compose cleanly with
any environment/secret management you already use.

## Debug mode

There is no hidden global debug flag — you inspect what's happening through
the objects Xyberos gives you:

```python
from xyberos import create_app

app = create_app()

ctx = app.run("Hello, world!")       # run() returns the full CognitiveContext
print(ctx.prompt)                    # the input
print(ctx.response)                  # the model's reply
print(ctx.succeeded)                 # True when there was no error
print(ctx.metadata)                  # open-ended dict you can attach anything to
```

Use `doctor()` for a quick environment snapshot:

```python
from xyberos import doctor

report = doctor()
print(report.as_dict())
```

## Logging

Log through `app.logger`:

```python
from xyberos import create_app

app = create_app()
app.logger.info("starting up")
```

Every layer publishes structured events to `app.events` — subscribe to watch
the pipeline trace:

```python
from xyberos.events import RESPONSE_PRODUCED

app.events.subscribe(RESPONSE_PRODUCED, lambda e: print(e.data))
```

> Full observability coverage is in [14. Observability & Debugging](14-observability.md).

## Default behavior

With no arguments at all, `create_app()` gives you:

- `EchoLLM` — echoes your prompt (no API key needed)
- in-memory memory, knowledge, planner, tools, workflow, intent, experience
- a fully automated brain pipeline
- a default `RuntimeAgent` in a `MultiAgentRuntime`

## Common mistakes

- **Expecting a real model by default** — the default is `EchoLLM`; pass
  `llm=` to use a real model.
- **Forgetting that semantic matching needs a real embedder** — the default
  `HashEmbedder` only matches near-identical text.
- **Installing SDKs you don't need** — `OllamaLLM` uses stdlib HTTP; only the
  official OpenAI/Anthropic/Gemini adapters require their SDKs (lazy-imported).

## Next Step

[**3. Hello Assistant**](03-hello-assistant.md) — create an assistant, send
messages, stream responses, and handle errors.

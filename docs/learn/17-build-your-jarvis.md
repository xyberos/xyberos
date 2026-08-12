# 17. Build Your First Jarvis

[**← Previous**](16-testing.md) · [**Next →**](18-configuring-services.md)

## What You'll Learn

- Combine everything into one assistant
- Project 1: My First AI Assistant (conversation + personality + LLM + memory)
- Project 2: Knowledge Assistant (+ knowledge)
- Project 3: Tool-Using Assistant (+ tools)
- Project 4: Your Jarvis (planning + workflows + agents + plugins)
- Next steps & the full project tutorial

---

Each chapter gave your assistant another capability. Now put them together.
You can copy each project, run it, modify it, and build on it.

## Project 1 — My First AI Assistant

```text
my_assistant/
├── assistant.py
├── config.py
└── requirements.txt
```

Capabilities: conversation, personality, LLM, memory.

```python
from xyberos import create_app
from xyberos.llm import OllamaLLM
from xyberos.memory import SqliteMemory

app = create_app(
    llm=OllamaLLM(model="llama3.2"),   # needs `ollama pull llama3.2`
    memory=SqliteMemory("chat.db"),
)

while True:
    message = input("> ")
    if message.lower() in ("quit", "exit"):
        break
    print(app.chat(message))
```

## Project 2 — Knowledge Assistant

Add knowledge: documents, embeddings, retrieval.

```python
from xyberos import create_app
from xyberos.knowledge import SqliteKnowledge
from xyberos.llm import OllamaLLM

knowledge = SqliteKnowledge("facts.db")
knowledge.add("hours", "Support is available 9am-6pm Mon-Fri.")
knowledge.add("refund", "Refunds are processed within 5-7 business days.")

app = create_app(
    llm=OllamaLLM(model="llama3.2"),
    knowledge=knowledge,
)
print(app.chat("what are your hours?"))
```

## Project 3 — Tool-Using Assistant

Add tools: calculator, lookups, APIs.

```python
from xyberos import create_app
from xyberos.llm import OllamaLLM
from xyberos.tools import FunctionTool, ToolRegistry

def add(a: float, b: float) -> str:
    """Add two numbers."""
    return str(a + b)

registry = ToolRegistry([
    FunctionTool("add", add, description="Add two numbers"),
])

app = create_app(llm=OllamaLLM(model="llama3.2"), tools=registry)
print(app.chat("what is 2 + 3?"))
```

## Project 4 — Your Jarvis

Combine everything:

```text
                 ┌── Personality
                 ├── Knowledge
                 ├── Memory
                 ├── Planning
                 ├── Workflows
                 ├── Skills / Tools
                 ├── Context
                 └── Plugins
                        │
                        ▼
                 ┌───────────────┐
                 │    JARVIS     │
                 │   (Your AI)   │
                 └───────────────┘
```

The complete runnable support-assistant — every subsystem in one service — is
in the repo:

- [`examples/support_assistant/`](https://github.com/xyberos/xyberos/blob/master/examples/support_assistant/README.md) — FastAPI server, order lookup,
  refund approval, escalation, streaming, events, and hardening.
- [`examples/hello_world_to_full_stack/`](https://github.com/xyberos/xyberos/blob/master/examples/hello_world_to_full_stack/README.md) — one script that grows
  from a one-liner into a full-stack app.
- [`examples/chat_app/`](https://github.com/xyberos/xyberos/blob/master/examples/chat_app/README.md) — a real FastAPI + SQLAlchemy backend.

## The full picture

By now your assistant has every capability. Here's what `app.chat("...")` does
with them, in order:

1. **Workflow** — any pre-steps run; a step that sets the response short-circuits.
2. **Memory** — past turns are added as conversation history.
3. **Knowledge** — matching facts are injected into the prompt.
4. **Intent / Plan** — the request is classified and a plan is computed.
5. **Router / Tools** — a confident cheap tier (or a tool) may answer first.
6. **LLM** — only the novel tail reaches the model; its answer is cached.
7. **Memory** — the completed turn is stored for next time.

## Next steps

- **Follow the full project tutorial** — [Build a Customer Support Assistant](23-customer-support-tutorial.md)
  walks every subsystem in a copy-pasteable, production-shaped app.
- **Make it learn** — see the [Training Tutorial](22-training-tutorial.md).
- **Ingest documents** — see the [Knowledge Ingestion tutorial](21-knowledge-ingestion.md).
- **Recipes & how-to** — see [How-To](../howto.md).
- **API reference** — see the [API Reference](../api-reference.md).

> **Under the hood:** curious how a layer works? Each RFC in
> [docs/RFCs/](../RFCs/RFC-Roadmap.md) explains the reasoning behind a
> subsystem. The tutorial is the *how*; the RFCs are the *why*.

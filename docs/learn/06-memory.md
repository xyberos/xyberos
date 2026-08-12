# 6. Give It Memory

[**← Previous**](05-knowledge.md) · [**Next →**](07-tools.md)

## What You'll Learn

- What memory is
- Conversation memory
- Memory providers (in-memory, SQLite, vector, consolidating, stratified)
- Retrieval and storage
- Clearing memory
- Custom memory provider
- Privacy considerations

---

## What is memory?

**Memory = information retained from interactions.** While knowledge is the
facts you *give* the assistant, memory is what it *retains* — the conversation
history, past contexts, and learned patterns.

## Conversation memory

Memory is wired in by default. The brain **retrieves past turns** before
generating and **stores each completed turn** afterward:

```python
from xyberos import create_app

app = create_app()
app.chat("my order is A-100")
print(app.chat("what did I just ask about?"))   # sees the history
```

Inspect what it remembers:

```python
for entry in app.memory.retrieve(None):
    print(entry.prompt, "->", entry.response)
```

## Memory providers

| Provider | What it does | Use it when |
|---|---|---|
| `InMemoryMemory` | stores contexts in-process | quick tests |
| `SqliteMemory` | persists rows to a file | durable conversation history |
| `VectorMemory` | embedding-based retrieval | semantic recall, "learn by accumulation" |
| `ConsolidatingMemory` | LLM summarization | compressing long histories |
| `StratifiedMemory` | durable facts + episodic history | separating what to remember from what to recall |

```python
from xyberos import create_app
from xyberos.memory import SqliteMemory

app = create_app(memory=SqliteMemory("chat.db"))   # survives restarts
app.chat("hello")
print(app.chat("what did I just say?"))
```

## Vector memory

`VectorMemory` replaces substring matching with **embedding-based retrieval**
(and blends in recency via `alpha`):

```python
from xyberos.memory import VectorMemory
from xyberos.vector import SqliteVectorStore

memory = VectorMemory(SqliteVectorStore("learning.db"), embedder=embedder, alpha=0.7)
```

## Clear memory

```python
app.memory.clear()
```

## Custom memory provider

Implement the `MemoryProvider` contract (`store(context)` and
`retrieve(context)` are the core methods):

```python
from xyberos.contracts.memory import MemoryProvider

class MyMemory(MemoryProvider):
    def store(self, context):
        ...

    def retrieve(self, context):
        return []

app = create_app(memory=MyMemory())
```

## Privacy considerations

- **What gets stored** — completed turns (prompt + response) by default; what
  else is stored depends on the provider.
- **Where it gets stored** — in-memory (process only), a SQLite file, or a
  vector store. SQLite files are written next to your script (`chat.db`,
  `learning.db`).
- **How to disable it** — pass an empty provider, or simply don't configure a
  persistent one; the default in-memory memory dies with the process.
- **How to delete it** — `memory.clear()` wipes stored contexts.

## Default behavior

- `create_app()` wires an **in-memory** memory provider by default.
- The brain retrieves memory before generation and stores the turn afterward
  — automatic, no extra config.
- Memory is *not* persistent across restarts unless you use
  `SqliteMemory` / a vector store.

## Common mistakes

- **Expecting persistence from the default** — switch to `SqliteMemory` or a
  `VectorStore` for durability.
- **Forgetting the embedder for semantic memory** — `VectorMemory` needs an
  `embed(text)` object; the default `HashEmbedder` matches only near-identical
  text.
- **Storing secrets in memory** — be mindful that conversation turns are
  stored; apply guardrails or redaction for sensitive data.

## Next Step

[**7. Give It Skills — Tools**](07-tools.md) — give your assistant hands.

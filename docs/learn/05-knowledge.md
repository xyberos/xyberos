# 5. Give It Knowledge

[**← Previous**](04-name-and-personality.md) · [**Next →**](06-memory.md)

## What You'll Learn

- What knowledge is
- Knowledge vs. memory (the crucial difference)
- Adding knowledge facts
- Knowledge providers (in-memory, SQLite, vector)
- Documents & ingestion
- Embeddings and retrieval
- Custom knowledge backend

---

## What is knowledge?

**Knowledge = information the assistant can reference.** It's the facts,
policies, and domain data that the model draws from when answering — your
company's hours, your refund policy, your product catalog.

> **Knowledge vs. Memory**
>
> ```text
> Knowledge = information the assistant can reference (facts, docs)
> Memory    = information retained from interactions (conversation history)
> ```

## Add knowledge

The quickest way is a fact map. The brain queries it and injects matching
facts into the prompt:

```python
from xyberos import create_app
from xyberos.knowledge import InMemoryKnowledge
from xyberos.llm import CallableLLM

app = create_app(
    llm=CallableLLM(lambda prompt: prompt),   # echo so you can SEE the injection
    knowledge=InMemoryKnowledge({
        "hours": "Support is available 9am-6pm Mon-Fri.",
        "refund": "Refunds are processed within 5-7 business days.",
    }),
)
print(app.chat("what are your hours?"))
```

You'll see the model's input already contains your fact:

```text
what are your hours?

Relevant knowledge:
{'hours': 'Support is available 9am-6pm Mon-Fri.'}
```

That's the whole trick — the brain retrieves matching facts and **enriches the
prompt** before calling the model.

## Knowledge providers

| Provider | Persistence | Use it when |
|---|---|---|
| `InMemoryKnowledge` | process only | quick tests, prototyping |
| `SqliteKnowledge` | SQLite file | durable curated facts |
| `VectorKnowledge` | a `VectorStore` | semantic retrieval over many facts |
| `IngestingKnowledge` | a `VectorStore` | indexing documents/files/URLs |

```python
from xyberos.knowledge import SqliteKnowledge

knowledge = SqliteKnowledge("facts.db")        # survives restarts
knowledge.add("hours", "Support is available 9am-6pm Mon-Fri.")
```

`InMemoryKnowledge` and `SqliteKnowledge` store **keyword-keyed facts**; a fact
is injected when a key/term matches the prompt. `VectorKnowledge` and
`IngestingKnowledge` use **embedding similarity**, so a question phrased
differently from the source text still retrieves the right facts.

## Query it directly

```python
from xyberos.runtime.context import CognitiveContext

ctx = CognitiveContext("tell me about refunds")
print(knowledge.query(ctx))                  # top facts formatted for injection

for hit in knowledge.query_scored(ctx, top_k=3):   # raw scores for gating
    print(f"{hit.score:.2f}  {hit.payload['value']}")
```

## Documents & ingestion

Ingest raw text into a semantic knowledge base with `IngestingKnowledge`.
You need a **vector store** and an **embedder**:

```python
from xyberos.knowledge import IngestingKnowledge
from xyberos.llm import OllamaEmbeddingLLM
from xyberos.vector import SqliteVectorStore

kb = IngestingKnowledge(
    SqliteVectorStore("kb.db"),                      # persists the index
    embedder=OllamaEmbeddingLLM(model="nomic-embed-text"),
)
kb.ingest("Support is available 9am-6pm Mon-Fri.\nRefunds take 5-7 days.")
```

```text
Document → embed → vector store → retrieve → inject
```

| Embedder | When to use |
|---|---|
| `HashEmbedder()` | dev/tests (deterministic, matches near-identical text) |
| `OllamaEmbeddingLLM` | real local semantics, no cloud, no SDK |
| `OpenAIEmbeddingLLM` | any OpenAI-compatible `/embeddings` endpoint |
| `SentenceTransformerEmbedder` | `pip install xyberos[embeddings]` |

> Full document/file/URL ingestion (PDF, markdown, web pages) is covered in the
> [Knowledge Ingestion tutorial](21-knowledge-ingestion.md).

## Custom knowledge backend

Implement the `KnowledgeProvider` contract (a `query(context)` method is the
heart of it) and swap it in:

```python
from xyberos.contracts.knowledge import KnowledgeProvider

class MyKnowledge(KnowledgeProvider):
    def query(self, context):
        # return facts relevant to context.prompt
        return {"hours": "9am-6pm"}

app = create_app(knowledge=MyKnowledge())
```

## Configuration

Wire it into the app explicitly:

```python
app = create_app(
    llm=OllamaLLM(model="qwen2.5:1.5b"),
    knowledge=SqliteKnowledge("facts.db"),
)
```

## Default behavior

- With no `knowledge=`, Xyberos uses an **empty** `InMemoryKnowledge` — no
  facts are injected.
- The brain queries the configured knowledge provider automatically on every
  request and injects matching facts as `Relevant knowledge:`.

## Common mistakes

- **Using `HashEmbedder` for real matching** — it only matches near-identical
  text. Use a semantic embedder for paraphrase matching.
- **Forgetting the embedder** — `IngestingKnowledge` raises `ProviderError` if
  no `embedder=` is provided.
- **Writing SQLite files next to your script** — `facts.db`, `kb.db`, etc. are
  created in the working directory; keep them out of git or pass explicit paths.

## Next Step

[**6. Give It Memory**](06-memory.md) — help your assistant remember the
conversation.

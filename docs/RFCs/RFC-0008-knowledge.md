RFC-0008 — Knowledge

Title: Knowledge Extension Contract

Status: Accepted

Summary

Defines the Knowledge subsystem — a pluggable fact-retrieval layer that grounds
LLM responses in curated, domain-specific information.

Motivation

LLMs hallucinate or lack domain-specific facts. A knowledge provider injects
relevant facts (FAQs, policies, documentation) into the prompt before the model
sees it, improving accuracy without fine-tuning.

Contract

```python
class Knowledge(ABC):

    @abstractmethod
    def query(self, context: object) -> Any:
        """Return knowledge relevant to the supplied execution context."""
```

The return shape is provider-defined — it may be a string, a list of
documents, or structured records. The provider decides what "relevant" means
(keyword match, embedding similarity, graph traversal, etc.).

Pipeline Integration

The Brain calls ``query`` after memory retrieval but before the planner:

```text
Memory (retrieve) → Knowledge (query) → Planner → Tools → LLM
```

The returned facts are injected into the model prompt so the LLM sees them
alongside the user's request.

Providers

| Provider | Backend | Lookup |
|---|---|---|
| ``InMemoryKnowledge`` | Python dict | Exact key match |
| ``SqliteKnowledge`` | SQLite file | LIKE-based search |

Populate facts via ``knowledge.add(key, value)``. Swap via:

```python
app = create_app(knowledge=SqliteKnowledge("facts.db"))
knowledge.add("hours", "Support is available 9am-6pm Mon-Fri.")
```

Future Providers

- Vector store — semantic similarity over embeddings
- Graph store — relationship-aware fact retrieval
- Remote API — live documentation or knowledge-base lookups

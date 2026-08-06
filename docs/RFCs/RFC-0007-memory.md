RFC-0007 — Memory

Title: Memory Extension Contract

Status: Accepted

Summary

Defines the Memory subsystem — a pluggable persistence layer for execution
contexts that enables conversation history, long-term recall, and
provider-swappable storage.

Motivation

The Brain must remember past interactions to provide coherent multi-turn
conversations. Rather than hard-coding a storage backend, Xyberos defines a
contract so deployments can choose in-memory, SQLite, Redis, or vector stores
without changing the pipeline.

Contract

```python
class Memory(ABC):

    @abstractmethod
    def retrieve(self, context: object) -> Any:
        """Return memory relevant to the supplied execution context."""

    @abstractmethod
    def store(self, context: object) -> None:
        """Persist information from the supplied execution context."""
```

The contract intentionally takes ``object`` rather than ``CognitiveContext``,
keeping extension contracts independent of core layer types. A provider may
inspect the object as needed.

Pipeline Integration

The Brain calls ``retrieve`` before LLM generation and ``store`` after a
response is produced:

```text
Memory (retrieve) → Knowledge → Planner → Tools → LLM → Memory (store)
```

Providers

| Provider | Backend | Persistence |
|---|---|---|
| ``InMemoryMemory`` | Python list | Process only |
| ``SqliteMemory`` | SQLite file | Cross-restart |

Both implement the same contract. Swap via:

```python
app = create_app(memory=SqliteMemory("chat.db"))
```

Future Providers

- Redis — shared state across processes
- Vector store — semantic/embedding-based retrieval

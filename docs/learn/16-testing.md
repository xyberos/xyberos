# 16. Testing

[**← Previous**](15-security.md) · [**Next →**](17-build-your-jarvis.md)

## What You'll Learn

- Testing an assistant
- Mocking the LLM
- Testing tools
- Testing workflows
- Testing memory & knowledge
- Contract testing
- Test coverage

---

## Testing an assistant

Xyberos is built for testability — the LLM is duck-typed, so you can swap in a
deterministic fake and test the whole pipeline without a network call:

```python
from xyberos import create_app
from xyberos.llm import CallableLLM

app = create_app(llm=CallableLLM(lambda prompt: f"answer: {prompt}"))

def test_chat_returns_text():
    assert app.chat("hello") == "answer: hello"
```

## Mocking the LLM

- `EchoLLM` — echoes the prompt (default).
- `CallableLLM(func)` — wrap any plain `prompt -> text` function; the perfect
  fake for building and testing.
- `AsyncLLM(agenerate)` — fake async-only providers.
- `StructuredLLM` — test structured output parsing.

```python
def test_success_flag():
    app = create_app()
    ctx = app.run("hello")
    assert ctx.succeeded is True
```

## Testing tools

Test tools directly through the registry — validation and coercion are
deterministic:

```python
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import FunctionTool, ToolRegistry
from xyberos.exceptions import ToolArgumentError
import pytest

def search(query: str, limit: int = 10) -> str:
    return f"search({query}, limit={limit})"

def test_tool_coerces_arguments():
    tool = FunctionTool("search", search, description="Search")
    assert tool.execute(None, query="books", limit="5") == "search(books, limit=5)"

def test_tool_rejects_bad_arguments():
    tool = FunctionTool("search", search, description="Search")
    with pytest.raises(ToolArgumentError):
        tool.execute(None, query="books", limit="many")
```

## Testing workflows

Workflow steps are plain functions — test them directly, and test pause/resume
flows end to end:

```python
from xyberos.exceptions import WorkflowPaused
from xyberos.runtime.context import CognitiveContext
from xyberos.workflows import GraphWorkflow

def test_workflow_pauses_and_resumes():
    graph = GraphWorkflow("verify")
    graph.add_node("verify", verify_step)

    run = graph.execute(CognitiveContext("task"))
    assert run.status == "paused"

    run = graph.resume(run, "yes")
    assert run.context.response == "approved"
```

## Testing memory & knowledge

Use the in-memory providers for fast, isolated tests:

```python
from xyberos.memory import InMemoryMemory
from xyberos.knowledge import InMemoryKnowledge

def test_memory_round_trip():
    memory = InMemoryMemory()
    ctx = CognitiveContext("remember me")
    memory.store(ctx)
    assert len(memory.retrieve(ctx)) == 1

def test_knowledge_query():
    knowledge = InMemoryKnowledge({"hours": "9am-6pm"})
    assert "9am-6pm" in str(knowledge.query(CognitiveContext("hours")))
```

## Contract testing

Every subsystem is behind a contract (see `xyberos.contracts`). Because
providers are swappable, you can write a test against the **contract** and run
it against every implementation — in-memory, SQLite, vector, and yours:

```python
from xyberos.memory import InMemoryMemory, SqliteMemory

def exercise_memory_contract(memory):
    ctx = CognitiveContext("x")
    memory.store(ctx)
    assert memory.retrieve(ctx)

def test_memory_contract_all_implementations():
    for memory in (InMemoryMemory(), SqliteMemory(":memory:")):
        exercise_memory_contract(memory)
```

## Test coverage

Run the suite with coverage (configured in `pytest.ini`):

```bash
pip install xyberos[dev]
pytest --cov=xyberos
```

The project ships 80+ test files across every subsystem — the test suite is
the authoritative reference for current behavior.

## Common mistakes

- **Hitting real APIs in tests** — always fake the LLM with `CallableLLM`.
- **Using `HashEmbedder` where semantics matter** — tests with near-identical
  text pass, real paraphrase matching needs a semantic embedder.
- **Testing concrete providers instead of contracts** — contract tests let one
  test cover every implementation.

## Next Step

[**17. Build Your First Jarvis**](17-build-your-jarvis.md) — put it all
together.

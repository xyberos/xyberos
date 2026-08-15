# How-To / Recipes

Quick answers for developers who already know Xyberos. Each recipe is a
complete, copy-pasteable pattern. For the progressive tutorial, start at
[Learn 1 — What is Xyberos](learn/01-what-is-xyberos.md).

---

## Change the LLM

```python
from xyberos import create_app
from xyberos.llm import OllamaLLM, OpenAILLM, AnthropicLLM, GeminiLLM

app = create_app(llm=OllamaLLM(model="llama3.2"))          # local
app = create_app(llm=OpenAILLM(api_key="..."))            # OpenAI
app = create_app(llm=AnthropicLLM(api_key="..."))         # Anthropic
app = create_app(llm=GeminiLLM(api_key="..."))            # Gemini
```

## Use a local LLM (no cloud, no SDK)

```python
from xyberos import create_app, create_semantic_app
from xyberos.llm import OllamaLLM, OllamaEmbeddingLLM

# needs `ollama pull llama3.2` and `ollama pull nomic-embed-text`
app = create_app(llm=OllamaLLM(model="llama3.2"))
semantic = create_semantic_app(
    llm=OllamaLLM(model="llama3.2"),
    embedder=OllamaEmbeddingLLM(model="nomic-embed-text"),
    router="hybrid",
)
```

## Add memory

```python
from xyberos import create_app
from xyberos.memory import SqliteMemory, VectorMemory

app = create_app(memory=SqliteMemory("chat.db"))                     # durable
app = create_app(memory=VectorMemory(store, embedder=embedder))      # semantic
```

## Disable memory

```python
from xyberos import create_app
from xyberos.memory import InMemoryMemory

app = create_app(memory=InMemoryMemory())   # in-memory: nothing survives restarts
app.memory.clear()                          # wipe what's stored
```

For a provider that stores nothing, implement a no-op `MemoryProvider`
(see [Learn 6 — Memory](learn/06-memory.md)).

## Add knowledge

```python
from xyberos import create_app
from xyberos.knowledge import SqliteKnowledge, InMemoryKnowledge

knowledge = SqliteKnowledge("facts.db")
knowledge.add("hours", "Support is available 9am-6pm Mon-Fri.")
app = create_app(knowledge=knowledge)
```

## Add PDF knowledge

The core stays dependency-free — extract text with your own parser, then
ingest:

```python
from pypdf import PdfReader
from xyberos.knowledge import IngestingKnowledge
from xyberos.vector import SqliteVectorStore

text = "\n\n".join(page.extract_text() or "" for page in PdfReader("manual.pdf").pages)
kb = IngestingKnowledge(SqliteVectorStore("kb.db"), embedder=embedder)
kb.ingest(text)
```

See the [Knowledge Ingestion tutorial](learn/21-knowledge-ingestion.md) for files, URLs,
and full examples.

## Replace the vector database

Pass any `VectorStore` — the bundled `SqliteVectorStore` is dependency-free;
`ChromaVectorStore` / `PgVectorStore` need `pip install xyberos[vectors]`; and
Qdrant / FAISS / Redis ship as plugins from
[`xyberos/xyberos-plugins`](https://github.com/xyberos/xyberos-plugins):

```python
from xyberos import create_semantic_app
from xyberos.llm import OllamaEmbeddingLLM
from xyberos.vector import SqliteVectorStore, ChromaVectorStore
from xyberos_qdrant import QdrantPlugin       # pip install xyberos[vectors]

embedder = OllamaEmbeddingLLM(model="nomic-embed-text")
app = create_semantic_app(embedder=embedder, store=SqliteVectorStore("learning.db"))
app = create_semantic_app(embedder=embedder, store=ChromaVectorStore())

# hosted or local Qdrant via plugin (local in-memory mode shown)
app = create_semantic_app(embedder=embedder, store=QdrantPlugin(location=":memory:").vector_store())
```

## Add a custom tool

```python
from xyberos.tools import FunctionTool, ToolRegistry

def add(a: float, b: float) -> str:
    """Add two numbers."""
    return str(a + b)

registry = ToolRegistry([FunctionTool("add", add, description="Add two numbers")])
app = create_app(tools=registry)
```

## Add web search

Expose search as a tool — wrap any search API behind `FunctionTool`:

```python
def web_search(query: str, limit: int = 5) -> str:
    """Search the web for a query."""
    return my_search_client.search(query, limit)   # your implementation

registry = ToolRegistry([FunctionTool("web_search", web_search, description="Search the web")])
app = create_app(tools=registry)
```

## Create a custom plugin

```python
from xyberos.contracts import Plugin

class MyPlugin(Plugin):
    @property
    def name(self):
        return "my_plugin"

    def register(self, kernel):
        kernel.register("answer", 42)

app = create_app()
app.load_plugin(MyPlugin())
```

## Scaffold a plugin with the CLI (toolkit)

The plugin toolkit (`xyberos-cli`) turns plugin creation into one command —
wizard, generator, validator, and CI action. No core changes required.

```bash
pip install xyberos-cli

# interactive wizard, or fully non-interactive:
xyberos plugin create --name github --type tool \
    --description "GitHub integration" --integrate-with "GitHub REST API" \
    --auth token --non-interactive

cd github
pip install -e .
xyberos plugin validate .     # static + live-kernel check -> Result: PASS/FAIL
xyberos plugin repair .       # auto-insert missing contract stubs
```

Generated plugins declare the `xyberos.plugins` entry point, so they load
automatically:

```python
app.load_entry_points()      # discovers every installed xyberos.plugins plugin
```

For the full walkthrough see
[Learn 24 — Build & Contribute Plugins](learn/24-plugin-development.md).

## Create a custom workflow

```python
from xyberos.workflows import GraphWorkflow, WorkflowCheckpoint
from xyberos.exceptions import WorkflowPaused

def approve(context):
    if GraphWorkflow.RESUME_KEY in context.metadata:
        context.response = "approved"
        return context
    raise WorkflowPaused(prompt="Approve?")

graph = GraphWorkflow("approve")
graph.add_node("approve", approve)
```

## Run asynchronously

```python
import asyncio
from xyberos import create_app

async def main():
    app = create_app()
    print(await app.achat("Hello!"))

asyncio.run(main())
```

## Stream responses

Subscribe to token events:

```python
from xyberos.events import TOKEN_STREAMED

app.events.subscribe(TOKEN_STREAMED, lambda e: print(e.data["token"], end=""))
app.chat("Write a haiku.")
```

## Debug an assistant

```python
ctx = app.run("what are your hours?")
print(ctx.succeeded, ctx.error)        # did it fail, and why?
print(ctx.enriched_prompt)             # exactly what the model saw
print(ctx.plan, ctx.intent)            # the plan and intent
```

## Mock the LLM in tests

```python
from xyberos.llm import CallableLLM

app = create_app(llm=CallableLLM(lambda prompt: f"answer: {prompt}"))
```

## Go completely offline

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

```python
from xyberos import create_semantic_app
from xyberos.llm import OllamaLLM, OllamaEmbeddingLLM

app = create_semantic_app(
    llm=OllamaLLM(model="llama3.2"),
    embedder=OllamaEmbeddingLLM(model="nomic-embed-text"),
    router="hybrid",   # LLM-free tiers answer common requests
)
```

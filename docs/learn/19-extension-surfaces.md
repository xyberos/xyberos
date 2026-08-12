# 19. Extension Surfaces

[**← Previous**](18-configuring-services.md) · [**Next →**](20-lifecycle.md)

Xyberos is built around a small set of extension surfaces. This guide shows how to use the ones that exist in the codebase today:

- services
- tools and typed function tools
- knowledge and memory providers (in-memory + SQLite)
- planners (fixed and LLM-driven)
- workflows and state graphs
- agents and collaboration
- plugins
- events and observability
- structured outputs and resilience
- model adapters

If you were expecting a first-class `skills` subsystem, this repository does not currently define one. In practice, the closest supported equivalents are plugins, tools, workflows, planners, and agents.

## 1. Services

Services are registered in the kernel and resolved by name.

```python
from xyberos import create_app

app = create_app()
app.register("answer", 42)

assert app.resolve("answer") == 42
```

### Register a factory

Factories are dependency-injected by parameter name.

```python
from xyberos import create_app

app = create_app()

def build_message(logger, config):
    return f"{logger.name}:{config.get('logger_name')}"

app.register_factory("message", build_message)
print(app.resolve("message"))
```

### Lifecycle-aware services

If a registered service has `start()` and `stop()` methods, the kernel will call them during lifecycle transitions.

```python
class CounterService:
    def __init__(self):
        self.started = False

    def start(self):
        self.started = True

    def stop(self):
        self.started = False
```

## 2. Tools

Tools are named capabilities that can act on a context.

The `Brain` dispatches tools automatically through the `ToolRunner` when one is
configured — the default heuristic selects a tool whose name appears in the
prompt. You can also register and execute tools directly.

```python
from xyberos.tools import ToolRegistry
from xyberos.contracts import Tool


class EchoTool(Tool):
    @property
    def name(self):
        return "echo"

    def execute(self, context, **arguments):
        return {
            "prompt": getattr(context, "prompt", ""),
            "arguments": arguments,
        }


registry = ToolRegistry([EchoTool()])
result = registry.execute("echo", context={"prompt": "hello"}, mode="debug")
```

### Typed function tools

Wrap a plain typed function with `FunctionTool` to get a JSON schema derived
from the signature and automatic argument validation/coercion. Bad arguments
raise `ToolArgumentError`:

```python
from xyberos.tools import FunctionTool


def search(query: str, limit: int = 10) -> str:
    return f"search({query}, limit={limit})"


tool = FunctionTool("search", search, description="Search the catalog")
print(tool.schema)   # typed JSON schema
print(tool.execute(None, query="books", limit="5"))  # limit coerced to 5
```

### When to use tools

- you want a named capability with a clear input/output shape
- you need to expose a specific operation like search, formatting, lookup, or transformation
- you want to keep the capability independent from the runtime and brain layers

## 3. Knowledge

Knowledge providers return information relevant to a context.

```python
from xyberos.knowledge import InMemoryKnowledge
from xyberos.runtime.context import CognitiveContext

knowledge = InMemoryKnowledge({
    "kernel": "platform services",
    "brain": "response generation",
})

context = CognitiveContext("tell me about the kernel")
print(knowledge.query(context))
```

### Adding facts

```python
knowledge.add("runtime", "request execution")
```

### When to use knowledge

- you need retrieval-style lookups
- you want to attach domain facts to a prompt
- you plan to swap the backend later, such as a document store or vector database

The `Brain` queries the configured knowledge provider automatically and injects
matching facts into the model prompt as relevant context.

## 4. Memory

Memory providers store and retrieve context history.

```python
from xyberos.memory import InMemoryMemory
from xyberos.runtime.context import CognitiveContext

memory = InMemoryMemory()
first = CognitiveContext("remember this")

memory.store(first)
print(memory.retrieve(first))
```

### When to use memory

- you want to accumulate past contexts
- you need a simple persisted history interface
- you want to replace the backend without changing callers

The `Brain` uses the configured memory provider automatically: it retrieves past
turns before generating and stores each completed turn afterward.

## 5. Planners

Planners produce an ordered plan from a context.

```python
from xyberos.planner import SequentialPlanner
from xyberos.runtime.context import CognitiveContext

planner = SequentialPlanner()
plan = planner.plan(CognitiveContext("ship the feature"))
print(plan)
```

### Custom steps

```python
planner = SequentialPlanner(("analyze", "draft", "verify"))
```

### LLM-driven planning

`LLMPlanner` asks an LLM to break the request into ordered steps, with a custom
`parse` for other shapes (e.g. JSON):

```python
from xyberos.planner import LLMPlanner
from xyberos.llm import CallableLLM

planner = LLMPlanner(CallableLLM(lambda p: "research\ndraft"))
print(planner.plan(CognitiveContext("build a report")))   # ['research', 'draft']
```

Combine with `config={"brain.inject_plan": True}` to have the Brain feed the
plan to the model prompt.

### When to use planners

- you want to derive a step list before execution
- you need a lightweight planning layer
- you may later replace it with a more advanced planner

## 6. Workflows

Workflows execute a sequence of steps against a cognitive context.

```python
from xyberos.runtime.context import CognitiveContext
from xyberos.workflows import SequentialWorkflow


def annotate(context):
    context.metadata["annotated"] = True


def respond(context):
    context.response = f"processed: {context.prompt}"
    return context


workflow = SequentialWorkflow([annotate, respond])
result = workflow.run(CognitiveContext("hello"))
print(result.response)
```

### Step behavior

- return `None` to keep the current context
- return a new `CognitiveContext` to replace it
- raise an exception to stop execution

### State graphs

`GraphWorkflow` builds a directed graph of named steps with fixed `add_edge`
and conditional `add_route` routing (branches and loops), and supports
pause/resume for human-in-the-loop. Paused runs can be checkpointed to SQLite:

```python
from xyberos.workflows import GraphWorkflow, WorkflowCheckpoint
from xyberos.exceptions import WorkflowPaused


def review(context):
    if GraphWorkflow.RESUME_KEY in context.metadata:
        context.response = "approved"
        return context
    raise WorkflowPaused(prompt="Approve?")


graph = GraphWorkflow("review")
graph.add_node("review", review)
checkpoint = WorkflowCheckpoint("runs.db")

run = graph.execute(CognitiveContext("task"))
checkpoint.save("r1", run)              # persist the pause
run = graph.resume_from_checkpoint(checkpoint, "r1", "yes")  # resume later
print(run.context.response)              # approved
```

## 7. Agents

Agents are named participants that transform a context.

```python
from xyberos import create_app
from xyberos.agents import RuntimeAgent

app = create_app()
agent = RuntimeAgent("default", app.runtime)

app.register_agent(agent)
result = app.run_agents("hello")
```

### When to use agents

- you want multiple sequential context transforms
- you want to adapt an existing runtime into a multi-agent pipeline
- you need named participants you can register, list, and remove

### Collaboration: messages, handoffs, and roles

Agents collaborate with `Message` (via `post`) and `handoff`, and carry a role
via `RoleAgent`:

```python
from xyberos.agents import RoleAgent, handoff, post


def ask(context):
    post(context, handoff("worker", sender="boss"))
    return context


app.register_agent(RoleAgent("boss", "supervisor", run=ask))
app.register_agent(
    RoleAgent("worker", "performer", run=work_step, receive=on_message)
)
app.run_agents("task", agent_names=["boss", "worker"])
```

A handoff runs its recipient next; `recipient="*"` broadcasts; agents that
implement `receive(message)` get inbound messages; the exchange is recorded on
`app.agents.messages`.

## 8. Plugins

Plugins extend the kernel by registering and unregistering services.

```python
from xyberos import create_app
from xyberos.contracts import Plugin


class DemoPlugin(Plugin):
    @property
    def name(self):
        return "demo"

    def register(self, kernel):
        kernel.register("demo_value", 123, replace=True)

    def unregister(self, kernel):
        kernel.registry.unregister("demo_value")


app = create_app()
app.load_plugin(DemoPlugin())
```

### Load from a module

If a module exports `plugin`, the loader can import and load it:

```python
app.plugins.load_from_module("my_package.my_plugin")
```

### Auto-discovery (pluggable registration)

Two mechanisms let modules/services register themselves without manual wiring.

**Convention scan** — walk a package and load every concrete `Plugin` subclass
it finds. Adding a new module to the package is enough to wire it up:

```python
# app/plugins/chat.py
class ChatPersistencePlugin(Plugin):
    @property
    def name(self):
        return "chat_persistence"

    def register(self, kernel):
        kernel.register("db_engine", engine)

    def unregister(self, kernel):
        kernel.registry.unregister("db_engine")

app.load_plugins_from("app.plugins")   # auto-discovers ChatPersistencePlugin
```

**Entry points** — a plugin is declared in its own package metadata and
found via `importlib.metadata` (the same mechanism pytest/uvicorn use), so
installing the package registers the plugin:

```toml
[project.entry-points."xyberos.plugins"]
chat = "app.plugins.persistence:ChatPersistencePlugin"
```

```python
app.load_entry_points()   # auto-discovers every installed xyberos.plugins entry point
```

Entry-point values are `module:attribute` (or a bare module whose `plugin`
export is used). Both discovery styles are idempotent — re-running never
double-registers a plugin.

## 9. Events and observability

Every layer publishes to an `EventBus` (`app.events`). Subscribe with the
canonical names from `xyberos.events`, or attach an `EventRecorder` to record
everything and forward to exporters:

```python
from xyberos.events import RESPONSE_PRODUCED, EventRecorder, LoggingExporter

app.events.subscribe(RESPONSE_PRODUCED, lambda e: print(e.data["response"]))
recorder = EventRecorder(limit=1000).subscribe_to(app.events)
recorder.add_exporter(LoggingExporter(app.logger))
```

## 10. Structured outputs

`StructuredLLM` (and the one-shot `structured` helper) parse LLM text output
into data; parse failures raise `StructuredOutputError`:

```python
from xyberos.llm import structured

data = structured(model, "Return JSON: {'ok': true}")
```

## 11. Resilience

`xyberos.utils` provides `retry`, `RateLimiter`, and `with_timeout`. The Brain
applies them to LLM/tool calls via config keys — all default to off:

```python
app = create_app(config={
    "brain.max_attempts": 3,
    "brain.retry_backoff": 0.1,
    "brain.rate_limit": 10,
    "brain.timeout": 30,
})
```

## 12. Model adapters

`xyberos.llm` ships dependency-light adapters: `OllamaLLM`, `OllamaEmbeddingLLM`,
and `OpenAICompatibleLLM` use stdlib HTTP; `OpenAILLM`, `AnthropicLLM`, and
`GeminiLLM` lazy-import their SDKs and raise a clear `ProviderError` when one
is missing:

```python
from xyberos.llm import OllamaLLM, OllamaEmbeddingLLM

app = create_app(llm=OllamaLLM(model="llama3.2"))
```

`OllamaEmbeddingLLM` calls Ollama's `/api/embed` over stdlib HTTP (no SDK), so a
single local server can provide both chat and real semantic embeddings. For a
fully-local, LLM-free-in-practice semantic app:

```python
from xyberos import create_semantic_app
from xyberos.llm import OllamaLLM, OllamaEmbeddingLLM

app = create_semantic_app(
    llm=OllamaLLM(model="llama3.2"),
    embedder=OllamaEmbeddingLLM(model="nomic-embed-text"),  # real semantic matching
    router="hybrid",                                        # template → tool → knowledge → memory → cache → LLM
)
```

## 13. Putting It Together

A typical flow looks like this:

1. Create the app with `create_app()`
2. Register services in the kernel
3. Add knowledge, memory, tools, planners, workflows, agents, or plugins as needed
4. Run the runtime or use the facade helpers

```python
from xyberos import create_app
from xyberos.llm import CallableLLM

app = create_app(llm=CallableLLM(lambda prompt: f"handled: {prompt}"))
app.register("cache", {})
print(app.chat("hello"))
```

## 14. Important Limits

- Tool selection uses a prompt-name heuristic, now preceded by intent-aware
  routing (`context.intent.target`) when an intent engine is enabled; there is
  still no schema-driven LLM function calling yet (`FunctionTool.schema` is
  available for describing tools, but selection is not LLM-driven).
- `Knowledge` and `Memory` ship with in-memory and SQLite providers; a bundled
  dependency-free `CosineVectorStore` plus optional `ChromaVectorStore` /
  `PgVectorStore` adapters (`xyberos[vectors]`) provide the semantic substrate
  (RFC-0016). Redis remains unimplemented.
- `SequentialWorkflow` is linear; `GraphWorkflow` adds branching, loops, and
  pause/resume (human-in-the-loop). Paused runs can be checkpointed to SQLite
  via `WorkflowCheckpoint`.
- Observability is limited to the in-process `EventBus`; there is no event
  persistence, distributed tracing, or metrics export yet.
- `PluginLoader` manages plugin lifecycle and discovery (entry points + package
  scan), not package installation.
- `skills` are not a core code concept in this repository.

---

## 15. Intent, vectors, and experience (RFC-0016, Phase 0)

Three additive seams extend the core without breaking the stable contracts.

### Intent engines

Implement `IntentEngine.classify(context) -> Intent`. Route by matching the
returned `Intent.target` against registered tools, agents, or workflows.

```python
from xyberos import create_app
from xyberos.intent import HeuristicIntentEngine, IntentRule

app = create_app(
    intent=HeuristicIntentEngine(
        [IntentRule("refund", ("refund", "money back"), target="refund_tool")]
    ),
    config={"brain.intent": True},
)
```

When enabled, the Brain classifies each request before planning, records it on
`context.intent`, and emits `brain.intent_classified`. `ToolRunner.choose`
honors `context.intent.target` first.

### Vector stores

Implement `VectorStore.upsert/query/delete/clear` over namespaces. The bundled
`CosineVectorStore` is dependency-free (in-memory) and `SqliteVectorStore`
persists to a SQLite file with no extra dependencies; `ChromaVectorStore` and
`PgVectorStore` are optional adapters (`pip install xyberos[vectors]`).

```python
from xyberos.vector import CosineVectorStore

store = CosineVectorStore()
store.upsert("intents", "a", [1.0, 0.0], payload={"name": "refund"})
hits = store.query("intents", [1.0, 0.0], top_k=3)
```

Embeddings are a duck-typed LLM capability (`embed(text) -> list[float]`), like
`stream`/`agenerate`. Use `EmbeddingLLM` to combine a generator with an
embedder, `OllamaEmbeddingLLM` for a local Ollama `/api/embed` server, or
`OpenAIEmbeddingLLM` for an OpenAI-compatible `/embeddings` endpoint.

### Experience / learning layer

Implement `ExperienceStore.record/query/feedback/stats`. The Brain records one
`Episode` per completed turn when enabled and emits `brain.episode_recorded`.

```python
from xyberos import create_app
from xyberos.experience import InMemoryExperience

app = create_app(
    experience=InMemoryExperience(),
    config={"experience.enabled": True},
)
app.chat("hello")          # records an episode
app.experience.stats()     # {"total": 1, "by_outcome": {...}, "by_intent": {...}}
```

Phase 1 ships those trainable providers: `LLMIntentEngine`, `EmbeddingIntentEngine`,
`CascadeIntentEngine`, `VectorMemory`, `ConsolidatingMemory`, `VectorKnowledge`,
`IngestingKnowledge`, `AdaptivePlanner`, and `ReflectivePlanner`, plus an
`app.feedback()` API and the `xyberos.learning` promote/demote helpers. A minimal
learning loop:

```python
from xyberos.learning import promote_successful, to_examples

# after requests were rated via app.feedback(...), promote the good episodes:
for prompt, response in to_examples(promote_successful(app.experience)):
    intent_engine.learn("helpful", prompt)
```

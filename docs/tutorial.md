# Xyberos Tutorial

This tutorial shows how to build a small Xyberos application using the features that exist today:

- configuration and services
- swapping the LLM and model adapters
- memory and knowledge providers (in-memory and SQLite)
- tools and typed function tools
- workflows and state graphs
- agents and multi-agent collaboration
- plugins
- events and observability
- async and streaming
- structured outputs and LLM-driven planning
- production hardening

The codebase does not currently include a first-class automatic tool-calling or `skills` subsystem. In this repository, those responsibilities are covered by tools, workflows, planners, agents, and plugins.

## 1. Create an app

The fastest entry point is `create_app()`.

```python
from xyberos import create_app

app = create_app()
print(app.chat("hello"))
```

By default, Xyberos uses `EchoLLM`, which returns the prompt unchanged.

## 2. Pass configuration

You can provide configuration at startup.

```python
from xyberos import create_app

app = create_app(config={
    "logger_name": "xyberos.tutorial",
    "log_level": "INFO",
})

print(app.config.as_dict())
```

The config object is accessible through `app.config`, and it is also registered as the `"config"` service in the kernel.

The app also exposes common services directly:

- `app.llm`
- `app.memory`
- `app.knowledge`
- `app.tools`
- `app.tool_runner`
- `app.planner`
- `app.workflow`
- `app.events`

## 3. Override the LLM

The supported way to replace the model is to pass an `LLMProvider` when you create the app.

```python
from xyberos import create_app
from xyberos.llm import CallableLLM


def reverse_text(prompt: str) -> str:
    return prompt[::-1]


app = create_app(llm=CallableLLM(reverse_text))
print(app.chat("abc"))  # cba
```

You can also instantiate the facade directly:

```python
from xyberos import Xyberos
from xyberos.llm import CallableLLM

app = Xyberos(llm=CallableLLM(lambda prompt: f"handled: {prompt}"))
```

For a real model, use one of the bundled adapters — `OllamaLLM` and
`OpenAICompatibleLLM` need no extra dependencies, while `OpenAILLM`,
`AnthropicLLM`, and `GeminiLLM` import their SDK lazily (see
[Model adapters](#19-model-adapters)):

```python
from xyberos.llm import OllamaLLM

app = create_app(llm=OllamaLLM(model="llama3.2"))   # a local Ollama server
```

### Important note

The `Brain` captures its providers when the app is constructed. If you replace a
registered provider afterwards (for example
`kernel.register("llm", ..., replace=True)`), the existing `Brain` instance
keeps its original reference. `app.load_entry_points()` re-syncs the brain from
the kernel after plugin discovery, but for a direct replacement either create a
fresh app or reassign the provider on the brain yourself.

## 4. Use the runtime

The runtime turns a prompt into a `CognitiveContext`.

```python
from xyberos import create_app

app = create_app()
context = app.run("say hello")

print(context.prompt)
print(context.response)
print(context.succeeded)
```

If you only want the generated text, use `chat()`:

```python
text = app.chat("say hello")
```

## 5. Add memory

`InMemoryMemory` is a simple provider that stores contexts in a list.

```python
from xyberos.memory import InMemoryMemory
from xyberos.runtime.context import CognitiveContext

memory = InMemoryMemory()
first = CognitiveContext("first request")
second = CognitiveContext("second request")

memory.store(first)
memory.store(second)

print(memory.retrieve(first))
```

The `Brain` wires memory automatically: it retrieves stored turns before
generating and stores each completed turn afterward. `create_app()` already
registers an `InMemoryMemory` as the default, so a default app remembers
conversations across calls.

```python
from xyberos import create_app

app = create_app()
app.chat("first message")
app.chat("what did I just say?")   # the first turn is part of the history

for entry in app.memory.retrieve(None):
    print(entry.prompt, "->", entry.response)
```

Swap in your own backend by passing `memory=` to `create_app()`. For durable
storage that survives restarts, use the SQLite provider (stdlib only):

```python
from xyberos import create_app
from xyberos.memory import SqliteMemory

app = create_app(memory=SqliteMemory("chat.db"))
```

The tool runner is available as `app.tool_runner` and can choose and execute a
tool for a context.

## 6. Add knowledge

`InMemoryKnowledge` provides keyword-based lookups.

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

You can extend it at runtime:

```python
knowledge.add("runtime", "request execution")
```

The `Brain` queries knowledge automatically: facts matching the prompt are
injected into the model input as relevant context. `create_app()` registers an
`InMemoryKnowledge` by default; pass `knowledge=` to supply your own.

```python
from xyberos import create_app
from xyberos.llm import CallableLLM
from xyberos.knowledge import InMemoryKnowledge

app = create_app(
    llm=CallableLLM(lambda prompt: prompt),   # echo the enriched prompt
    knowledge=InMemoryKnowledge({"hours": "9am-6pm"}),
)
print(app.chat("What are your hours?"))
# What are your hours?
#
# Relevant knowledge:
# {'hours': '9am-6pm'}
```

You can extend the provider at runtime with `knowledge.add(key, value)`, and use
`SqliteKnowledge("facts.db")` for a durable backend.

## 7. Use tools

Tools are named capabilities that act on a context. You register them in a
`ToolRegistry` and execute them by name, or let the `ToolRunner` dispatch based
on the prompt content.

```python
from xyberos.contracts import Tool
from xyberos.tools import ToolRegistry, ToolRunner
from xyberos.runtime.context import CognitiveContext


class ReverseTool(Tool):
    name = "reverse"

    def execute(self, context, **arguments):
        return context.prompt[::-1]


registry = ToolRegistry([ReverseTool()])
print(registry.execute("reverse", CognitiveContext("abc")))  # cba

runner = ToolRunner([ReverseTool()])
print(runner.dispatch(CognitiveContext("reverse this")))  # cba
```

For typed tools, wrap a plain function — `FunctionTool` derives a JSON schema
from the signature and validates/coerces arguments:

```python
from xyberos.tools import FunctionTool


def search(query: str, limit: int = 10) -> str:
    return f"search({query}, limit={limit})"


tool = FunctionTool("search", search, description="Search the catalog")
print(tool.schema)   # JSON schema for the parameters
print(tool.execute(CognitiveContext("x"), query="books", limit="5"))  # limit coerced to 5
```

## 8. Build workflows

Workflows execute a sequence of steps against a cognitive context. Each step can
mutate the context or return a replacement.

```python
from xyberos.workflows import SequentialWorkflow
from xyberos.runtime.context import CognitiveContext


def annotate(context):
    context.metadata["source"] = "workflow"

def respond(context):
    context.response = f"processed: {context.prompt}"
    return context


workflow = SequentialWorkflow([annotate, respond])
result = workflow.run(CognitiveContext("hello"))
print(result.response)   # processed: hello
print(result.metadata)   # {'source': 'workflow'}
```

Steps that return `None` keep the current context. Steps that return a new
`CognitiveContext` replace it. Raising an exception stops the workflow.

For branching, loops, and human-in-the-loop, use `GraphWorkflow` — a directed
graph of named steps with `add_edge` (fixed) and `add_route` (conditional):

```python
from xyberos.workflows import GraphWorkflow
from xyberos.exceptions import WorkflowPaused


def review(context):
    if GraphWorkflow.RESUME_KEY in context.metadata:   # resumed with a value
        context.response = f"approved by {context.metadata[GraphWorkflow.RESUME_KEY]}"
        return context
    raise WorkflowPaused(prompt="Approve this action?")


graph = GraphWorkflow("review")
graph.add_node("review", review)

run = graph.execute(CognitiveContext("task"))
if run.status == "paused":
    print(run.prompt)                        # "Approve this action?"
    run = graph.resume(run, "the reviewer")  # human-in-the-loop

print(run.context.response)                  # approved by the reviewer
```

Paused runs can be persisted and resumed in a later process with
`WorkflowCheckpoint("runs.db")` and `graph.resume_from_checkpoint(...)`.

## 9. Add agents

Agents are named participants that transform a context. The framework ships with
`RuntimeAgent` (which wraps a runtime) and `MultiAgentRuntime` (which runs
agents sequentially).

```python
from xyberos import create_app
from xyberos.contracts import Agent


class AuditAgent(Agent):
    name = "audit"

    def run(self, context):
        context.metadata.setdefault("audits", []).append("checked")
        return context


app = create_app()
app.register_agent(AuditAgent())
result = app.run_agents("task", agent_names=["audit", "default"])
print(result.response)
print(result.metadata)   # {'audits': ['checked']}
```

Agents can also collaborate with messages, handoffs, and roles via `RoleAgent`,
`Message`, `post`, and `handoff`:

```python
from xyberos.agents import RoleAgent, handoff, post


def ask(context):
    post(context, handoff("worker", sender="boss"))
    return context


def work(context):
    context.response = "handled by worker"
    return context


app.register_agent(RoleAgent("boss", "supervisor", run=ask))
app.register_agent(RoleAgent("worker", "performer", run=work))
app.run_agents("task", agent_names=["boss", "worker"])
```

A `handoff` message runs its recipient next, `recipient="*"` broadcasts, and
agents that implement `receive(message)` get inbound messages. The whole
exchange is recorded on `app.agents.messages`.

## 10. Load plugins

Plugins extend the kernel by registering and unregistering services. They are
first-class extension points with a stable contract.

```python
from xyberos import create_app
from xyberos.contracts import Plugin


class GreetingPlugin(Plugin):
    name = "greeting"

    def register(self, kernel):
        kernel.register("greeting", "hello from plugin")

    def unregister(self, kernel):
        kernel.registry.unregister("greeting")


app = create_app()
app.load_plugin(GreetingPlugin())
print(app.resolve("greeting"))   # hello from plugin
```

## 11. Auto-discovery

Plugins don't have to be loaded manually. Two auto-discovery mechanisms let
modules register themselves without any wiring in the app.

**Convention scan** — walk a package and load every concrete `Plugin` subclass
it finds. Drop a new module in the folder and it is wired up:

```python
app.load_plugins_from("app.plugins")   # auto-discovers every Plugin in the package
```

**Entry points** — a plugin declares itself in its package metadata and is found
via `importlib.metadata` (the same mechanism pytest and uvicorn use). Installing
the package registers the plugin:

```toml
# pyproject.toml of the plugin package
[project.entry-points."xyberos.plugins"]
chat = "app.plugins.persistence:ChatPersistencePlugin"
```

```python
app.load_entry_points()   # auto-discovers every installed xyberos.plugins entry point
```

Both styles are idempotent — re-running discovery never double-registers a plugin.

## Putting it together

A typical Xyberos app composes the kernel, an LLM, providers, tools, agents, and
plugins. For a complete walkthrough, run the
[Hello World to Full Stack](../examples/hello_world_to_full_stack/README.md)
example, or study the
[Chat App](../examples/chat_app/README.md) for a real FastAPI + database
backend with pluggable auto-discovery.

```python
from xyberos import create_app

app = create_app()

def build_message(logger, config):
    return f"{logger.name}:{config.get('logger_name')}"

app.register_factory("message", build_message)
print(app.resolve("message"))
```

## 12. Put everything together

Here is a small end-to-end example that exercises every subsystem through the
automated brain pipeline.

```python
from xyberos import create_app
from xyberos.llm import CallableLLM
from xyberos.contracts import Tool
from xyberos.knowledge import InMemoryKnowledge
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import ToolRegistry


class ReverseTool(Tool):
    @property
    def name(self):
        return "reverse"

    def execute(self, context, **arguments):
        return context.prompt[::-1]


app = create_app(
    llm=CallableLLM(lambda prompt: f"model:{prompt}"),
    knowledge=InMemoryKnowledge({"hello": "a greeting"}),
)

context = app.run("hello")
print(context.plan)                    # the planner's recorded plan
print(app.resolve("knowledge").query(context))
print(app.chat("hello"))               # the model sees the injected knowledge

# The brain dispatches tools when they are registered with the app; you can
# also execute a tool directly.
tools = ToolRegistry([ReverseTool()])
print(tools.execute("reverse", CognitiveContext("abc")))  # cba
```

> Note: because the brain is wired to every subsystem, the memory, knowledge,
> and tool steps also happen automatically inside `app.run()` / `app.chat()`
> without manual orchestration. The explicit calls above let you observe them.

## 13. The automated pipeline

Since the brain is wired to every subsystem, a single `app.chat(prompt)` runs:

1. **Workflow** — any configured steps run first; a step that sets the response short-circuits.
2. **Memory** — past turns are retrieved and added to the prompt as conversation history.
3. **Knowledge** — matching facts are retrieved and added to the prompt.
4. **Planner** — the plan is computed and recorded on `context.plan`.
5. **Tools** — a matching tool may handle the request before the model is called.
6. **LLM** — the (possibly enriched) prompt is sent to the model.
7. **Memory** — the completed turn is stored so the next request can recall it.

You can observe the memory behavior directly:

```python
from xyberos import create_app

app = create_app()
app.chat("hello")
app.chat("what did I just say?")

for entry in app.memory.retrieve(None):
    print(entry.prompt, "->", entry.response)
```

## 14. Events and observability

Every request publishes events to an `EventBus` (exposed as `app.events`):
kernel and plugin lifecycle, runtime requests, and each brain pipeline step
(memory, knowledge, planner, tools, response). Subscribe with the event names
from `xyberos.events`:

```python
from xyberos.events import RESPONSE_PRODUCED, TOKEN_STREAMED

app.events.subscribe(RESPONSE_PRODUCED, lambda e: print("response:", e.data["response"]))
app.events.subscribe(TOKEN_STREAMED, lambda e: print(e.data["token"], end=""))
```

Attach an `EventRecorder` to record everything and forward to exporters:

```python
from xyberos.events import EventRecorder, LoggingExporter

recorder = EventRecorder(limit=1000).subscribe_to(app.events)
recorder.add_exporter(LoggingExporter(app.logger))
print(recorder.counts())   # per-event counts for dashboards
```

A listener that raises is logged and isolated — it never breaks the pipeline.

## 15. Async and streaming

The synchronous API is the default; async is opt-in via `app.arun` and
`app.achat`:

```python
import asyncio
from xyberos import create_app
from xyberos.llm import AsyncLLM


async def agenerate(prompt):
    return f"async: {prompt}"


app = create_app(llm=AsyncLLM(agenerate))
response = asyncio.run(app.achat("hello"))
```

An LLM that implements `stream(prompt, on_token)` emits tokens incrementally;
the brain publishes them as `brain.token_streamed` events:

```python
from xyberos.llm import StreamingLLM


def stream(prompt, on_token):
    for token in "abc":
        on_token(token)
    return "abc"


app = create_app(llm=StreamingLLM(generate=lambda p: p, stream=stream))
```

## 16. Structured outputs

Parse LLM text output into data with `StructuredLLM` or the one-shot
`structured` helper. Parse failures raise `StructuredOutputError`:

```python
from xyberos.llm import structured

data = structured(app.llm, "Return JSON: {'city': 'Paris'}")   # -> {'city': 'Paris'}
```

## 17. LLM-driven planning

`LLMPlanner` asks the LLM to break a request into ordered steps, and the Brain
records the plan on `context.plan`:

```python
from xyberos import create_app
from xyberos.planner import LLMPlanner
from xyberos.llm import CallableLLM

app = create_app(
    config={"brain.inject_plan": True},   # optional: feed the plan to the model
    planner=LLMPlanner(CallableLLM(lambda p: "research\ndraft\nreview")),
)
print(app.run("build a report").plan)      # ['research', 'draft', 'review']
```

## 18. Production hardening

Retries, rate limiting, and timeouts are configured through `Config` and all
default to off:

```python
app = create_app(config={
    "brain.max_attempts": 3,     # retry LLM calls
    "brain.retry_backoff": 0.1,  # exponential backoff base
    "brain.rate_limit": 10,      # calls per second
    "brain.timeout": 30,         # seconds per LLM call
})
```

The standalone helpers (`retry`, `RateLimiter`, `with_timeout`) live in
`xyberos.utils`.

## 19. Model adapters

Dependency-light adapters for real models live in `xyberos.llm`:

- `OllamaLLM` — a local Ollama server (stdlib HTTP, no dependencies).
- `OpenAICompatibleLLM` — any `/chat/completions` endpoint (OpenAI, llama.cpp,
  vLLM, LM Studio).
- `OpenAILLM`, `AnthropicLLM`, `GeminiLLM` — official SDKs, imported lazily on
  first use (a clear `ProviderError` is raised if the SDK isn't installed).

```python
from xyberos.llm import OpenAILLM

app = create_app(llm=OpenAILLM(api_key="sk-..."))   # requires `pip install openai`
```

## 20. Practical guidance

- Use `create_app()` for the simplest setup.
- Pass `llm=` during creation when you want to override the model.
- Provide `memory=`, `knowledge=`, `planner=`, `workflow=`, or `tools=` when you
  want custom backends — the brain uses them automatically.
- Use tools for named operations and workflows for ordered steps.
- Use `tool_runner` when you want a simple orchestration layer that chooses and executes tools.
- Use agents when you want multiple participants to process one context.
- Use plugins when you need to add or remove kernel-level services.

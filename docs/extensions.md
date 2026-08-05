# Using Extension Surfaces

Xyberos is built around a small set of extension surfaces. This guide shows how to use the ones that exist in the codebase today:

- services
- tools
- knowledge providers
- memory providers
- planners
- workflows
- agents
- plugins

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

## 9. Putting It Together

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

## 10. Important Limits

- Tool selection uses a simple prompt-name heuristic; there is no LLM-driven
  tool-calling or tool-choice learning yet.
- `Knowledge` and `Memory` ship as in-memory reference implementations; there are
  no persistent or vector-store backends bundled yet.
- Workflows are sequential only; there is no branching, state graph, or
  human-in-the-loop support yet.
- Observability is limited to the in-process `EventBus`; there is no event
  persistence, distributed tracing, or metrics export yet.
- `PluginLoader` manages plugin lifecycle and discovery (entry points + package
  scan), not package installation.
- `skills` are not a core code concept in this repository.

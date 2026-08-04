# Xyberos Tutorial

This tutorial shows how to build a small Xyberos application using the extension surfaces that exist today:

- configuration and services
- swapping the LLM
- knowledge providers
- memory providers
- tools
- workflows
- agents
- plugins

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

### Important note

If you replace the registered `"llm"` service after the app has already built its brain, the existing `Brain` instance will still hold the old LLM object. If you need a different model after initialization, create a fresh app or rebuild the brain and runtime yourself.

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

This repository does not automatically connect memory into the runtime, so you usually register it as a service and use it from your own orchestration layer.

```python
from xyberos import create_app
from xyberos.memory import InMemoryMemory

app = create_app()
app.register("memory", InMemoryMemory())
```

The tool runner is available as `app.tool_runner` and can choose and execute a tool for a context.

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

Like memory, knowledge is a contract plus provider, not an automatic pipeline component. Register it as a service if you want the app to resolve it later.

```python
from xyberos import create_app
from xyberos.knowledge import InMemoryKnowledge

app = create_app()
app.register("knowledge", InMemoryKnowledge())
```

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

## 8. Use tools

Tools are named capabilities. The registry lets you register and execute them directly.

```python
from xyberos.contracts import Tool
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import ToolRegistry


class UppercaseTool(Tool):
    @property
    def name(self):
        return "uppercase"

    def execute(self, context, **arguments):
        suffix = arguments.get("suffix", "")
        return f"{context.prompt.upper()}{suffix}"


registry = ToolRegistry([UppercaseTool()])
result = registry.execute("uppercase", CognitiveContext("hello"), suffix="!")
print(result)  # HELLO!
```

This is useful when you want a clear, named operation such as formatting, search, lookup, or transformation.

## 9. Build a workflow

Workflows are sequential transformations over one context.

```python
from xyberos.runtime.context import CognitiveContext
from xyberos.workflows import SequentialWorkflow


def annotate(context):
    context.metadata["tutorial"] = True


def answer(context):
    context.response = f"processed: {context.prompt}"
    return context


workflow = SequentialWorkflow([annotate, answer])
result = workflow.run(CognitiveContext("hello"))
print(result.response)
```

Use workflows when you want deterministic step-by-step processing.

## 10. Add agents

Agents are named participants that process the same context in order.

```python
from xyberos import create_app
from xyberos.agents import RuntimeAgent

app = create_app()
app.register_agent(RuntimeAgent("default", app.runtime))

result = app.run_agents("hello")
print(result.response)
```

Agents are useful when you want multiple passes over a context, or when you want to adapt a runtime into a named participant.

## 11. Load plugins

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
print(app.resolve("demo_value"))
```

You can also load a plugin from a module that exports `plugin`.

```python
app.plugins.load_from_module("my_package.my_plugin")
```

## 12. Put everything together

Here is a small end-to-end example.

```python
from xyberos import create_app
from xyberos.llm import CallableLLM
from xyberos.contracts import Tool
from xyberos.knowledge import InMemoryKnowledge
from xyberos.memory import InMemoryMemory
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import ToolRegistry


class ReverseTool(Tool):
    @property
    def name(self):
        return "reverse"

    def execute(self, context, **arguments):
        return context.prompt[::-1]


app = create_app(llm=CallableLLM(lambda prompt: f"model:{prompt}"))
app.register("memory", InMemoryMemory())
app.register("knowledge", InMemoryKnowledge({"hello": "a greeting"}))
app.register("tools", ToolRegistry([ReverseTool()]))

context = app.run("hello")
memory = app.resolve("memory")
knowledge = app.resolve("knowledge")
tools = app.resolve("tools")

memory.store(context)
print(knowledge.query(context))
print(tools.execute("reverse", CognitiveContext("abc")))
print(app.chat("hello"))
```

## 13. Practical guidance

- Use `create_app()` for the simplest setup.
- Pass `llm=` during creation when you want to override the model.
- Register memory and knowledge as services when your own orchestration code needs to access them later.
- Use tools for named operations and workflows for ordered steps.
- Use `tool_runner` when you want a simple orchestration layer that chooses and executes tools.
- Use agents when you want multiple participants to process one context.
- Use plugins when you need to add or remove kernel-level services.

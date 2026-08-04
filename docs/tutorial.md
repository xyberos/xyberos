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

Swap in your own backend by passing `memory=` to `create_app()`, or by
registering a replacement service. The tool runner is available as
`app.tool_runner` and can choose and execute a tool for a context.

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

You can extend the provider at runtime with `knowledge.add(key, value)`.

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

## 14. Practical guidance

- Use `create_app()` for the simplest setup.
- Pass `llm=` during creation when you want to override the model.
- Provide `memory=`, `knowledge=`, `planner=`, `workflow=`, or `tools=` when you
  want custom backends — the brain uses them automatically.
- Use tools for named operations and workflows for ordered steps.
- Use `tool_runner` when you want a simple orchestration layer that chooses and executes tools.
- Use agents when you want multiple participants to process one context.
- Use plugins when you need to add or remove kernel-level services.

# 18. Configuring Services

[**← Previous**](17-build-your-jarvis.md) · [**Next →**](19-extension-surfaces.md)

Three approaches to wire up services (LLM, tools, knowledge, memory, etc.) in
Xyberos, from simplest to most decoupled.

The runnable version lives at [`examples/configuring_services.py`](https://github.com/xyberos/xyberos/blob/master/examples/configuring_services.py).

---

## 1. Explicit — pass instances at construction time

The simplest approach: build your providers and hand them directly to
`create_app()` or `Xyberos()`. Great for scripts, notebooks, and early
prototyping.

```python
from xyberos import Xyberos, create_app
from xyberos.llm import CallableLLM
from xyberos.knowledge import InMemoryKnowledge

# Convenience helper — fills in defaults for anything you omit
app = create_app(
    llm=CallableLLM(lambda prompt: f"response: {prompt}"),
    knowledge=InMemoryKnowledge({"hours": "9am-6pm"}),
)
print(app.chat("What are your hours?"))

# Direct construction — full control, no defaults injected
manual = Xyberos(
    llm=CallableLLM(lambda prompt: f"custom: {prompt}"),
)
print(manual.chat("hello"))

# Trainable-engine providers (RFC-0016) — pass them explicitly, enable via config
from xyberos.experience import SqliteExperience
from xyberos.intent import HeuristicIntentEngine, IntentRule

app = create_app(
    intent=HeuristicIntentEngine([IntentRule("refund", ("refund",), target="refund_tool")]),
    experience=SqliteExperience("experience.db"),
    config={"brain.intent": True, "experience.enabled": True},
)

# One-line persistent semantic app (RFC-0016) — intent/memory/knowledge/planner
# share a SqliteVectorStore("learning.db") by default; swap store= for Chroma/PgVector.
# Pass a real embedder for semantic matching (default HashEmbedder only matches
# near-identical text). OllamaEmbeddingLLM = fully local, no cloud, no SDK.
from xyberos import create_semantic_app
from xyberos.llm import OllamaLLM, OllamaEmbeddingLLM

semantic = create_semantic_app(
    llm=OllamaLLM(model="llama3.2"),
    embedder=OllamaEmbeddingLLM(model="nomic-embed-text"),
    router="hybrid",
)

# Persistent security audit trail — one config key
secure = create_app(config={"security.audit_path": "audit.db"})
secure.security.engage_kill_switch("maintenance")   # recorded to audit.db
```

### Pros and cons

- **Pros**: trivial to read, no indirection, everything in one place.
- **Cons**: the app is coupled to the concrete providers; swapping a backend
  means changing the creation site.

---

## 2. Class / factory — register with the kernel, resolved via DI

Register a **factory callable** with the kernel. The kernel inspects the
factory's parameter names and resolves them from the registry (config, logger,
or any other registered service). This is how you make a service configurable
without touching the app creation site.

```python
from xyberos import create_app
from xyberos.llm import CallableLLM, EchoLLM


def build_llm(config):
    """Factory: config is injected by name from the kernel registry."""
    provider = config.get("llm_provider", "echo")
    if provider == "echo":
        return EchoLLM()
    return CallableLLM(lambda prompt: f"[{provider}] {prompt}")


app = create_app(config={"llm_provider": "openai"})
app.register_factory("llm", build_llm, replace=True)

# resolve() picks up the factory-built provider
llm = app.resolve("llm")
print(llm.generate("hi"))  # prints: [openai] hi

# Change config at runtime — resolve picks up the new value
app.config.set("llm_provider", "claude")
llm = app.resolve("llm")
print(llm.generate("hi"))  # prints: [claude] hi
```

> Note: `app.chat()` uses the `Brain`, which captures its provider references at
> construction time. Replacing a provider via `register` / `register_factory`
> affects future `resolve()` calls but not the already-built brain.
> `app.load_entry_points()` re-syncs the brain's providers after plugin
> discovery; otherwise, build a fresh app.

### Dependency injection by parameter name

The kernel's `inject()` method resolves **any** callable by matching its
parameter names to registered services:

```python
app = create_app()
app.register("greeting", "hello from service")

# "greeting" matches the registered service name — injected automatically
def build_message(greeting, config):
    return f"{greeting} (env: {config.get('env', 'dev')})"

msg = app.inject(build_message)  # no args — resolved by name
```

### Pros and cons

- **Pros**: config-driven, swappable at runtime, testable (mock the factory).
- **Cons**: factories run inside the kernel lifecycle; DI parameter naming must
  match registered service names.

---

## 3. Plugin — auto-discovered, zero wiring in the app

Package your services as a `Plugin` and let auto-discovery load them. The app
never imports the plugin by name — it just calls `load_plugins_from()` or
`load_entry_points()`.

### Convention scan

Drop a module in a package folder. Wiring:

```python
# app/plugins/llm_plugin.py
from xyberos.contracts import Plugin
from xyberos.llm import CallableLLM

class LLMPlugin(Plugin):
    @property
    def name(self):
        return "llm_plugin"

    def register(self, kernel):
        kernel.register("llm", CallableLLM(lambda p: f"plugin: {p}"), replace=True)

    def unregister(self, kernel):
        kernel.registry.unregister("llm")
```

```python
# main.py — no import of the plugin!
from xyberos import create_app

app = create_app()
app.load_plugins_from("app.plugins")   # auto-discovers LLMPlugin

print(app.chat("hello"))  # plugin: hello
```

### Entry points

Declare the plugin in the package's `pyproject.toml`, install it, and the app
discovers it via `importlib.metadata` — same mechanism pytest and uvicorn use:

```toml
# my_chat_lib/pyproject.toml
[project.entry-points."xyberos.plugins"]
llm = "my_chat_lib.plugins:LLMPlugin"
```

```python
# In any app that has my_chat_lib installed:
app = create_app()
app.load_entry_points()   # auto-discovers every installed xyberos.plugins entry point
```

### Pros and cons

- **Pros**: fully decoupled — the app knows nothing about the plugin until
  discovery runs. Adding or removing a plugin means adding or removing a module
  (convention) or a package (entry points).
- **Cons**: requires the `Plugin` contract (register/unregister). Best for
  reusable service bundles, not one-off configuration.

---

## When to use each

| Approach | Best for |
|---|---|
| **Explicit** | Scripts, notebooks, quick prototyping |
| **Factory** | Config-driven apps, hot-swappable services |
| **Plugin** | Reusable packages, large apps with many service bundles, third-party extensions |

You can mix them — use `create_app(llm=...)` for the default and plugins for
the rest, or start explicit and extract plugins as the app grows.

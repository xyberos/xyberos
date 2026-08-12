# 9. Skills & Plugins

[**← Previous**](08-workflows.md) · [**Next →**](10-brain.md)

## What You'll Learn

- What a plugin is
- Plugin architecture
- Create your first plugin
- Load, unload, and discover plugins
- Auto-discovery (convention scan + entry points)
- Replace a plugin / provider
- Plugin lifecycle

---

## What is a plugin?

A **plugin** is a bundle that extends the kernel by registering and
unregistering services. It's the long-term home for your skills — tools,
providers, and integrations — packaged so they load automatically.

```text
Assistant
   ↓
Plugin Registry
   ↓
Plugin
   ↓
Capability (tools, providers, services)
```

## Create your first plugin

Implement the `Plugin` contract — `name`, `register(kernel)`, `unregister(kernel)`:

```python
from xyberos import create_app
from xyberos.contracts import Plugin
from xyberos.tools import ToolRegistry, FunctionTool

def greeting() -> str:
    """Return a greeting."""
    return "hello from plugin"

class GreetingPlugin(Plugin):
    @property
    def name(self):
        return "greeting"

    def register(self, kernel):
        kernel.register("greeting", "hello from plugin")
        kernel.register("tools", ToolRegistry([
            FunctionTool("greeting", greeting, description="Return a greeting"),
        ]), replace=True)

    def unregister(self, kernel):
        kernel.registry.unregister("greeting")

app = create_app()
app.load_plugin(GreetingPlugin())
print(app.resolve("greeting"))       # hello from plugin
```

## Load & unload

```python
app.load_plugin(plugin)        # register one plugin
app.unload_plugin(plugin.name) # unregister it
```

Load from a module that exports `plugin`:

```python
app.plugins.load_from_module("my_package.my_plugin")
```

## Auto-discovery (pluggable registration)

Two mechanisms let modules/services register themselves with **zero wiring**.

**Convention scan** — drop a module in a package folder and every concrete
`Plugin` subclass is loaded:

```python
# app/plugins/chat.py
class ChatPersistencePlugin(Plugin):
    @property
    def name(self):
        return "chat_persistence"

    def register(self, kernel):
        kernel.register("db_engine", engine)

app.load_plugins_from("app.plugins")   # auto-discovers ChatPersistencePlugin
```

**Entry points** — declare the plugin in its package metadata and install it;
discovery happens via `importlib.metadata` (the same mechanism pytest/uvicorn
use):

```toml
# my_chat_lib/pyproject.toml
[project.entry-points."xyberos.plugins"]
chat = "app.plugins.persistence:ChatPersistencePlugin"
```

```python
app.load_entry_points()   # auto-discovers every installed xyberos.plugins entry point
```

Both styles are idempotent — re-running never double-registers a plugin.

## Replace a plugin (swap implementations)

This is the core Xyberos concept — the default implementation is a convenience,
not a prison:

```text
Default implementation
        ↓
      Contract
        ↓
Your implementation
```

A plugin replaces a provider with `replace=True`:

```python
def register(self, kernel):
    kernel.register("llm", MyLLM(), replace=True)
```

> After `load_entry_points()`, the facade re-syncs the brain's provider
> references, so `replace=True` providers take effect immediately.

## Plugin lifecycle

- `load_plugin` / `load_entry_points` / `load_plugins_from` run before
  `app.start()` so discovered services join the kernel lifecycle.
- Services exposing `start()`/`stop()` are started in registration order and
  stopped in reverse order.
- `PluginLoader` manages lifecycle and discovery — not package installation.

## Default behavior

- `create_app()` loads no plugins automatically (no entry points are scanned
  unless you call `load_entry_points()`).
- Plugin loading is idempotent with `skip_existing=True` (the default).

## Common mistakes

- **Forgetting `register`/`unregister` symmetry** — what you register should be
  cleaned up on unload.
- **Expecting plugins to install packages** — `PluginLoader` discovers and
  manages plugins; installation is a packaging concern.
- **Calling discovery after `start()`** — call `load_entry_points()` /
  `load_plugins_from()` before `start()` so discovered services join the
  lifecycle.

## Next Step

[**10. Give It a Brain**](10-brain.md) — understand the cognitive pipeline that
orchestrates everything.

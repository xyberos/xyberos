RFC-0013 — Plugins

Title: Plugin System

Status: Accepted

Summary

Defines the Plugin subsystem — a discovery and lifecycle mechanism for
third-party extensions that register and remove platform services from the
Kernel without modifying core code.

Motivation

A framework must be extensible without forcing users to fork or patch the core.
Plugins let third parties ship LLM adapters, custom memory backends, tool
bundles, or entire agent pipelines as installable packages.

Contract

```python
class Plugin(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        """A stable, unique identifier for this plugin."""

    @abstractmethod
    def register(self, kernel: object) -> None:
        """Register the plugin's services with the platform kernel."""

    @abstractmethod
    def unregister(self, kernel: object) -> None:
        """Remove the plugin's services from the platform kernel."""
```

The contract takes ``object`` (the kernel) to avoid depending on core types,
allowing plugins to be tested in isolation.

Discovery Mechanisms

### Direct loading

```python
app.load_plugin(MyPlugin())
app.unload_plugin("my_plugin")
```

### Entry-point auto-discovery

Third-party packages declare plugins in ``pyproject.toml``:

```toml
[project.entry-points."xyberos.plugins"]
my_chat = "my_chat.plugins:plugin"
```

Then load all installed plugins with:

```python
app.load_entry_points()  # defaults to group "xyberos.plugins"
```

### Package scanning

```python
app.load_plugins_from("my_package.plugins")
```

Scans a Python package for ``Plugin`` subclasses and loads every one found.

Lifecycle

- ``load`` → calls ``plugin.register(kernel)``, stores the plugin, emits
  ``plugin.loaded`` event
- ``unload`` → calls ``plugin.unregister(kernel)``, removes the plugin, emits
  ``plugin.unloaded`` event
- Duplicate names raise ``PluginAlreadyLoadedError``
- Failed registration raises ``PluginLoadError``

After loading plugins that replace providers (e.g., a plugin that registers a
new ``"llm"`` service with ``replace=True``), the Brain's provider references
are refreshed so the new plugin takes effect immediately.

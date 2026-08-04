# Lifecycle and Service Behavior

This guide explains how services, factories, and lifecycle-aware components behave in Xyberos.

## Kernel Lifecycle

The kernel owns startup and shutdown.

```python
from xyberos import create_app

app = create_app()
app.start()
app.stop()
```

### Start behavior

- `start()` is idempotent
- lifecycle-aware services are started in registration order
- services registered after startup are started immediately if they expose `start()`

### Stop behavior

- `stop()` is idempotent
- lifecycle-aware services are stopped in reverse registration order

## Registering Services

Services are stored in the kernel registry.

```python
app.register("cache", {})
service = app.resolve("cache")
```

The app exposes the common registered services directly as convenience properties:

- `app.llm`
- `app.memory`
- `app.knowledge`
- `app.tools`
- `app.tool_runner`
- `app.planner`
- `app.workflow`
- `app.brain`
- `app.runtime`
- `app.agents`

### Replacement

You can replace an existing service by setting `replace=True`.

```python
app.register("cache", {}, replace=True)
```

## Registering Factories

Factories are resolved lazily.

```python
def build_client(logger, config):
    return (logger, config)

app.register_factory("client", build_client)
client = app.resolve("client")
```

### Singleton factories

- default behavior is singleton
- set `singleton=False` to create a fresh instance on each resolve

## Dependency Injection

Injection matches dependencies by parameter name.

```python
def build_message(logger, config):
    return f"{logger.name}:{config.get('logger_name')}"

message = app.inject(build_message)
```

### Rules

- keyword overrides win first
- then registered services are resolved by name
- default values are respected
- required missing dependencies raise a resolution error

## Plugin Lifecycle

Plugins register and unregister services through the kernel.

```python
app.load_plugin(plugin)
app.unload_plugin(plugin.name)
```

### Auto-discovery

Plugins can also be loaded automatically without manual wiring:

- `app.load_entry_points(group="xyberos.plugins")` — discovers every plugin
  declared as a Python entry point in installed packages.
- `app.load_plugins_from("app.plugins")` — walks a package and loads every
  concrete `Plugin` subclass it finds.

Both are idempotent — re-running them never double-registers a plugin. Call them
before `app.start()` so discovered services participate in the lifecycle.

## Best Practices

- register foundational services early
- call `load_entry_points()` or `load_plugins_from()` before `start()` so
  discovered services join the lifecycle
- use factories for expensive or dependency-heavy objects
- prefer `replace=True` only when the new service is intended to take over
- stop the app when you are done so lifecycle-aware services can clean up

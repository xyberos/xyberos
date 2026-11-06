# Plugin guide

> Status: Phase 3. The plugin API is preview API and lives in the core package — no extra is
> needed.

## Trust boundary

**Plugins are trusted, in-process Python code.** Adding a plugin is equivalent to importing a
library: it runs with the full privileges of your process. Xyberos provides no sandbox, no
permission model, and no protection from a plugin that misbehaves, and it makes no attempt to
limit what a plugin can do with the objects it is handed. Only add plugins you trust.

Entry-point discovery is deliberately not implemented. Application code chooses plugins
explicitly with `app.add_plugin(...)`, so startup stays visible and reproducible.

## The contract

Subclass `xyberos.Plugin`:

```python
from dataclasses import dataclass

from xyberos import App, Plugin


@dataclass(frozen=True)
class GreetingConfig:
    greeting: str = "hello"
    excited: bool = False


class GreetingPlugin(Plugin[GreetingConfig]):
    name = "greeting"              # required, unique, an identifier
    api_version = "1"              # the plugin API version this plugin targets
    requires = ()                  # plugin names that must be registered first
    config_type = GreetingConfig   # optional dataclass configuration schema

    def register(self, app: App, config: GreetingConfig) -> None:
        app.provide(Greeter, instance=Greeter(config))
        app.get("/greet")(self._greet)

    async def start(self) -> None:   # optional
        ...

    async def stop(self) -> None:    # optional
        ...


app = App()
app.add_plugin(GreetingPlugin())
```

| Member | Required | Purpose |
| --- | --- | --- |
| `name` | yes | unique plugin name; also its configuration key |
| `api_version` | no | plugin API version the plugin targets; must match the runtime major version |
| `requires` | no | other plugins that must already be registered |
| `config_type` | no | frozen dataclass describing the plugin's settings |
| `register` | yes | add providers and routes while the application is still mutable |
| `start` | no | prepare plugin-owned resources after app-scoped providers are constructed |
| `stop` | no | release plugin-owned resources before app-owned resources are closed |

`Plugin` is an abstract base class, so a missing `register` fails at import time rather than at
startup. A plugin can only be added before `app.start()`.

## Ordering

A plugin's `requires` must already be registered when it is added, so registration order is
dependency order and startup order is deterministic. A missing requirement fails immediately with
a message naming the plugin and the missing dependency; requirement cycles are impossible.

Lifecycle integration, in order:

1. `app.add_plugin(plugin)` — validate metadata, build typed configuration, run `register`.
2. `app.start()` — validate the provider graph, construct eager app-scoped providers, then start
   plugins in registration order.
3. `app.stop()` — stop plugins in reverse order, then close app-owned resources in reverse order.
   A failing `stop` hook is collected and reported through `ShutdownError.resources` as
   `plugin:<name>`, and every remaining hook still runs.

If a plugin fails to start, the plugins that already started are stopped in reverse order, the
application moves to `FAILED`, and the error names the plugin and the phase:

```text
PluginLifecycleError: plugin 'metrics' failed during start: <original error>
```

The original exception is preserved as the cause. If cleanup also fails, the message names the
plugins whose `stop` hook failed.

## Configuration

Plugin settings use the same precedence as core settings: the explicit mapping passed to
`app.add_plugin`, then the environment, then the configuration file, then the dataclass defaults.

```toml
# xyberos.toml
[plugins.greeting]
greeting = "hey"
excited = true
```

```powershell
$env:XYBEROS_PLUGINS__GREETING__EXCITED = "true"
```

```python
app.add_plugin(GreetingPlugin(), config={"greeting": "hi"})
```

- Settings sections are matched case-insensitively and normalized to lowercase.
- Supported field types are `str`, `int`, `float`, `bool`, and their `| None` forms. `int` and
  `float` accept numeric strings, and `bool` accepts `true`/`false`/`yes`/`no`/`on`/`off`/`1`/`0`,
  which is what environment variables provide.
- Unknown keys, missing required settings, and invalid values raise `PluginConfigurationError`
  naming the plugin and the setting location — never the configured value.
- A plugin that declares no `config_type` and is given configuration is rejected, so a typo in a
  settings section cannot pass silently.

## Plugin API compatibility

`PLUGIN_API_VERSION` is the version of the plugin contract this runtime implements. A plugin
declares the version it targets; the **major** component must match, so `"1"` and `"1.4"` are
compatible with a runtime at `PLUGIN_API_VERSION = "1"`. A mismatch raises
`PluginCompatibilityError` during `add_plugin`, before `register` runs and before any startup
work begins.

## Providers, replacements, and diagnostics

A plugin registers providers exactly as application code does: `app.provide(...)`. A duplicate
registration fails, so a plugin cannot silently replace an existing provider. Replacement is
explicit — application configuration calls `app.provide(..., replace=True)`, and tests use
`app.with_overrides({...})`.

Providers registered from a plugin's `register` hook are attributed automatically, and
`app.diagnostics()` reports the source of every active provider plus the plugin order:

```python
print(app.diagnostics().render())
```

```text
providers:
  Recorder [app] from application
  Metrics [app] from plugin:metrics
  Repository [app] from test override
plugins:
  metrics 1 [registered] requires: -
  summary 1 [registered] requires: metrics
```

## Routes

Plugins contribute routes through the same `App` route API the application uses
(`app.get`, `app.post`, `app.route`). Route records are compiled by the HTTP adapter, so a plugin
that adds routes needs the `http` extra installed in the application, and a plugin that adds only
services needs nothing beyond core. Route registration is rejected after `app.start()`, so a
plugin cannot add or change routes once the application is ready.

## Testing plugins

- `app.with_overrides({...})` isolates provider values. A test clone copies providers and routes
  but not plugin registrations, so plugin lifecycle hooks do not run twice across clones.
- A plugin package should be tested as a separately distributed package. The suite includes one at
  `tests/fixtures/metrics_plugin`, and `tests/integration/test_plugin_packages.py` asserts that it
  imports only public `xyberos` names.

## The catalogue

There is no plugin *registry service* and no discovery: a plugin is a package you install and add
explicitly, and `xyberos` never looks for one ([ADR 0007](./adr/0007-trusted-plugins.md)). That is a
supply-chain decision — entry-point loading means a dependency can change what your process does at
import time — but it does not mean extensions are invisible. This section is the list.

**Every name below is tracked in the manifest.** `published` means a release of this line's content
exists, `written` means the source exists but has not been released, and `retired` identifies a name
this line no longer publishes. Three names also serve a 1.x release, which is the other line's code.
Published packages are published by this project.
How to use the published packages, with the install line for each, is in [the packages
guide](../site/extend/packages.md). `tests/test_packages_manifest.py` checks this catalogue against
[`packages.toml`](../packages.toml), so a package cannot be added to the manifest and quietly omitted
here — and this page cannot invent one.

| Package | What it provides | Proved by | Status |
| --- | --- | --- | --- |
| `xyberos-mcp` | the server direction: exposing an application's tools over MCP, and a stdio transport only with the owner's approval | its own suite against a stub server | published |
| `xyberos-templates` | an engine-neutral `Templates` contract with Jinja2 shipped, a static mount, and form reading | its own tests, including the escaping pair and a render that does not block the loop | published |
| `xyberos-observability` | one explicit call that configures a handler and spans, fed by the runtime's event sink | its own tests, including that a redacted field stays redacted | published |
| `xyberos-auth` | verification only: an assertion from a shared secret or a JWKS, and a `Principal` | its own tests refusing an unsigned, an expired, and a wrong-audience assertion | published |
| `xyberos-postgres` | a `DatabaseProvider` for PostgreSQL | `assert_provider_contract` | published |
| `xyberos-storage-s3` | a `Storage` provider for S3-compatible stores | `assert_storage_contract` | published |
| `xyberos-openai-compatible` | a `ModelProvider` for OpenAI-compatible endpoints | `assert_model_provider_contract` | published |
| `xyberos-crud` | filtering, sorting, and pagination over the database provider contract, as values rather than entities | its own tests, including that a field name is resolved only through the caller's allowlist | published |
| `xyberos-memory` | persistent conversation history and explicitly scoped facts over `DatabaseProvider` | its own tests for history, scope isolation, facts, and forgetting | written |
| `xyberos-knowledge` | document chunking, embeddings, retrieval, and citations over an application-supplied `VectorStore` | its own tests and `assert_vector_store_contract` for adapters | written |
| `xyberos-db` | retired: the capability is `xyberos[database]` and the provider seam | — | retired |
| `xyberos-metrics` | retired: request metrics ship as `xyberos.http.RequestMetricsMiddleware` | — | retired |

**Every published name carries a check the job runs.** `packages.toml` records a `conformance` snippet for each
one and refuses a published name without it, because a package that is installed and not checked is worse than
one that is not installed at all. The snippet comes in one of two shapes, decided by whether this repository
ships a suite for the seam the package implements: a **provider** runs that suite, so `xyberos-postgres` runs
`assert_provider_contract` and the storage and AI packages run theirs; a package that implements **no** such
seam imports its own public names against the core it declares and asserts that the core is this line. That
second shape is weaker than a suite and it is not nothing: it is the check that fails when the installed core
is older than the module the package imports, which is exactly how a release went out without
`xyberos.storage` in it.

**Published by this project, or listed as a community plugin.** A row marked *this project* is published
by the people who publish `xyberos`, from the repository above, and its conformance suite is the one this
repository ships. A **community** plugin is listed because it passes its own tests against a released
`xyberos`; listing is a link, not an endorsement, and the [trust boundary](#trust-boundary) is the whole
of the promise either way.

**To be listed here**, open an issue with a link to the repository and one sentence on what the plugin
contributes. Two requirements: it passes its own tests against a released version, and it declares
`xyberos>=2,<3` — the 1.x line and this one share an import root, so an open upper bound is a broken
install waiting to happen.

Two capabilities in that table are **extension points rather than plugins**: a database backend for
another engine ([writing a database provider](./database-providers.md)) and a storage backend
([object storage](./storage.md)). Neither registers anything, so neither is a plugin; both are values the
application provides.

**Publishing one.** A plugin package needs very little:

```text
mycompany-xyberos-metrics/
├── pyproject.toml            # depends on xyberos >= the release you target
├── src/mycompany_metrics/
│   ├── __init__.py           # exports the Plugin subclass
│   └── plugin.py             # name, api_version, config_type, register
└── tests/
    └── test_plugin.py        # imports xyberos, never an internal module
```

Four rules make a plugin safe to depend on:

1. **Declare `api_version`** and keep the major component honest. `"1"` means "I only use what the
   version-1 plugin contract promises"; a runtime with a different major refuses to load you,
   before `register` runs.
2. **Import only public names.** `xyberos`, `xyberos.plugins`, and the documented `xyberos.*` modules —
   never an internal module. The fixture plugin's test is the pattern to copy: assert that every
   module your plugin imports is in the public surface, so an internal change surfaces as your test
   failing rather than your users breaking.
3. **Validate your own configuration.** `config_type` is checked by the runtime and unknown keys are
   rejected, so a typo fails at startup instead of being ignored.
4. **Do not reach for the application in `start`.** It is not `READY` yet; register an eager provider
   whose factory does the work, or do it in `register` ([existing limitation](#deliberate-limitations)).

**To be listed here**, open an issue with a link to the repository and one sentence on what the plugin
contributes. The only requirement is that it passes its own tests against a released version.

## Deliberate limitations

- No plugin sandbox, permission model, or isolation of untrusted code.
- No entry-point discovery; plugins are added explicitly.
- A plugin cannot resolve application services from its `start` hook, because the application is
  not `READY` yet. Register an eager provider whose factory performs that work instead, or do it
  in `register`.
- Plugins cannot be added, removed, or replaced after `app.start()`.

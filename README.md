# Xyberos

Xyberos is an experimental, composable Python application runtime. Its planned stable
surface is application composition, typed dependencies, Starlette-backed HTTP, SQLite,
and explicit in-process Workflow execution. Durable execution and AI adapters are optional.

The project is at version **`2.2.0`**, the third release of this line.
Phases 0–11 are complete: the architecture baseline, the application runtime, the Starlette HTTP
adapter with the SQLite database provider, the trusted plugin/capability model, the in-process
workflow engine, the provider-neutral AI facade with Ollama as the first adapter, the experimental
durable executor, the release engineering, the boundary decisions that state who the framework is
for, object storage and the MCP client, the introspection commands, and the distributions that live
beside this line. The public surface and its versioning rules are frozen in
[the stability guide](https://github.com/xyberos/xyberos/blob/master/docs/stability.md) and [ADR 0013](https://github.com/xyberos/xyberos/blob/master/docs/adr/0013-stable-surface-and-versioning.md).
This line publishes as **`2.x`** ([ADR 0017](https://github.com/xyberos/xyberos/blob/master/docs/adr/0017-release-identity-and-lineage.md)): the
`xyberos` name is held on the package index by the published 1.x line, which is a different codebase
and cannot be installed alongside this one. The release procedure is in
[the release guide](https://github.com/xyberos/xyberos/blob/master/docs/release.md).
**Durable execution is experimental** and is never represented as exactly-once, multi-host, or highly
available.

## Runtime

The stable `xyberos` import root exposes the core runtime: application composition, typed
configuration, dependency injection, lifecycle, context/logging helpers, and route records. It
never imports optional capabilities.

```python
from typing import Annotated

from xyberos import App, Inject, Settings


class Repository:
    async def list_users(self) -> list[str]:
        return []


class UserService:
    def __init__(self, repository: Annotated[Repository, Inject()]) -> None:
        self.repository = repository


async def main() -> None:
    app = App(settings=Settings.load())
    app.provide(Repository)
    app.provide(UserService)

    async with app.lifespan():
        service = await app.resolve(UserService)
        print(await service.list_users())
```

See [the runtime guide](https://github.com/xyberos/xyberos/blob/master/docs/runtime.md) for scopes, lifecycle, configuration, and the error
taxonomy, or start from [the tutorial](https://github.com/xyberos/xyberos/blob/master/docs/tutorial.md) if you are new to this, or
[the getting started guide](https://github.com/xyberos/xyberos/blob/master/docs/getting-started.md) and
[the hello app example](https://github.com/xyberos/xyberos/blob/master/examples/hello_app/README.md) if you would rather read reference material.
If you are reviewing the design rather than using it, start with
[the architecture review](https://github.com/xyberos/xyberos/blob/master/docs/architecture.md).

## HTTP and database

HTTP support is an optional extra over Starlette, and the SQLite provider is an optional extra
over SQLAlchemy Core and `aiosqlite`:

```python
from typing import Annotated

from xyberos import App, Inject
from xyberos.database import DatabaseProvider, SqliteSettings, sqlite_provider
from xyberos.http import HttpAdapter

app = App()
app.provide(DatabaseProvider, factory=sqlite_provider(SqliteSettings()), eager=True)


@app.get("/health")
async def health(database: Annotated[DatabaseProvider, Inject()]) -> dict[str, str]:
    await database.health()
    return {"status": "ready"}


asgi_app = HttpAdapter(app).asgi_app
```

See the [HTTP guide](https://github.com/xyberos/xyberos/blob/master/docs/http.md), the [database operations guide](https://github.com/xyberos/xyberos/blob/master/docs/database.md), and the
[`sqlite_crud` example](https://github.com/xyberos/xyberos/blob/master/examples/sqlite_crud/README.md).

## Plugins

Trusted, in-process capability integrations are added explicitly:

```python
from xyberos import App, Plugin


class GreetingPlugin(Plugin[None]):
    name = "greeting"
    config_type = None

    def register(self, app: App, config: None) -> None:
        app.provide(Greeter, instance=Greeter())


app = App()
app.add_plugin(GreetingPlugin())
```

Plugins are ordinary Python code — there is no sandbox — and `app.diagnostics().render()` reports
where every provider came from and in which order plugins start. See the
[plugin guide](https://github.com/xyberos/xyberos/blob/master/docs/plugins.md) and the [`custom_plugin` example](https://github.com/xyberos/xyberos/blob/master/examples/custom_plugin/README.md).

## Workflows

Multi-step work can be expressed as an immutable, inspectable definition with bounded retries,
conditional branches, per-step timeouts, a whole-run budget, cooperative cancellation, and
structured events. The engine is part of core and imports no optional capability:

```python
from xyberos import Retry, StepContext, Workflow, seconds


async def retrieve(value: str, context: StepContext) -> list[str]:
    return [f"document-for-{value}"]


async def answer(value: list[str], context: StepContext) -> str:
    return f"answer from {len(value)} document(s)"


workflow = (
    Workflow("support", version="1")
    .step("retrieve", retrieve, retry=Retry(max_attempts=3))
    .step("answer", answer, timeout=seconds(30))
    .edge("retrieve", "answer")
)

result = await workflow.run(input="T-1", timeout=seconds(45))
```

In-process execution keeps no state after the process exits and promises no recovery; durable
execution is a separate, experimental phase. See the [workflow guide](https://github.com/xyberos/xyberos/blob/master/docs/workflow.md) and the
[`workflow` example](https://github.com/xyberos/xyberos/blob/master/examples/workflow/README.md).

## AI

The AI facade is provider-neutral and dependency-free, so it ships in core: contracts, structured
output over a closed JSON Schema subset, allowlisted tool invocation, streaming, embeddings, and a
deterministic fake provider are all usable and testable with no SDK and no model service. Only a
vendor adapter needs an extra:

```python
from typing import Annotated

from xyberos import App, Inject
from xyberos.ai import AIFacade, ChatRequest, Message
from xyberos.ai.ollama import OllamaSettings, ollama_provider

provider_factory = ollama_provider(OllamaSettings(model="your-model"))


async def assistant_factory() -> AIFacade:
    return AIFacade(await provider_factory())


app = App()
app.provide(AIFacade, factory=assistant_factory, eager=True)


@app.get("/ask")
async def ask(assistant: Annotated[AIFacade, Inject()]) -> str:
    response = await assistant.chat(ChatRequest(messages=(Message.user("Hello"),)))
    return response.message.content
```

Prompt, completion, and credential content stays out of logs by default; content capture is an
explicit, redacted opt-in, and `Message` content never reaches an event payload. Ollama is never
started, stopped, or downloaded by the framework: a missing model is a configuration error, not
something the framework fixes. See the [AI guide](https://github.com/xyberos/xyberos/blob/master/docs/ai.md) and the
[`ai_assistant` example](https://github.com/xyberos/xyberos/blob/master/examples/ai_assistant/README.md).

## Durable execution (experimental)

Multi-step work can outlive the process that was running it. Progress is persisted in a separate
SQLite journal, so a new worker resumes from the record instead of from memory:

```python
from xyberos.durable import ActivityPolicy, JournalSettings, JournalStore, open_journal
from xyberos.durable.worker import DurableWorker, WorkerSettings

journal = await open_journal(JournalSettings(path="var/journal.db"))
store = JournalStore(journal)

await store.submit(workflow, input={"invoice": "INV-1001"}, execution_id="invoice-1001")

worker = DurableWorker(
    store,
    {"invoice:1": workflow},
    activities={"charge": ActivityPolicy()},
    settings=WorkerSettings(owner="worker-1"),
)
await worker.serve()
```

The limits are part of the contract, not a disclaimer: **single host, one journal file, at-least-once
effects**. A persisted step result proves a step completed, not that its external effect happened
exactly once. An attempt whose outcome cannot be established is recorded as `outcome_unknown` and
parked for a decision rather than retried on a guess. See the
[durable execution guide](https://github.com/xyberos/xyberos/blob/master/docs/durable.md), [ADR 0011](https://github.com/xyberos/xyberos/blob/master/docs/adr/0011-durable-executor-contract.md),
and the [`durable_workflow` example](https://github.com/xyberos/xyberos/blob/master/examples/durable_workflow/README.md).

## Command line

Five commands wrap APIs the runtime already provides — nothing is re-implemented, and no server is
bundled:

```powershell
xyberos new myapp                                   # a minimal project that runs
xyberos check --app myapp.app:create_app --app-dir src   # settings, provider graph, handler signatures
xyberos check --json --app myapp.app:create_app --app-dir src   # the same facts for a script
xyberos run --app myapp.app:asgi_app --app-dir src --reload   # delegate to your ASGI server
xyberos migrate --migrations migrations --url "sqlite:///var/app.db"
xyberos durable status --journal var/journal.db     # read-only view of the experimental journal
```

`check` never starts the application, and `run` hands the import string to the ASGI server so
reloading and shutdown stay the server's business. `check --json`, `--why CONTRACT`, and `--schema`
(which types each declared plugin's `[plugins.<name>]` section) are the machine-facing half;
`durable status` opens its journal through SQLite's `mode=ro` and never migrates it. See the
[command-line guide](https://github.com/xyberos/xyberos/blob/master/docs/cli.md).

## Development

Use Python 3.10 or newer. Install the project with development tools and run the quality
suite:

```powershell
python -m pip install -e ".[dev,http,database]"
python -m pytest
ruff check src tests examples
ruff format --check src tests examples
mypy
python -m build
```

Optional capability dependencies are intentionally separate:

```powershell
python -m pip install -e ".[http]"
python -m pip install -e ".[database]"
python -m pip install -e ".[ollama]"
python -m pip install -e ".[durable]"
```

See [the architecture plan](https://github.com/xyberos/xyberos/blob/master/docs/PLAN.md), [the phase-by-phase implementation plan](https://github.com/xyberos/xyberos/blob/master/docs/implementation.md), [the getting started guide](https://github.com/xyberos/xyberos/blob/master/docs/getting-started.md), [the tutorial](https://github.com/xyberos/xyberos/blob/master/docs/tutorial.md), [the architecture review](https://github.com/xyberos/xyberos/blob/master/docs/architecture.md), [the positioning page](https://github.com/xyberos/xyberos/blob/master/docs/positioning.md), [what is absent and what to do instead](https://github.com/xyberos/xyberos/blob/master/docs/capabilities.md), [the command-line guide](https://github.com/xyberos/xyberos/blob/master/docs/cli.md), [the runtime guide](https://github.com/xyberos/xyberos/blob/master/docs/runtime.md), [the HTTP guide](https://github.com/xyberos/xyberos/blob/master/docs/http.md), [the database operations guide](https://github.com/xyberos/xyberos/blob/master/docs/database.md), [the provider author guide](https://github.com/xyberos/xyberos/blob/master/docs/database-providers.md), [the plugin guide](https://github.com/xyberos/xyberos/blob/master/docs/plugins.md), [the workflow guide](https://github.com/xyberos/xyberos/blob/master/docs/workflow.md), [the AI guide](https://github.com/xyberos/xyberos/blob/master/docs/ai.md), [the durable execution guide](https://github.com/xyberos/xyberos/blob/master/docs/durable.md), [the testing guide](https://github.com/xyberos/xyberos/blob/master/docs/testing.md), [the troubleshooting guide](https://github.com/xyberos/xyberos/blob/master/docs/troubleshooting.md), [the security guide](https://github.com/xyberos/xyberos/blob/master/docs/security.md), [the stability guide](https://github.com/xyberos/xyberos/blob/master/docs/stability.md), [the release guide](https://github.com/xyberos/xyberos/blob/master/docs/release.md), [the performance baselines](https://github.com/xyberos/xyberos/blob/master/docs/performance.md), and [the architecture decisions](https://github.com/xyberos/xyberos/tree/master/docs/adr/). Contributors should read [the changelog](https://github.com/xyberos/xyberos/blob/master/CHANGELOG.md) and [the security policy](https://github.com/xyberos/xyberos/blob/master/SECURITY.md).

## Status and compatibility

This line publishes as `2.x`, and `2.0.0` is the release that first promised the stable runtime and
Workflow surfaces described in the implementation plan. The leading digit records lineage rather than
maturity,
because the `xyberos` name is already held on the package index by the published 1.x line
([ADR 0017](https://github.com/xyberos/xyberos/blob/master/docs/adr/0017-release-identity-and-lineage.md)).

[The stability guide](https://github.com/xyberos/xyberos/blob/master/docs/stability.md) lists which surface is stable, preview, or experimental, and
how each one changes; [ADR 0013](https://github.com/xyberos/xyberos/blob/master/docs/adr/0013-stable-surface-and-versioning.md) records the rules
behind it. From `2.0.0` — the release that first promised the stable tier — a breaking change to a
stable name requires a major release, and a minor release may break only a preview name. A patch release
breaks no documented name.

The project is licensed under the [Apache License 2.0](https://github.com/xyberos/xyberos/blob/master/LICENSE), including its express patent
grant. See [ADR 0012](https://github.com/xyberos/xyberos/blob/master/docs/adr/0012-project-licence.md) for why that licence was chosen, and
`CONTRIBUTING.md` for the contributor terms that are still open.

This line is at `2.2.0`, and [the release guide](https://github.com/xyberos/xyberos/blob/master/docs/release.md) records the procedure. A project on the published 1.x line
should pin `xyberos<2`: that line stays installable, but it is a different codebase, the two cannot
share an environment, and upgrading changes the API. Security reports go through
[SECURITY.md](https://github.com/xyberos/xyberos/blob/master/SECURITY.md), and changes are recorded in [the changelog](https://github.com/xyberos/xyberos/blob/master/CHANGELOG.md).

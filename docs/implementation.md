# Xyberos implementation plan

> Implementation status: Phases 0–11 are complete. The repository is at `2.2.0`, the third release of
> this line ([ADR 0017](adr/0017-release-identity-and-lineage.md)): the app
> runtime, the Starlette HTTP adapter with the SQLite provider, the trusted plugin/capability model,
> the Workflow engine, the optional AI facade, the experimental durable executor, the frozen public
> surface, and the release engineering. The phase table under "Phase status" is the at-a-glance state,
> and nothing is released until the project owner signs the release gate. Phases 9-11 — the extras and
> conformance suites this line ships, the packages that stay in the ecosystem repository, and developer tooling —
> are complete here: the distributions beside this line are written in
[`xyberos/xyberos-plugins`](https://github.com/xyberos/xyberos-plugins), and none of them is published. They
apply the capability-placement decision recorded under "Adopted
> implementation decisions", together with the mechanism inventory and the publication-and-naming decision
> recorded beside it: they are the additive work the release after `2.0.0` carries, they introduce no stable
> public name, and their exit gates are below.

## Purpose and release boundary

Ship a small, well-tested Python application framework whose stable surface is:

- application composition, lifecycle, configuration, and typed dependencies;
- Starlette-backed HTTP applications;
- SQLite-backed application data through a replaceable provider;
- in-process, explicit `Workflow` execution; and
- in-process, trusted plugins.

The SQLite durable executor is an opt-in **experimental** package. It must not be imported, configured, or migrated by a normal application. It is single-host only, and must never be described as exactly-once execution.

Capability beyond that surface arrives in one of two ways, and never by growing the stable surface: as an
**extra** of this package when it is small and dependency-free, or as a **package** in the ecosystem
repository when it needs a dependency this line will not adopt. Both are governed by the capability-placement
decision below, and neither changes what a bare `pip install xyberos` imports.

## Review of `PLAN.md`

> Status: recommendations 1–8 below are all accepted. Items 1, 2, 3, and 5 are implemented by
> Phases 0–1; items 4 and 8 are scheduled in the phases that own them; items 6 and 7 belong to
> Phase 4. The external review of this baseline is dispositioned in `PLAN.md` Appendix A.

### What is already strong

The architectural boundary between capability registration (what services exist) and execution (how work runs) is the right foundation. The plan also makes three important scope decisions: direct calls remain the default, Workflow is explicit, and durability cannot block the stable release. The acceptance criteria and test categories are good starting quality gates.

### Recommendations to adopt before implementation

1. **Write API contracts before modules.** Phase 0 needs versioned, executable API examples and decision records for `App`, `Inject`, provider scope, plugin lifecycle, `Workflow`, and error types. This prevents the proposed directory layout from becoming the de-facto design.
2. **Make lifecycle and DI graph validation precise.** Validate the provider graph at startup, including missing providers, cycles, scope violations, and incompatible types. Construct lazy app-scoped services on first use unless they opt into eager startup; validation must still happen before traffic. This avoids expensive or side-effectful construction merely to validate an app.
3. **Define the scope model explicitly.** Use only `app`, `request`, and `transient` initially. A request-scoped dependency may depend on app-scoped services but not the reverse. Workflow execution context is not a DI scope; Workflow input/state must be passed explicitly.
4. **Separate SQLite files, not just tables.** Use one application database and a separate executor-journal database. Enable WAL mode at database creation, set a bounded `busy_timeout`, keep write transactions short, and document that SQLite still permits one writer at a time. `synchronous=NORMAL` is a performance/durability trade-off and should be an explicit configurable default, not an unconditional guarantee.
5. **Treat context propagation as observability, not authorization.** Store trace/correlation IDs in `contextvars` and copy context when crossing into threads or custom background workers. `asyncio.create_task` already copies the current context at task creation on supported Python versions. Do not rely on ambient context for identity, tenancy, permissions, or transaction handles; pass those explicitly and re-authorize background work.
6. **Keep Workflow definitions declarative first.** A builder API produces an inspectable graph and is compatible with retries, tracing, and future durability. A decorator/imperative API can be evaluated later, but arbitrary Python control flow cannot reliably be inspected or recovered. Do not make it part of the first stable Workflow contract.
7. **Use AI adapters as Workflow test fixtures, not a reason to reorder core work.** Define the provider protocol and a deterministic fake during Workflow development. Deliver the public AI facade after Workflow semantics stabilize, while using simulated slow/failing calls to test retries, deadlines, cancellation, and usage reporting.
8. **Add compatibility and security boundaries.** Publish supported Python and Starlette version ranges, plugin API versioning, configuration precedence, secret redaction, and a public-versus-internal import policy before accepting third-party plugins.

### Corrections and clarifications

- A persisted activity result does not prove an external side effect occurred once. Durable activities require an idempotency key, an idempotent operation, or a documented reconciliation policy.
- Lease ownership needs a monotonically increasing fencing token. Every state-changing commit must condition on the current owner and token, so a stale worker cannot commit after a lease is reclaimed.
- Timeout terminology needs two levels: a cooperative step deadline and a whole-workflow deadline. Python cannot safely kill arbitrary in-process code; cancellation is cooperative and blocking/CPU-bound work needs a documented executor policy.
- The current `PLAN.md` contains mojibake (for example, `â€”` in headings and tree characters). Re-save it as UTF-8 before publishing it as project documentation.

## Technical decisions to lock in Phase 0

| Area | Decision |
| --- | --- |
| Python baseline | Python 3.10+; CI tests every supported minor version. Use `typing.Annotated` and `contextvars`; provide a small `TaskGroup` compatibility layer because `asyncio.TaskGroup` starts in Python 3.11. |
| Public package | `xyberos` is the sole stable import root; modules not re-exported from it are internal until documented otherwise. |
| Configuration | `xyberos.toml`, parsed with stdlib `tomllib` on Python 3.11+ and `tomli` on 3.10. Precedence is explicit arguments, environment, file, then defaults. Keep secrets in environment variables and redact them in errors/diagnostics. |
| Providers | Providers declare key/type, factory or instance, scope, dependencies, and optional close hook. Duplicate keys fail unless an explicit replacement/override is active. |
| Lifecycle | `register -> validate -> start -> ready -> stop`; startup follows dependency order and shutdown reverses successfully started resources. Collect shutdown failures without skipping later cleanup. |
| Plugins | Trusted, in-process Python code with a name, API version, declared dependencies, `register`, optional async `start`, and optional async `stop`. No entry-point auto-discovery in the first cut unless explicitly configured. |
| HTTP | Thin Starlette adapter. Runtime readiness completes inside ASGI lifespan before routes accept requests. |
| Database | SQLAlchemy 2.x Core with the `aiosqlite` async dialect, plus Alembic migrations. Xyberos owns configuration and transaction ownership; it does not require applications to adopt SQLAlchemy ORM. |
| Workflow | Declarative named graph; unique immutable step IDs; serializable metadata; explicit retry, timeout, and error policy. |
| AI | Ollama is the first provider, implemented as an optional `xyberos[ollama]` adapter over its HTTP API. It must not be imported or contacted by core. |
| Versioning | Development begins at `0.0.0`, a working placeholder; this line releases as `2.0.0`, where the leading digit records lineage rather than maturity ([ADR 0017](adr/0017-release-identity-and-lineage.md)). The project follows SemVer/PEP 440, and the stable, preview, and experimental tiers are declared in [stability.md](stability.md); plugin, configuration, Workflow-definition, and journal-schema compatibility are versioned independently. |
| Optionality | Ollama and durable dependencies are extras, e.g. `xyberos[ollama]` and `xyberos[durable]`; importing core must not load either. |

## Adopted implementation decisions

### Python support policy

Xyberos supports CPython **3.10 and newer**. CI must test 3.10, the current supported Python minors, and the newest stable CPython release. Type hints use `from __future__ import annotations` where needed to keep 3.10 support clean.

`asyncio.TaskGroup` is not available in Python 3.10. The runtime must expose its own small structured-concurrency abstraction with identical documented cleanup semantics, implemented using `TaskGroup` on 3.11+ and a tested compatibility implementation on 3.10. No public API may require a caller to depend directly on `TaskGroup`.

When a Python minor reaches end of life, removal is announced in a minor release and takes effect only in the next Xyberos major release, except where an urgent security/runtime incompatibility requires a documented exception.

### SQLite access and migration stack

Adopt the following implementation stack:

| Concern | Selection | Rationale |
| --- | --- | --- |
| Database toolkit | SQLAlchemy 2.x Core | Mature SQL construction, connection/transaction management, async support, and a credible path to future providers without imposing ORM entities on users. |
| SQLite async driver | `aiosqlite` | Integrates with SQLAlchemy's async SQLite dialect and keeps database calls off the ASGI event-loop thread. It still serializes work per SQLite connection and does not remove SQLite's single-writer constraint. |
| Migrations | Alembic | The established SQLAlchemy migration tool; it supports async integration and SQLite batch/table-rebuild migrations. |
| Mapping style | SQLAlchemy Core first | The framework exposes provider/transaction boundaries and does not make SQLAlchemy ORM models part of the Xyberos public API. Applications may use the ORM privately. |

Place these in a `database` optional dependency group rather than core, for example `sqlalchemy>=2.0,<2.1`, `aiosqlite>=0.20,<1`, and `alembic>=1.13,<2`; resolve and lock exact tested versions in the project lock/constraints file. Exact lower bounds must be verified against the selected Python support matrix before release.

Use `create_async_engine` with the `sqlite+aiosqlite` dialect. The provider owns engine lifetime and supplies an explicit async transaction context; an `AsyncSession` must never be shared across concurrent tasks. Configure each newly opened SQLite connection with foreign keys enabled, WAL where supported, a bounded busy timeout, and the selected synchronous policy. The database provider documentation must state that `aiosqlite` uses a worker thread per connection rather than true non-blocking SQLite I/O, so it improves event-loop behavior but not write parallelism. [SQLAlchemy SQLite documentation](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html) describes the dialect and its pooling behavior; [Alembic's SQLite batch guidance](https://alembic.sqlalchemy.org/en/latest/batch.html) explains why some SQLite schema changes require a table-rebuild migration.

Use one Alembic migration environment for application data and a separate, durable-extra migration environment for the journal database. Never auto-run migrations at normal production application startup; make migration execution an explicit CLI/deployment action. Automatic migration is acceptable only for an isolated local-development template with a clearly marked option.

### Configuration format and precedence

Adopt **TOML** in a dedicated `xyberos.toml` file. TOML fits Python packaging conventions, is readable for nested typed configuration, has a standard-library parser from Python 3.11 onward, and needs only the small, well-established `tomli` fallback on 3.10. Do not use `pyproject.toml` for runtime application settings: package-build metadata and deploy-time configuration have different owners and lifecycles. PEP 680 documents the standard-library `tomllib` addition and its `tomli` basis. [PEP 680](https://peps.python.org/pep-0680/)

The loader checks an explicit config path first; otherwise it checks `XYBEROS_CONFIG`, then `./xyberos.toml`. It fails with a clear error if an explicitly requested file is missing or malformed. There is no upward directory search, which avoids accidentally loading a parent project's settings.

Settings use this precedence, highest to lowest:

1. explicit `App(settings=...)` values supplied by the embedding application;
2. environment variables prefixed `XYBEROS_`;
3. values in `xyberos.toml`;
4. documented safe defaults.

Map nested environment settings with double underscores inside an accepted section, for example `XYBEROS_AI__OLLAMA__MODEL` maps to `[ai.ollama] model`. Parse environment values through the same typed schema as TOML values, and reject unknown keys.

```toml
schema_version = 1

[app]
name = "support-service"
environment = "development"

[ai.ollama]
base_url = "http://127.0.0.1:11434"
model = "llama3.2"
request_timeout_s = 60

[plugins.observability]
level = "INFO"
endpoint = "http://127.0.0.1:4318"
```

Core types four root keys — `schema_version`, `app`, and the **two extension channels**, each an opaque `name -> table` map the owning component validates:

- **`[plugins.<name>]`** is the channel for anything that ships a `Plugin`, and the runtime already types it: `config_type` is checked, unknown keys are rejected with the plugin and the key named, and `str`, `int`, `float`, `bool`, and their `None`-defaulted forms are coerced through the same helpers core uses. `Settings.plugin_options(name)` returns the raw section for anything that builds its own object.
- **`[ai.<name>]`** is the channel for an AI adapter, and it is deliberately *untyped* by core: core validates the section's shape and leaves every AI concept to the adapter, which reads it through `Settings.ai_options(name)` and its own `from_mapping(...)`. `OllamaSettings.from_mapping` is the worked example to copy.

Everything a package needs follows from those two, and Phase 9 must not widen `Settings` to get it. A capability that is not a plugin — a database provider, a storage backend, an AI adapter — takes its configuration as an **explicit argument**, exactly as the shipped SQLite provider does: `SqliteSettings(...)` is the settings object, and `sqlite_provider(settings)` returns the zero-argument async factory that `app.provide` accepts. Configuration belongs to the application, so the application composes it; a package has to expose a settings dataclass and a factory, and nothing more. The forward-compatible alternative the earlier draft anticipated — an `extra = "allow"` root namespace — stays unused until a candidate cannot be expressed either way, which is the same bar the capability-placement decision sets for a new protocol.

TOML is for non-secret settings. Secrets such as provider credentials belong in environment variables or an application-supplied secret provider, never committed configuration. The loader must redact values for fields classified as secrets in logs, validation errors, and diagnostics. `schema_version` is mandatory from the first public config format and is migrated/validated before other settings are consumed.

### First AI provider: Ollama

Ollama is the first provider because it offers a local HTTP API and supports the required initial facade capabilities: chat, streaming, embeddings, JSON-schema structured outputs, and tool-call payloads. The adapter uses the documented HTTP API directly through an internal async HTTP client, rather than making an Ollama Python SDK part of the framework contract. This keeps provider-specific types isolated and makes requests straightforward to mock. Ollama documents tool calls and JSON-schema `format` structured outputs in its [API documentation](https://docs.ollama.com/api).

The `xyberos[ollama]` extra contains the adapter and its HTTP-client dependency. Core import, application startup, and tests must not require the Ollama service, a downloaded model, or an accelerator. The adapter's default base URL is `http://127.0.0.1:11434`, but the model is **required configuration** in production; `llama3.2` may appear only in examples. Xyberos never pulls, starts, stops, or upgrades an Ollama model automatically.

The first adapter release includes:

- non-streaming and streaming chat completion;
- embeddings through the current Ollama embedding endpoint;
- structured output by sending a JSON schema and then independently validating the returned payload;
- tool-call parsing and Xyberos-side validation/authorization before any tool is executed;
- configurable connect/read/overall timeouts, cancellation propagation, request IDs, model metadata, and normalized errors; and
- a health/readiness check that distinguishes an unreachable service, unavailable model, and model response failure.

Model capabilities vary. The adapter must not infer that a model supports tools or structured output merely because the Ollama API accepts those fields. It validates configured capability claims at initialization where possible, retains response validation at runtime, and reports an actionable unsupported-capability error. Prompt and response content remain excluded from logs by default.

### Recommended versioning and compatibility policy

The distributable package begins at **`0.0.0`** as a working placeholder and releases as **`2.0.0`**, following [Semantic Versioning 2.0.0](https://semver.org/) together with PEP 440 spelling for Python packaging. The leading digit records **lineage**, not maturity: the `xyberos` name is held on the package index by the already-published 1.x line, which installs the same import root, so this line cannot be `0.x` or `1.0.0` ([ADR 0017](adr/0017-release-identity-and-lineage.md)). Maturity is declared by the classifier and by the tiers in [stability.md](stability.md). Development releases use forms such as `2.0.0.dev1`, `2.0.0a1`, `2.0.0b1`, and `2.0.0rc1`; pre-releases are opt-in and never selected by a normal compatible-version constraint.

| Version change | Permitted changes | Compatibility obligation |
| --- | --- | --- |
| Patch `2.x.y` | Bug fixes, documentation, and internal changes. | No break to a documented name in any tier; document every user-visible change. |
| Minor `2.x.0` | Backward-compatible features, new optional capabilities, deprecations, and breaking changes to a **preview** name. | Stable names keep working. A preview break needs an "Upgrade notes" entry and migration assistance where practical. Do not silently reuse configuration or persisted-data meanings. |
| `2.0.0` | First release of this line: the stable runtime and Workflow surfaces defined in this plan. | Freeze the documented public contract and start the stable-major policy below. It breaks compatibility with the published 1.x line, which is a different codebase. |
| Major `3.0.0` and later | Removal of deprecated API, changed stable semantics, supported-Python removal, or incompatible config/plugin/protocol change. | Migration guide, automated migration where feasible, and an overlap/deprecation period in the preceding stable major/minor line. |

Before the first release of this line, every documented surface is preview unless explicitly marked stable for a limited contract. From `2.0.0`, stable public API comprises documented imports under `xyberos`, documented CLI commands, `xyberos.toml` schema, provider/plugin protocols, documented Workflow definition format, and documented error fields. Internal module paths and underscored APIs have no compatibility promise. Experimental APIs live under `xyberos.experimental` or an explicitly marked optional package and may change in a **minor** release; every such change is listed prominently in release notes and emits `ExperimentalWarning` where practical.

Compatibility is independently versioned where persisted or third-party contracts demand it:

| Contract | Policy |
| --- | --- |
| Plugin API | `PLUGIN_API_VERSION = "1"`, and the plugin protocol is a **stable** surface ([stability.md](stability.md)), so its major component moves only in a Xyberos major release or on an incompatible contract change, which takes an ADR. A plugin declares the same major through `api_version`; a mismatch raises `PluginCompatibilityError` before `register` runs. Plugins declare a core range such as `>=2,<3` ([ADR 0013](adr/0013-stable-surface-and-versioning.md), [plugin guide](plugins.md#plugin-api-compatibility)). |
| Configuration schema | `schema_version = 1`. A minor release may add keys or make a documented breaking correction with upgrade notes; silently changing a key's meaning is forbidden. Breaking removal or reinterpretation requires a new schema version plus migration guidance and support for the prior schema for at least two minor releases whenever feasible. |
| Workflow definition format | Explicit `definition_version`. An incompatible meaning requires a new version and release note while the format is preview. Once a format version is stable, it is readable for the complete major release; an incompatible meaning requires a new version and converter or rejection before execution. |
| Durable journal schema | Alembic revision plus journal `schema_version`. Upgrade is forward-only in normal operation, tested from every supported prior journal revision, and never automatic at production app startup. |
| Serialized events/errors | Additive fields only within a major release. Consumers must ignore unknown fields. |

Deprecation policy: mark a stable API deprecated in documentation and runtime warnings in one minor release, retain it for at least two subsequent minor releases or six months (whichever is longer), and remove it only in the next major release. Security or data-corruption fixes may bypass this period, with a release-note explanation. The changelog must include an "Upgrade notes" section for every minor and major release.

### Capability placement: extendability first

**Adopted.** Xyberos 2.0 already has every mechanism a capability needs: `register(app)` for providers and
routes, `Plugin` for a distribution the runtime validates, orders, and attributes, the provider registry for
scopes, dependencies, and test overrides, and extras for an implementation this package ships. This plan adds
no mechanism, and a new protocol is justified only by a candidate that none of these fits — nothing currently
on the list qualifies, so a phase that proposed one would be proposing work without a customer.

What the mechanisms do not settle is *placement*, and one rule settles it:

| Placement | Ships as | Applies when |
| --- | --- | --- |
| **Extra, here** | `xyberos[x]`, one working implementation, tested by this repository's suite | no new third-party dependency, no policy a recorded ADR refuses, and small enough that this suite can exercise it |
| **Package, there** | a distribution in the ecosystem repository, `xyberos/xyberos-plugins` ([ADR 0022](adr/0022-ecosystem-repository-and-satellite-names.md)) | it needs a dependency core will not adopt, it carries policy, or it has its own release cadence |
| **Retire, with a pointer** | the published version stays; a metadata-only patch names the replacement | the capability landed in an extra, so a second distribution would be a second answer to one question |
| **Refuse** | nothing | a recorded ADR refuses it, or the deferred backlog holds it |

Two consequences of the rule are binding rather than stylistic, and each has an existing precedent:

- **An extra is a promise the release makes.** It is released with this package, carries its own CI row, and
  must ship one *working* implementation rather than a bare contract — which is what `[http]`, `[database]`,
  `[ollama]`, and `[durable]` do, and why a storage extra ships local files instead of only a protocol.
- **Middleware belongs to the application.** `HttpAdapter(app, middleware=(...))` is the only shape the adapter
  offers, so a cross-cutting request concern is a class the application passes; it can never be a plugin, and
  no phase may pretend otherwise. Metrics, tracing, and logging presets are therefore extras' classes or
  application code, never self-installing plugins.

Phase 9 records the rule and its reasons in **ADR 0018** when it opens; until then this subsection is the
decision, and Phases 9 and 10 exist to apply it. The alternative that looks simpler — publishing a 1.x name as
a thin package that re-exports an extra — is rejected here rather than in a phase, because the 1.x runtime and
plugin APIs are unrelated to this line's, so the body is a rewrite either way, the import root changes, and a
second distribution answering one question inherits this package's release cadence as a version constraint.

### The mechanisms a capability already has

**Adopted.** The placement rule is only usable because every candidate on Phase 9's list is already served by a
mechanism that ships and is tested today. This table is that inventory, and it exists so a phase which claims to
add no mechanism can be held to it: each row names the mechanism, the evidence that already exists, and the one
thing the new work is allowed to do with it. Putting the whole extendability surface in one place is also what
keeps the placement argument honest — a candidate that fits no row belongs *there*, or is refused, rather than
being the reason for a new protocol.

| The capability needs to… | The mechanism that already ships | Proved today by | So Phases 9-11 |
| --- | --- | --- | --- |
| register providers and routes inside an application | `App.provide`, `@app.get`, `RouteRegistry` | `tests/runtime/`, `tests/contracts/examples/phase2_http_app.py` | use it as it is; add nothing |
| arrive as a distribution the runtime validates, orders, and attributes | `Plugin`: `name`, `api_version`, `requires`, `config_type`, `register`, `start`, `stop`, with the major-version check and the unknown-key rejection done *before* `register` | `tests/plugins/`, `tests/integration/test_plugin_packages.py`, `tests/fixtures/metrics_plugin/`, `examples/custom_plugin/` | ship a `Plugin` wherever a package wants a one-line install or a typed settings section |
| carry typed configuration | `[plugins.<name>]` with `config_type`, or the opaque `[ai.<name>]` with the owning component's own `from_mapping` | `src/xyberos/plugins/config.py`, `OllamaSettings.from_mapping`, `Settings.plugin_options` / `.ai_options` | reuse both channels; a package that is not a plugin takes an explicit settings object instead |
| own an HTTP concern that is not routing | a middleware class the application passes to `HttpAdapter(app, middleware=(...))` | `src/xyberos/http/middleware.py`, `tests/http/` | request metrics is a class, never a plugin |
| replace a backend behind one contract | a contract module plus an `assert_*_contract` suite and a `temporary_*` double | `xyberos.database.contracts` with `xyberos.database.testing`, and the two deliberately broken providers in `tests/database/test_provider_contract.py` | `[storage]` copies the shape; the S3, PostgreSQL, and AI packages run the same suites from another repository |
| stand in for a slow or failing dependency in a test | `FakeModelProvider`, `ManualClock`, `FakeExternalService`, `create_test_client`, `temporary_database`, `app.with_overrides` | `tests/ai/`, `tests/workflow/`, `tests/runtime/` | new suites get doubles of the same kind, and no pytest plugin ([testing.md](testing.md) refuses one) |
| observe a run without patching internals | `EventSink` / `WorkflowEvent` / `EventType`, and the runtime context (`correlation_id`, `deadline`, `ContextLogFilter`) | `tests/workflow/`, `src/xyberos/runtime/context.py` | `xyberos-observability` subscribes to events and configures a handler; it never monkey-patches |
| fail with the command that fixes it | `_extras.extra_error`, `suggest_extra`, and the `PACKAGE_EXTRAS` map | `tests/test_optional_dependencies.py`, `tests/test_import_boundary.py`, the `installed-artefact` CI job | each extra adds its own boundary case and, if it has one, its dependency to `PACKAGE_EXTRAS` |

One row needed a qualification rather than a citation, and it is resolved above instead of by new mechanism:
**configuration for a package that is not a plugin.** A package takes its settings as an explicit factory
argument — the shape `SqliteSettings` plus `sqlite_provider` already proves — and a package that wants a typed
section under `[plugins.<name>]` ships a `Plugin` to get one. Phase 9 must prove both paths with shipped code,
one new extra and one new package taking one path each, because an extensibility claim no package has exercised
is exactly the kind of claim the rest of this document refuses.

### Where the ecosystem lives, and under which names

**Adopted.** The placement rule says *what* leaves this repository. It does not say where it lands, who
publishes it, or what it is called, and leaving those to Phase 10 would make the first satellite release the
place they get decided. They are decided here.

- **One repository, several distributions, grouped by subject.** The **ecosystem repository** is a single
  repository holding one directory per subject and one directory per distribution inside it, each distribution
  with its own `pyproject.toml`, version, and changelog. What is shared is the machinery: one CI matrix, one
  review path, one release procedure, one drift job. Phase 10's work packages already assume that layout; this
  makes it the decision rather than the discovery. The ecosystem repository is **`xyberos/xyberos-plugins`**,
  not `xyberos/xyberos`, which holds the 1.x core line, and its name, URL, and owner are recorded in
  [ADR 0022](adr/0022-ecosystem-repository-and-satellite-names.md).
- **A subject folder owns its providers.** `db/` holds the database providers, `storage/` the storage
  providers, and `llm-providers/` the model providers, one directory per distribution inside each:
  `db/xyberos_postgres/` ships `xyberos-postgres`, and a second provider for the same subject lands beside it
  rather than in a folder of its own. A retired name keeps its 1.x tree one level down, because a pointer patch
  is the last release of a name a user may still have pinned; a reused name is rewritten where it already
  lives, because a rewrite is not a patch.
- **Re-create it only if it is not controllable, and re-create it before the first upload.** The deciding cost
  is not history or stars, it is **trusted publishing**: a PyPI trusted publisher binds to a (repository,
  workflow, environment) triple, so a repository that moves invalidates the publisher for every name it
  published, and each one has to be re-registered. The repository that holds the satellites is under the
  project's control, so it becomes the ecosystem home as it stands: it already has publishers, tags, and a
  release path whose failures are understood. That is the branch
  [ADR 0022](adr/0022-ecosystem-repository-and-satellite-names.md) took, and it is why that repository's name
  and its publishing workflow's filename are both fixed. The pointer patches below need only an upload either
  way — they do not need the repository to be a new one.
- **Reuse the registered names rather than inventing new ones.** The owner already controls the `xyberos-*`
  names, so reuse costs nothing, whereas a fresh name for an existing capability splits search, documentation,
  and issue history for no gain. The resolver expresses the break on its own: a 2.x package declares
  `xyberos>=2,<3`, so an environment on the 1.x core keeps resolving the old release while an environment on 2.x
  resolves the new one. Two things stay forbidden, and they are the rule rather than a preference: **two
  distributions answering one question**, and **reviving a name no candidate needs** — the satellites without a
  customer stay untouched on the 1.x line.
- **A distribution owns a top-level import root of its own.** An extra lives inside this package and imports as
  `xyberos.<name>` (`xyberos.mcp`, `xyberos.storage`); a package imports as its own top-level module
  (`xyberos_templates`, `xyberos_auth`, `xyberos_observability`, `xyberos_postgres`, `xyberos_storage_s3`). Two
  distributions owning paths under `xyberos.*` would make `xyberos/` a namespace package shared across installs,
  where a partial install leaves a half-existing directory and an uninstall can leave files behind — and the
  boundary tests that keep core honest would stop meaning anything. The corollary is binding in the other
  direction: **an extra's import path is a promise of this package**, so moving `xyberos.mcp` into a package
  later is a breaking change. That is why Phase 9's placement table is also an import-path decision, taken
  before the code rather than with it.
- **Claim the names before writing the code, with a pre-release.** A name on the index is unclaimed until the
  first upload, so a name this plan has decided on can be taken while the package it names is still being
  written. A README-only placeholder published as a **pre-release** (`2.0.0a0`, `requires-python`, an empty
  package, the `Development Status` classifier) reserves it at essentially no cost. The placeholder must be a
  pre-release: a normal release would be selected by `pip` and would describe something that does not exist.
- **One manifest, and the documentation is checked against it.** [`packages.toml`](../packages.toml) at this
  repository's root is the single source for each distribution's name, import root, core range, dependency
  set, conformance target, and status (`placeholder`, `planned`, `written`, `published`, `retired`). It lives here
  because the documents checked against it are here: the plugin guide's catalogue, the feature matrix, and
  the release guide, all verified by `tests/test_packages_manifest.py`, the way `mkdocs.yml`'s navigation
  and `site/scripts/reference.py` are checked against the pages. The compatibility job reads the same file
  for its matrix, so nothing in the ecosystem has to repeat the list. A hand-maintained list is what Phase 8
  shipped for a repository with no packages in it; a checked one is what a published ecosystem needs.
- **Compatibility is proved against installable artefacts, and on both sides of the boundary.** The job installs
  the *published* core and the *published* package from the index into one environment, and then runs the
  package's **conformance suite** rather than a smoke test, because the suites are the contract and a smoke test
  would let a package ship that passes on the exemplar and fails on everything else. It is required before a
  core release, as Phase 10 has it, and before a package release, which Phase 10 does not: each package's own CI
  tests three cores — the newest published one, this repository's checkout, and its declared floor at the bottom
  of `xyberos>=2,<3` — so "it worked on my branch" and "it silently needs a newer core" are both caught by a job
  instead of by a user.

## Phase status

The detailed work packages live in the phase-by-phase plan below; this table is the at-a-glance
state. Phases 0–8 are complete; Phase 9 and Phase 11 are complete here, and Phase 10 is complete here
with its ecosystem half still belonging to another repository. The release decision is the project
owner's, and no artefact is published before it is made.

| Phase | Scope | Status | Exit-gate evidence |
| --- | --- | --- | --- |
| 0 | Architecture, repository, and API contracts | complete | installable core package, ADR set, CI quality gates, contract examples |
| 1 | Application runtime, registry, lifecycle, and dependency injection | complete | `tests/runtime/`, `tests/test_public_api.py`, `tests/contracts/test_contract_examples.py`, `docs/runtime.md`, [ADR 0005](adr/0005-phase-1-runtime-contract.md) |
| 2 | Starlette adapter and SQLite CRUD slice | complete | `tests/http/`, `tests/database/`, `tests/integration/`, `tests/test_import_boundary.py`, `examples/sqlite_crud/`, [ADR 0006](adr/0006-http-and-database-adapters.md) |
| 3 | Trusted plugin and capability model | complete | `src/xyberos/plugins/`, `src/xyberos/diagnostics.py`, `tests/plugins/`, `tests/integration/test_plugin_packages.py`, `tests/fixtures/metrics_plugin/`, `examples/custom_plugin/`, [ADR 0007](adr/0007-trusted-plugins.md) |
| 4 | Stable, in-process Workflow engine | complete | `src/xyberos/execution/`, `tests/workflow/` (107 tests), `tests/integration/test_workflow_example.py`, `tests/contracts/examples/phase4_workflow.py`, `examples/workflow/`, `docs/workflow.md`, [ADR 0009](adr/0009-workflow-engine-contract.md) |
| 5 | Optional AI facade | complete | `src/xyberos/ai/`, `tests/ai/` (125 tests), `tests/integration/test_ai_assistant.py` (11 tests), `examples/ai_assistant/`, `docs/ai.md`, [ADR 0010](adr/0010-ai-facade-contract.md) |
| 6 | Experimental single-host durable executor | complete | `src/xyberos/durable/` (10 modules), `tests/durable/` (100 tests), `tests/crash_recovery/` (17 process-kill tests), `tests/integration/test_durable_example.py`, `examples/durable_workflow/`, `docs/durable.md`, [ADR 0011](adr/0011-durable-executor-contract.md) |
| 7 | Developer experience, hardening, and release | complete (release decision pending owner sign-off) | all seven work packages: `docs/stability.md` + [ADR 0013](adr/0013-stable-surface-and-versioning.md) + `tests/test_public_surface.py` + `tests/test_compatibility.py` + `tests/test_deprecation.py` + `src/xyberos/deprecation.py`; `docs/getting-started.md`, `docs/testing.md`, `docs/troubleshooting.md`, `docs/security.md`, `examples/hello_app/`; `src/xyberos/cli/` + `docs/cli.md` + `tests/cli/`; `CHANGELOG.md`, `SECURITY.md`, `docs/release.md`, `tests/test_release_artefacts.py`; `tests/perf/` + `docs/performance.md`; the threat review with two credential-echo defects fixed |
| 8 | Boundary legibility and extension points | complete | [ADR 0014](adr/0014-no-identity-or-authorization-model.md), [0015](adr/0015-durability-is-single-host.md), [0016](adr/0016-database-providers-are-an-extension-point.md); `docs/positioning.md`, `docs/database-providers.md`; `assert_provider_contract` in `xyberos.database.testing` + `tests/database/test_provider_contract.py`; `examples/tenancy/`, `examples/broker_worker/` and their integration tests; the write-throughput baseline |
| 9 | Extras here, and the placement rule | complete here (retirement patches belong to the publishing release) | [ADR 0018](adr/0018-capability-placement-rule.md), [ADR 0019](adr/0019-storage-contract.md); `src/xyberos/storage/` + `tests/storage/` (44 cases), `src/xyberos/http/metrics.py` + `tests/http/test_metrics.py`, `src/xyberos/mcp/` + `tests/mcp/` (23 cases), `assert_model_provider_contract` + `assert_embedding_provider_contract` in `src/xyberos/ai/testing.py`, the opt-in live Ollama leg, `docs/storage.md`, `docs/mcp.md` |
| 10 | The packages that stay in the ecosystem repository | complete here; all eight distributions are released | [`packages.toml`](../packages.toml) + `tools/ecosystem.py` + `tests/test_packages_manifest.py` (15 cases); [`.github/workflows/compatibility.yml`](../.github/workflows/compatibility.yml) installing the published core and all eight packages per leg; [the packages guide](../site/extend/packages.md); the plugin catalogue, feature matrix, and per-name release-guide wording checked against the manifest |
| 11 | Developer tooling and the contributor loop | complete here | [ADR 0020](adr/0020-introspection-documents.md); `src/xyberos/cli/{check,schema,durable}.py` + `src/xyberos/config.schema.json` + `tests/cli/test_introspection.py` + `tests/cli/test_durable_status.py` + `tests/test_config_schema.py`; the published schema copy (`site/scripts/build.py`); `.devcontainer/devcontainer.json`, `.pre-commit-config.yaml`, `tests/test_contributor_loop.py`; `tests/integration/test_first_five_minutes.py` |

### Phase 7 entry checklist

Confirmed when Phase 7 opened; the rows below record how, and the release decision gate in the Phase 7
work package section is now the live gate.

1. Phases 0–6 are complete and every public contract is frozen in an ADR: runtime
   ([0005](adr/0005-phase-1-runtime-contract.md)), HTTP/database
   ([0006](adr/0006-http-and-database-adapters.md)), plugins
   ([0007](adr/0007-trusted-plugins.md)), Workflow
   ([0009](adr/0009-workflow-engine-contract.md)), AI
   ([0010](adr/0010-ai-facade-contract.md)), durability
   ([0011](adr/0011-durable-executor-contract.md)), and now the surface itself
   ([0013](adr/0013-stable-surface-and-versioning.md)).
2. Durable execution is explicitly experimental *and* its exit gate is met, so Phase 7 has to choose
   between promoting it and omitting it from the release; either way it must not block the stable
   runtime. Its promotion criteria are `PLAN.md` section 5.4. **Not promoted by this phase's default:
   the release decision gate carries "durable (experimental)" as a row, so the release can ship with
   durability present and labelled, or omitted.**
3. Both optional surfaces are complete enough to document as preview: the AI facade ships in core
   with only adapters behind extras, and the durable package is behind the `durable` extra with a
   separate journal.
4. Known backlog items are dispositioned rather than quietly carried: the decorator Workflow API,
   parallel steps, the step-executor boundary, richer schema keywords, streaming tool calls, and the
   AI/RAG subsystem are all recorded as deferred, and the ones needing a new ADR say so.
5. The owner decisions in "Remaining owner decisions" are settled — the license and the AI
   release/model/retention policies are decided; only the contributor terms (DCO versus CLA) and any
   promotion of durable execution remain open, and both have a decision point rather than a
   dependency.


## Detailed phase-by-phase execution plan

The phases are intentionally sequential at their public-contract boundaries. Work inside a phase can proceed in parallel only after its API contract is accepted. Do not begin a dependent phase by importing unfinished internal modules; use a fake contract implementation instead.

### Phase 0 - architecture, repository, and API contracts

**Objective:** make the first implementation decisions reviewable and make every later phase start from a reproducible development environment.

**Prerequisites:** the adopted Python, configuration, database, Ollama, and versioning decisions above are recorded as accepted ADRs. The project owner selects the license before distribution; it does not block local architecture work. **Resolved:** the license is Apache-2.0, declared in metadata from Phase 0's `pyproject.toml` ([ADR 0012](adr/0012-project-licence.md)).

**Work packages**

1. Create the `src/` package layout, `pyproject.toml`, lock/constraints policy, editable-install workflow, README, contribution guide, and test layout. Set `requires-python = ">=3.10"`; core, database, Ollama, and durable dependencies must be separate extras from day one.
2. Configure a formatter, linter, type checker, test runner, coverage threshold, dependency audit, and build verification. Add CI jobs for each supported Python version and for core-only, AI-extra, and durable-extra installation.
3. Write ADRs for the adopted database stack, TOML loader, Ollama adapter, and versioning policy, plus runtime ownership, DI scopes, lifecycle ordering, HTTP adaptation, Workflow semantics, durable-execution limits, plugin trust, logging/redaction, and public-import policy.
4. Add executable API examples for a minimal app, an injected service, a SQLite transaction, a plugin, and a simple Workflow. These are contract tests, not merely documentation snippets.
5. Establish the error taxonomy. Errors must include safe, actionable context and preserve root exceptions. The taxonomy is introduced incrementally by the phase that owns each family: Phases 0–1 define configuration, registration, dependency-resolution, and lifecycle errors; Phase 2 adds HTTP-adaptation and database errors; Phase 3 adds plugin and provider errors; Phase 4 adds Workflow-validation and Workflow-execution errors; Phase 6 adds durable-state errors and defines `ExperimentalWarning`, the warning category every experimental API emits (ADR 0003).
6. Define documentation conventions: stable versus experimental labels, version support policy, deprecation policy, and the rule that all public examples are tested in CI.

**Implementation detail:** keep the initial root module deliberately small. Public re-exports should be explicit, and every other module is internal unless the docs say otherwise. This creates freedom to reorganize implementation files without an accidental compatibility commitment.

**Verification and exit criteria**

- A fresh virtual environment can install the wheel and run the minimal example without optional extras.
- Format, lint, type checking, tests, package build, and documentation-example tests run in one documented command.
- Contract tests compile and execute the intended public APIs, using temporary fakes where a subsystem is not yet implemented.
- CI tests both source and built-wheel installation, so missing package data and accidental imports are found early.

**Deliverables:** repository baseline, CI workflow, ADR set, contribution guide, public API contract tests, and a minimal runnable app example.

### Phase 1 - application runtime, registry, lifecycle, and dependency injection

**Status:** complete. [`src/xyberos/app.py`](../src/xyberos/app.py),
[`src/xyberos/config.py`](../src/xyberos/config.py),
[`src/xyberos/errors.py`](../src/xyberos/errors.py), and
[`src/xyberos/runtime/`](../src/xyberos/runtime/) implement the public runtime; the
exit-criteria tests live in [`tests/runtime/`](../tests/runtime/) and
[`tests/test_public_api.py`](../tests/test_public_api.py); the executable example and the
[runtime guide](runtime.md) are in place.

**Objective:** implement application composition without HTTP, database, AI, or Workflow dependencies.

**Prerequisites:** Phase 0 contracts for `App`, provider records, scopes, lifecycle, configuration, and errors are accepted.

**Work packages**

1. Implement typed configuration loading and validation. Inputs are explicit constructor arguments, then environment variables, then selected config file/default values. Return field-level validation errors without echoing secret values.
2. Implement an application-local registry. A provider record includes its contract key/type, factory or supplied instance, declared dependencies, scope, ownership/close hook, source plugin, and eager/lazy flag.
3. Build a dependency graph from registration metadata and annotations. On validation, reject missing providers, ambiguous providers, cycles, unsupported annotations, and illegal scope edges. Error output must show the resolution path and registration source.
4. Implement `app`, `request`, and `transient` resolution. Cache app-scoped instances on the app and request-scoped instances on the request context; construct transient instances each time. A longer-lived service may not capture a shorter-lived service.
5. Implement `register -> validate -> start -> ready -> stop`. Start dependencies first. On a partial startup failure, stop only successfully started resources in reverse order. On shutdown, attempt all cleanup and raise/record an aggregated cleanup failure only after cleanup completes.
6. Provide context helpers for correlation IDs, logger bindings, cancellation/deadline metadata, and safe background-task creation. Context variables are copied deliberately across custom worker/thread boundaries.
7. Implement test-only overrides as a bounded context manager or app clone. Overrides must never mutate global state or bleed to parallel tests.

**Non-goals:** parameter-name DI, a global service locator, auto-wiring arbitrary classes, nested custom scopes, and automatic thread/process execution.

**Verification and exit criteria**

- Two applications with different config and overrides run concurrently in one interpreter without cross-talk.
- Unit tests prove graph ordering, cycle reports, app/request/transient cache behavior, illegal-scope rejection, lazy construction, eager-start behavior, and reverse cleanup after each failure point.
- Test cases prove that a failure before readiness prevents work from being accepted and that all shutdown hooks receive a chance to run.
- Public type checking accepts `Annotated[T, Inject()]` and rejects injection without an explicit marker where the API requires one.

**Deliverables:** `App`, registry and DI APIs, lifecycle engine, configuration module, context/logging primitives, runtime documentation, and isolated-app tests.

### Phase 2 - Starlette adapter and SQLite CRUD vertical slice

**Status:** complete. `src/xyberos/http/` and `src/xyberos/database/` implement the adapter and
provider; tests live in `tests/http/`, `tests/database/`, and `tests/integration/`, with the
import-boundary check in `tests/test_import_boundary.py`; the example is `examples/sqlite_crud/`;
guides are [HTTP](http.md) and [database](database.md). The Phase 1 follow-up on a configurable
shutdown drain landed as `settings.app.shutdown_timeout`.

**Objective:** prove that the runtime supports a conventional production-style web application before adding Workflow or AI complexity.

**Prerequisites:** Phase 1 readiness/lifecycle and request-scope contracts are complete; the SQLAlchemy Core, `aiosqlite`, and Alembic stack is available through the database extra.

**Work packages**

1. Build a thin ASGI adapter around Starlette. `App` owns the runtime while Starlette owns ASGI routing, request/response types, middleware mechanics, and test client compatibility.
2. Add route decorators and route registration. Inspect handler signatures at registration/validation time, compile explicit injected arguments, and keep ordinary request parameters separate from service injection.
3. Coordinate Starlette lifespan with the runtime. Runtime validation and startup occur before requests are accepted; runtime shutdown executes after the HTTP server stops taking new work.
4. Define middleware order and error behavior. Document the outer-to-inner order, correlation-ID placement, exception normalization, logging, and which errors are safe to expose to a client. Do not silently translate programmer errors into successful responses.
5. Implement the database provider over SQLAlchemy 2.x `AsyncEngine`/`AsyncConnection` and the `sqlite+aiosqlite` dialect: URL/path configuration, connection creation, transaction context manager, explicit migration command integration, health/readiness check, close behavior, and temporary-file test fixture. Do not expose ORM sessions as a required framework abstraction.
6. At database initialization, configure the SQLite connection with foreign keys enabled, WAL mode where compatible, a bounded busy timeout, and an explicit synchronous policy. Set database-level PRAGMAs on connection initialization, not ad hoc inside requests. Keep transactions application-defined and short; do not hold a write transaction across network calls.
7. Build one complete `sqlite_crud` example with an Alembic migration, SQLAlchemy Core table/query definitions, service layer, injected database provider, route-level validation, domain errors, and tests. Exercise SQLite batch migration once in the suite so its table-rebuild behavior is understood before production use.

**Concurrency policy:** SQLite permits a single writer. The provider may retry a small, documented set of transient lock failures only when the operation is safe to retry; it must never hide an indefinitely blocked write. The application database and future durable journal use distinct files and connection pools/configuration.

**Verification and exit criteria**

- The ASGI test client observes that startup completes before a request succeeds and that shutdown releases provider resources.
- CRUD tests cover successful operations, validation failures, missing data, rollback after an exception, and a migration from an empty database.
- Integration tests use a real temporary SQLite file and simulate concurrent writers. Expected outcomes are either bounded success/retry or a documented retryable failure, never a hung test.
- An import-boundary test proves runtime does not import Starlette unless the HTTP adapter is selected, and the database layer does not depend on route/request objects.

**Deliverables:** Starlette adapter, routing/handler injection, middleware/error policy, SQLite provider and migrations integration, CRUD example, test utilities, and database operations guide.

### Phase 3 - trusted plugin and capability model

**Status:** complete. `src/xyberos/plugins/` implements the contract, configuration, and registry;
`src/xyberos/diagnostics.py` reports provider sources and plugin order; the separately packaged
fixture plugin is `tests/fixtures/metrics_plugin/`, the example is `examples/custom_plugin/`, and
the guide is [plugins](plugins.md). The Phase 2 follow-up on provider `source` attribution landed
here: plugin registrations record `plugin:<name>` automatically.

**Objective:** make independently authored, in-process capability integrations predictable without turning the registry into a global service locator.

**Prerequisites:** Phase 1 registry and lifecycle behavior are stable; Phase 2 supplies an HTTP capability as a real plugin consumer.

**Work packages**

1. Define a versioned plugin protocol with immutable name, plugin API compatibility range, declared capability dependencies, optional typed configuration schema, `register`, optional async `start`, and optional async `stop`.
2. Implement an explicit `app.add_plugin(plugin)` path. In the first release, application code chooses plugins directly; defer package entry-point discovery so startup remains visible and reproducible.
3. Add plugin dependency ordering and diagnostics. A failure identifies plugin name/version, lifecycle phase, capability/setting involved, and the original exception chain with secrets redacted.
4. Define provider replacement behavior. Production duplicate registration fails; a named replacement is permitted only by configuration or a test override. Record the source of the active provider in diagnostics.
5. Allow plugins to register routes only through the HTTP adapter contract, and prevent route mutation after readiness.
6. Create a fixture package representing a separately distributed plugin. Test installation, compatibility rejection, duplicate name/provider failures, configuration failures, partial startup cleanup, and route contribution.

**Security boundary:** plugins are trusted arbitrary Python code. Document this in the API and do not imply a sandbox, permission model, or safe execution of untrusted package code.

**Verification and exit criteria**

- A separately packaged plugin supplies a service and optional route to an app without importing undocumented runtime internals.
- Plugin order is deterministic and a dependent plugin cannot start before its requirements are ready.
- Replacement and test override precedence are visible in a diagnostic command/result.
- Compatibility tests reject a plugin built for an incompatible plugin API version before startup work begins.

**Deliverables:** plugin protocol/API, lifecycle integration, custom-plugin example, plugin test fixture package, compatibility guide, and diagnostics output.

### Phase 4 - stable, in-process Workflow engine

**Objective:** provide explicit, inspectable multi-step execution with no persistence or recovery promises.

**Prerequisites:** Phase 1 context and error conventions are stable. A deterministic fake external-service provider is available as a test double; it does not require the Phase 5 public AI facade.

**Work packages**

1. Define immutable `Workflow`, `Step`, `Edge`, input/output contract, retry policy, backoff policy, timeout policy, cancellation token, execution context, event format, and result/error models.
2. Implement build-time graph validation: unique IDs, legal entry/exit nodes, no unsupported cycles, valid branch targets, compatible declared inputs/outputs, and serializable definition metadata. Start with sequential execution plus conditional branch edges; do not claim arbitrary DAG parallelism.
3. Implement execution using structured concurrency. The executor owns every task it creates and awaits/cancels it before returning. A step gets an explicit input, execution context, and deadline.
4. Implement bounded retries. Retry classification must be policy driven; preserve each attempt's outcome; calculate backoff from an injectable clock/random source; stop retrying on cancellation or overall deadline expiry.
5. Implement step and whole-workflow deadlines. Cancellation is cooperative. Detect/block documentation for synchronous CPU-bound or blocking I/O step functions, and provide a deliberate future executor boundary rather than unsafe forced thread termination.
6. Emit structured execution events for started, succeeded, failed, retried, skipped, timed-out, and cancelled states. Integrate trace/correlation metadata without storing sensitive input/output by default.
7. Add a Workflow inspection representation suitable for logs, tests, and documentation. It should display nodes, edges, policies, and definition version without executing handlers.

**Required semantics**

- A step’s side effect may occur more than once when a retry policy applies; callers own idempotency for side-effecting steps.
- Cancellation requested before a next step starts prevents that step from starting. Cancellation of an already-running operation is best effort and depends on the operation cooperating.
- The executor does not retain execution state after process termination. Do not reuse Workflow events as a durable journal.

**Verification and exit criteria**

- Tests deterministically cover order, branching, invalid definitions, retry limits/classification/backoff, step deadline, workflow deadline, cancellation before/during a step, error chaining, and event sequencing.
- Tests assert the executor has no child task still running after success, failure, timeout, or cancellation.
- A fake provider simulates latency, rate-limit errors, transient failures, malformed results, and a cancellation-aware call.
- Workflow documentation clearly distinguishes direct calls, Workflow execution, and experimental durable execution.

**Deliverables:** Workflow builder/executor, policies/models, event/tracing contract, graph inspection, Workflow example, deterministic fake provider, and stable Workflow API documentation.

### Phase 5 - optional AI facade

**Objective:** add model capabilities as adapters that use core runtime and Workflow interfaces but do not shape either one.

**Prerequisites:** Phase 3 provider/plugin conventions and Phase 4 error, deadline, cancellation, and tracing semantics are complete. Ollama is the first supported provider; its adapter is tested against a mocked HTTP API and, separately, a pinned supported Ollama release in opt-in integration tests.

**Work packages**

1. Define provider-neutral protocols for chat/text generation, embeddings, structured output, and optional tool invocation. Normalize request metadata, timeouts, usage, model identity, provider errors, and cancellation signals.
2. Implement a deterministic fake provider first. It supports scripted responses, structured-output failures, token/usage data, delay, rate limit, transient fault, and cancellation tests without network access.
3. Add `xyberos[ollama]` as the first provider adapter. Call the documented Ollama HTTP API through an internal async client; keep Ollama request/response models entirely inside the adapter. Configure `base_url`, required model, timeout, streaming, and optional request options through the typed TOML/environment schema. Do not auto-pull models or make Ollama a core dependency.
4. Implement structured output validation at the facade boundary. Distinguish provider transport failure, refusal, invalid provider payload, and schema validation failure so retry policy can make correct decisions.
5. Define a tool contract with explicit registration and allowlists. Tool invocations need input validation, deadline/cancellation propagation, audit events, and no implicit access to every registered app service.
6. Add Ollama embeddings and streaming chat, then validate the adapter's behavior for models that do and do not support tool calls or schema-constrained output. Defer knowledge/retrieval until its own storage, chunking, filtering, authorization, and evaluation contracts are designed.
7. Build an AI assistant example that runs entirely against the fake provider in CI and offers an explicitly configured Ollama profile for local use. Ollama-backed smoke tests are opt-in, never download models automatically, and keep prompts/responses out of CI logs.

**Security and operations policy:** never log API keys; default to metadata-only request logging; make prompt/response capture an explicit, redacted opt-in; document tool permissions and provider data-handling implications.

**Verification and exit criteria**

- Core package imports and tests pass with no AI SDK installed.
- Fake-provider tests cover timeouts, cancellation, malformed JSON/structured output, tool validation, provider errors, usage accounting, and error redaction.
- The Ollama adapter has request-shape, streaming, embedding, structured-output, tool-capability, and error-mapping tests; live service tests are separately marked and never required for normal CI.
- The AI example uses the same DI, plugin, and Workflow contracts as other services.

**Deliverables:** optional AI package, provider-neutral contracts, fake provider, selected adapters, structured-output/tool APIs, assistant example, and AI security/operations documentation.

**Shipped.** The facade, contracts, tool contract, closed schema subset, and fake provider live in
`src/xyberos/ai/` and import nothing outside the core package and the standard library, so the core
wheel answers "no AI SDK installed" with a working, fully testable facade; `xyberos.ai.ollama` is
the only module behind the `ollama` extra, and `xyberos.ai` never imports it. The frozen contract,
including the classification-is-the-retry-interface rule and the closed schema subset, is
[ADR 0010](adr/0010-ai-facade-contract.md), and `docs/ai.md` carries the guide plus the
security/operations policy with real captured log output.

Two scope notes, both deliberate:

- **Knowledge/retrieval was not built**, as work package 6 requires; it stays in the deferred
  backlog until it has its own storage, chunking, filtering, authorization, and evaluation
  contracts. `PLAN.md` section 4.5 lists it as an initial interface, so it is named there as
  deferred rather than quietly dropped.
- **Model capability claims are declared, not inferred.** The Ollama adapter cross-checks a declared
  `tools` claim against what the model reports through `/api/show`, because that is the only
  capability the API exposes; every other claim is the operator's to make.

Phase 5 also produced the next phase's inputs: AI usage metadata is the only thing Phase 6 may
persist, the event shape is metadata-only by default, and the Ollama release range and smoke-test
model names remain owner decisions.

### Phase 6 - experimental single-host durable executor

**Objective:** provide opt-in persisted Workflow progress for a carefully bounded SQLite, single-host deployment model.

**Prerequisites:** stable Workflow definition/policy/event schemas have versioning; migration tooling, temporary-file test fixtures, monotonic clock abstraction, and process-kill test harness are available. The durable package remains optional and its migrations use a separate journal database.

**Work packages**

1. Write a formal transition table and invariants before implementing workers. Specify every legal source/target state, terminal-state rules, retry scheduling, cancellation races, timeout behavior, lease expiry, worker recovery, and workflow-version incompatibility outcome.
2. Define journal schema and migrations: workflow definitions, executions, step attempts/results, ordered events, worker leases/fencing tokens, scheduled retries, and migration metadata. Include schema and workflow definition version fields in persisted records.
3. Implement execution submission transactionally: persist a known workflow definition/version, validate serializable input and payload size/redaction rules, create `PENDING` execution/event records, and expose read-only inspection.
4. Implement atomic claims with short SQLite transactions. A claim assigns worker identity, monotonic fencing token, and lease expiry. Every heartbeat, result, transition, retry, or cancellation-sensitive update has a conditional `WHERE` clause on current ownership and fencing token.
5. Implement the single worker loop: wake eligible pending/retrying work, claim, execute one permitted step through an activity boundary, persist result/transition, schedule retry, and release/renew lease. Define bounded polling/backoff and resource limits.
6. Implement cancellation. Persist the request first; prevent unstarted steps; signal running cooperative work; record final state only when the current worker has the valid fence. A cancellation request must not let a stale worker mark completed afterward.
7. Implement startup recovery: inspect expired leases/non-terminal executions, acquire a new fenced claim, and decide whether to resume, retry, reconcile, fail safely, or report incompatible definition. Recovery decisions become events.
8. Implement activity idempotency/reconciliation contracts. A side-effecting activity must accept an idempotency key or register a reconciliation operation. Surface `outcome_unknown` when a crash occurs after an external call but before result persistence.
9. Add durable inspection and operational diagnostics: execution status, event timeline, blocked/incompatible work, queue depth, lease age, worker liveness, journal schema version, and explicit experimental/single-host warnings.
10. Mark the experimental surface. Expose the durable API under the experimental boundary, emit `ExperimentalWarning` from unstable entry points, and state the single-host, at-least-once, and no-exactly-once limits in the API docs and package metadata. This discharges the ADR 0003 consequence that experimental APIs are clearly named, documented, and warned about.

**Explicit non-guarantees:** no multi-host ownership, quorum, HA, distributed locks, exactly-once external effects, arbitrary Python checkpointing, transparent replay, or recovery of non-idempotent side effects without a supplied policy.

**Verification and exit criteria**

- Unit tests exercise every state-transition-table row and verify illegal transitions cannot be persisted.
- SQL/integration tests prove atomic claim behavior, contention handling, stale-fence rejection, retry scheduling, lease expiry, cancellation races, and schema/version rejection using a real SQLite file.
- Controlled subprocess termination tests cover crash before start, during activity, after result write, before final transition, and during lease renewal. Restart results must match the documented policy.
- A side-effect simulation proves at-least-once behavior and demonstrates idempotency/reconciliation or `outcome_unknown`, never an unsupported exactly-once claim.
- Documentation provides backup/restore, journal growth/retention, supported deployment topology, incident triage, and data sensitivity guidance.
- Experimental labelling is verified: unstable entry points emit `ExperimentalWarning`, the experimental namespace is used, and package metadata and docs state the single-host and at-least-once limits.

**Deliverables:** optional durable package, schema/migrations, store, scheduler/worker/recovery components, process-fault test harness, durable-workflow example, operator guide, and experimental API label with `ExperimentalWarning`.

**Shipped.** All ten work packages are implemented. The transition table and invariants are frozen in
[ADR 0011](adr/0011-durable-executor-contract.md) and locked by a test that lists every row; the
journal owns a versioned schema in a separate file and refuses one written by a newer package; the
store submits transactionally, claims atomically under a monotonic fencing token, and guards every
write with ownership and the token; a pure scheduler re-derives the next step from persisted state
alone; a worker advances one step per claim, heartbeats its lease, and turns a persisted cancellation
request into cooperative cancellation; recovery resumes what it can prove, retries only what a step
declares idempotent, asks a reconciler when one exists, and parks everything else as
`outcome_unknown`. `docs/durable.md` is the operator guide and `examples/durable_workflow/` shows both
crash cases.

The exit gate is met: `tests/durable/` covers every transition-table row, atomic claims, contention,
stale-fence rejection, retry scheduling, lease expiry, cancellation races, and schema/version
rejection against a real SQLite file; `tests/crash_recovery/` kills a real subprocess at each of the
five documented boundaries and asserts the documented policy in the parent; a side-effect log proves
at-least-once behavior and shows reconciliation resolving an uncertain attempt without a repeat; and
the experimental labelling is verified by emitting `ExperimentalWarning` from `open_journal` and
`DurableWorker`.

Two decisions taken while implementing are worth naming, because they define the contract's edges: a
ready execution belongs to nobody (a live lease protects `RUNNING` work only, so one worker advances
one step per claim and yields), and an unresolved attempt is never handed out as work (the scheduler
reports `NEEDS_DECISION`, so a resumed-but-unreconciled execution parks again instead of silently
repeating an effect).

**Deliberate non-guarantee:** the single-host, at-least-once limits are stated in the guide, the ADR,
the package docstring, and the emitted warning. Phase 7 decides whether to promote or omit, and must
not represent durability as exactly-once, multi-host, or highly available.

### Phase 7 - developer experience, hardening, and release

**Status:** work complete; the release decision itself is the project owner's. All seven work packages
are done: the surface is audited and frozen, the cross-cutting guides and the hello app example are
published, the CLI exists, the release engineering and the resource baselines are in place, and the
threat and abuse review is complete with its two findings fixed. The ADR consequence lists were
walked: every item is satisfied, owned by a named phase, or in the standing deferred backlog. What
remains is a go/no-go decision, and no artefact is published before it.

**Objective:** turn validated features into a release that users can install, understand, upgrade, and operate safely.

**Prerequisites:** stable scope is feature complete (Phases 0-5) and durable capabilities are either explicitly experimental or omitted from the release if their exit gate is not met.

**Work packages**

1. Audit the public API and freeze the stable surface. Add deprecation mechanics, semantic-versioning rules, supported-version policy, and compatibility tests for public imports, configuration fields, plugin protocol, and serialized Workflow definition metadata. **Done:** `docs/stability.md` states the tiers to users, [ADR 0013](adr/0013-stable-surface-and-versioning.md) records the rules, `src/xyberos/deprecation.py` provides the mechanics, and `tests/test_public_surface.py`, `tests/test_compatibility.py`, and `tests/test_deprecation.py` pin it. The audit's finding was the argument for doing it: five documented modules leaked their imports (`Mapping`, `json`, `sys`) as public surface because they declared no `__all__`.
2. Complete documentation: getting started, runtime/DI, configuration, lifecycle, HTTP, SQLite, plugins, Workflow, AI, testing, migrations, error troubleshooting, security considerations, and a separate durable-execution limitations/operator guide. **Done:** each subsystem already had a guide, and this package added the four cross-cutting ones — [getting started](getting-started.md), [testing](testing.md), [troubleshooting](troubleshooting.md), and [security](security.md). Writing them found two documentation defects in `docs/runtime.md` that had survived five phases: `App.resolve` was documented as synchronous when it is a coroutine, and the settings were named as attributes of `App` when they live on `app.settings.app`. Both are corrected, because a guide that names an API that does not exist is worse than no guide. Two further documents were added afterwards for the two audiences a guide set tends to miss: [the tutorial](tutorial.md), whose every output block is produced by running the code it belongs to and is checked by `tests/integration/test_tutorial.py`, and [the architecture review](architecture.md), which is the reviewer's entry point to the design.
3. Finish minimal CLI commands only where they wrap proven APIs: project scaffold, development server, configuration validation/diagnostics, and migrations. Avoid making the CLI a second runtime implementation. **Done:** `src/xyberos/cli/` provides `check`, `new`, `run`, and `migrate` on `argparse` alone. `check` calls `Settings.load` and `App.validate()` and compiles route handlers through the adapter when the extra is installed; `run` hands an import string to the ASGI server so reloading stays the server's job; `migrate` calls `run_migrations`/`apply_migrations` and redacts a password in the URL. Nothing is imported on the application's behalf except in `check`, which starts nothing.
4. Publish tested examples: hello app, SQLite CRUD, custom plugin, Workflow with retry/branch, AI assistant using fake provider, and durable workflow with its limitations displayed prominently. **Done:** `examples/hello_app/` completes the set, and every example is exercised by `tests/integration/`, so an example that stops working fails the suite rather than being discovered by a reader.
5. Add release engineering: changelog, release notes, signed/tagged artifacts as appropriate, SBOM/dependency license audit, vulnerability response policy, wheel/sdist checks, clean-install smoke test, and rollback/release instructions. **Done:** `CHANGELOG.md` (Keep a Changelog, `Unreleased` becoming `2.0.0`), `SECURITY.md` (the vulnerability response policy), `docs/release.md` (the procedure, the dependency and licence audit computed from installed metadata, and the rollback instructions), `tests/test_release_artefacts.py` (the wheel and sdist checks, which build the artefacts rather than trusting the checkout), and a CI job that installs the built wheel into a fresh environment and exercises the CLI from it.
6. Run performance and resource smoke tests. Establish only modest, reproducible baselines for app startup, simple route latency, Workflow overhead, SQLite contention behavior, and durable journal throughput. Treat regressions as signals for investigation, not premature optimization targets. **Done:** `tests/perf/` measures all five, prints one table, and asserts ceilings an order of magnitude above the recorded numbers so a slow machine does not fail the suite. `docs/performance.md` records the baseline, what each measurement includes, and what has deliberately not been optimized.
7. Conduct a final threat/abuse review covering secret handling, configuration diagnostics, provider/plugin trust, tool allowlists, SQL/path input handling, journal payload retention, and logging redaction. **Done:** all seven areas were reviewed against the code rather than the docstrings, and six came back clean with evidence — SQL is built from static strings and bound parameters (the f-string fragments in `durable/store.py` and the PRAGMA interpolation use framework constants and allowlists), the tool set is the allowlist with schema-validated arguments and a container-free context, durable fencing re-states owner/fence/expiry in every conditional write, and `max_payload_bytes` is enforced on every persisted field. Two defects were found in secret handling and both are fixed: a database URL containing `%` crashed Alembic's configuration with the whole URL — password included — in the message, and a rejected Ollama `base_url` echoed a credential it carried when the scheme was also wrong. Regression tests live in `tests/database/test_migrations.py`, `tests/cli/test_cli.py`, and `tests/ai/test_ollama.py`.

**Release decision gate**

| Release area | Required evidence | Where it is |
| --- | --- | --- |
| Core runtime | Lifecycle/DI/configuration tests, clean install, docs examples, supported-version CI | `tests/runtime/`, `tests/contracts/`, `tests/integration/test_hello_app.py`, the `quality` matrix on 3.10–3.13, the `installed-artefact` job |
| HTTP and SQLite | CRUD integration suite, migration test, contention policy test, documented deployment limits | `tests/http/`, `tests/database/`, `tests/integration/test_sqlite_crud.py`, `tests/database/test_migrations.py`, the contention baseline in `tests/perf/`, [database guide](database.md) |
| Plugins | Independent fixture-plugin compatibility suite and versioning documentation | `tests/fixtures/metrics_plugin/`, `tests/integration/test_plugin_packages.py`, `tests/plugins/`, [plugin guide](plugins.md) |
| Workflow | Deterministic behavior suite for validation, retries, cancellation, deadlines, and events | `tests/workflow/`, `tests/contracts/examples/phase4_workflow.py`, [workflow guide](workflow.md) |
| AI | Core-without-AI install, fake-provider suite, redaction/tool tests, adapter contract tests | `tests/ai/`, `tests/integration/test_ai_assistant.py`, the core-only smoke steps in the `optional-installation` job, [AI guide](ai.md) |
| Durable (experimental) | Fault/restart suite, state/lease tests, limitations/operator documentation | `tests/durable/`, `tests/crash_recovery/` (17 process-kill tests), `tests/integration/test_durable_example.py`, [durable guide](durable.md), [performance baselines](performance.md) |

Two rows are decisions rather than evidence lists:

- **Durable execution ships experimental.** Its exit gate is met — that is why it is in the release at
  all — but the promotion evidence in `PLAN.md` section 5.4 is not, so the label stays and the API
  keeps warning.
- **The extra can be omitted instead.** Nothing in the stable tier depends on it, and the
  `optional-installation` job tests every extra in isolation, so a release without durability is a
  supported configuration rather than a diminished one.

**Deliverables:** release candidate, versioned docs, tested examples/templates, changelog/release notes, CI evidence, and a go/no-go checklist signed off by the project owner. Concretely: the release
candidate is the `python -m build` output at the tagged commit, the versioned docs are `docs/` at that
tag ([stability](stability.md) and [release](release.md) included), the examples are the eight under
`examples/` — each exercised by `tests/integration/` — the changelog is [`CHANGELOG.md`](../CHANGELOG.md),
the evidence is the `quality`, `installed-artefact`, and `optional-installation` jobs, and the
procedure that ties them together is [the release guide](release.md).

### Phase 8 - boundary legibility and extension points

**Objective:** make the limits of the framework *legible and actionable* rather than discovered, without
growing core. Phase 7 ended with a list of things Xyberos is a poor fit for; leaving them as an
unexplained absence is what loses a reader, and fixing them by adding features is what loses the
project's reason to exist.

**Prerequisites:** Phase 7 complete, so the surface, the docs, and the release procedure are frozen
enough that a new document is a claim about something stable.

**Work packages**

1. **Record the refusals as decisions.** [ADR 0014](adr/0014-no-identity-or-authorization-model.md)
   (no identity, tenancy, or authorization, plus the sanctioned explicit-principal shape),
   [ADR 0015](adr/0015-durability-is-single-host.md) (single-host durability, with the worker role as
   the integration point and the alternatives named), and
   [ADR 0016](adr/0016-database-providers-are-an-extension-point.md) (one provider shipped, the contract
   reusable). Each records why, and what to do instead.
2. **Publish the positioning page.** [`docs/positioning.md`](positioning.md): who it is for and who it
   is not for, the "if you need X, use Y" table, supported topologies, the capacity summary, and the
   table of defaults with the seam that replaces each one. This is the cheapest artifact in the phase
   and the one that protects the most: it stops wrong adopters arriving.
3. **Make the database provider contract reusable.** `assert_provider_contract` ships in
   `xyberos.database.testing` (preview tier, extra-gated, so core is untouched); the shipped SQLite
   provider runs it in `tests/database/test_provider_contract.py`, which also proves the suite *fails*
   for two deliberately broken providers — one that commits rolled-back work, one whose `retrying`
   drops the operation's result. [`docs/database-providers.md`](database-providers.md) is the author
   guide, including what stays SQLite-specific.
4. **Publish capacity guidance with measured numbers.** A write-throughput scenario joined
   `tests/perf/`, and [`docs/performance.md`](performance.md#capacity-where-the-wall-is) states the two
   findings: about 2 000 writes per second from one writer, and the counter-intuitive one — under
   contention the retry backoff, not the disk, sets the pace.
5. **Ship the two highest-demand integrations as tested recipes.**
   [`examples/tenancy/`](../examples/tenancy/README.md) proves that a payload claiming another tenant
   changes nothing and that an unsigned assertion is refused;
   [`examples/broker_worker/`](../examples/broker_worker/README.md) proves that a redelivered item
   reuses its execution instead of repeating its effects. Both are asserted by
   `tests/integration/`, so a recipe that stops being true fails the suite.
6. **Make extensions visible without discovery.** The [plugin guide](plugins.md#the-catalogue) now has a
   catalogue section: what known extensions exist (none published yet), the four rules a plugin must
   follow, the package layout, and how to be listed. Discovery stays absent by decision
   ([ADR 0007](adr/0007-trusted-plugins.md)); visibility was the actual gap.

**Exit gate**

| Criterion | Evidence |
| --- | --- |
| Every poor fit has a recorded disposition | three ADRs and the positioning page; none is left as an unexplained absence |
| The database seam is proven, not asserted | `assert_provider_contract` passes for SQLite and fails for two broken providers |
| Capacity is a number, not a vibe | the write-throughput baseline in `tests/perf/`, quoted in two documents |
| The integrations that matter are tested code | `tests/integration/test_tenancy_example.py`, `tests/integration/test_broker_worker_example.py` |
| Core did not grow | no change to `src/xyberos/__init__.py`, the runtime, or the core dependency set; the one new public name lives in the `database` extra's testing module |

**Deliverables:** three ADRs, three documents (positioning, database providers, and the capacity
section), one reusable conformance suite, and two tested examples — all of it outside the runtime.

### Phase 9 - extras here, and the placement rule

**Status:** *implemented here, apart from the retirement patches.* Landed in this repository: **ADR 0018** (the placement rule),
**ADR 0019** (the storage contract), `xyberos.storage` with the shipped filesystem provider, the
in-memory double and `assert_storage_contract` (`tests/storage/`, 44 cases), request metrics as
`xyberos.http.RequestMetricsMiddleware` (`tests/http/test_metrics.py`), `xyberos.mcp` with its
streamable-HTTP client, tool projection and stub-server suite (`tests/mcp/`, 23 cases), and
`assert_model_provider_contract` with the embedding half in `xyberos.ai.testing`, run against the
shipped Ollama adapter in the opt-in live suite. Remaining: the **retirement patches**, which need an
upload to the package index rather than a change here, so they belong to the release that publishes
them. 2.0 already has every
mechanism a package needs — `register(app)` for
providers and routes, `Plugin` for a distribution the runtime validates, orders, and attributes, and the
provider registry for scopes, dependencies, and test overrides — so this phase adds no mechanism. The
capability-placement decision is recorded under "Adopted implementation decisions", so this phase applies it,
records it as **ADR 0018** in full, and ships the extras it sends here. Two limits bound what it may add. The
first is the middleware limit: a cross-cutting request concern is a class the application passes
(`HttpAdapter(app, middleware=(...))`), never a plugin, and never something a module installs behind the
application's back. The second is the configuration limit: configuration reaches a package as an explicit
factory argument or through a `Plugin`'s typed `[plugins.<name>]` section, never by widening `Settings` — which
is what stops "no new mechanism" from quietly becoming one.

**Objective:** ship the capability that belongs here, and stop shipping it anywhere else. A dependency-free
capability small enough for this repository's suite becomes an extra with one working implementation — the
shape `[http]`, `[database]`, `[ollama]`, and `[durable]` already have — and the 1.x name it replaces is
retired with a pointer rather than shimmed.

**Prerequisites:** Phases 0-8 complete, so the mechanisms are frozen, and the owner's decisions on the
placement rule ([ADR 0018](#remaining-owner-decisions)) and the reused names ([ADR 0022](#remaining-owner-decisions))
recorded. ADR numbers in this plan are indicative: the directory assigns them when an ADR is written, and
`docs/adr/README.md` is the truth about which number means what.

**The rule, applied per candidate.** The placements are the adopted decision's; this table is where each
candidate on the list lands, including the ones that are not packages at all. `here` is this repository,
`there` is the ecosystem repository. The kinds are the three the docs already use: a **module** registers
providers and routes inside an application, a **plugin**
is a distribution the runtime validates and attributes, and a **provider** or **adapter** implements one
extension-point contract.

| Candidate | Placement | Why |
| --- | --- | --- |
| MCP tools (consume a server's tools) | **module here**: `xyberos.mcp`, a streamable-HTTP client; the stdio transport belongs *there*, with the package | the 1.x client's own description says it speaks JSON-RPC over stdio and streamable HTTP using only the standard library — so no dependency, and the port re-proved that rather than assuming it: `xyberos.mcp` imports nothing outside the standard library, which makes it a module rather than an extra that would install nothing. HTTP-only here, because a stdio transport spawns a process: that collides with the standing policy that the framework starts nothing, and `asyncio` subprocess behaviour is platform-specific while CI has no non-Linux leg |
| Request metrics | **here, inside `[http]`**: a middleware class, no new extra | no dependency, and the smallest thing on this list; the application passes it to `HttpAdapter`, which is the only shape 2.0 offers for middleware. A separate extra is earned only if the capability grows a sink, an exporter, or a dependency: an extra costs a release row, a CI row, a tier entry, a feature-matrix row, and a catalogue row, and one class does not repay them |
| Storage (files and blobs) | **module here**: `xyberos.storage` with local files, a double, and the provider suite | no third-party dependency at all, and an extra that installs nothing is theatre: `pip install "xyberos[storage]"` would pull in no dependency and gate no import. `xyberos.ai` is the precedent — a dependency-free capability is a built-in module, not an empty extra (ADR 0018) |
| Storage (S3-compatible), PostgreSQL, MySQL | package there | each needs a client library core will not adopt; [ADR 0016](adr/0016-database-providers-are-an-extension-point.md) already places database engines there |
| Templates, static files, forms | package there: `xyberos-templates`, an engine-neutral `Templates` contract with Jinja2 as the shipped implementation | it needs Jinja2 **and** `python-multipart`, and `pyproject.toml` already records why neither is an extra of this package; the contract stays engine-neutral so a team that would rather write typed components satisfies the same protocol instead of forking the package |
| A logging preset and tracing | package there: `xyberos-observability` | it needs OpenTelemetry, and the runtime configures no handler by decision |
| Identity and authentication | package there: `xyberos-auth`, verification only | real assertions are asymmetric, so it needs `cryptography`; [ADR 0014](adr/0014-no-identity-or-authorization-model.md) still owns the policy half, and no flow, preset, session, or role returns |
| LLM providers | package there: `xyberos-openai-compatible`; the suite stays here | the adapter is a second backend for a facade whose first is [ADR 0004](adr/0004-initial-ai-provider.md)'s Ollama; promoting it to an extra would amend that ADR |
| Multi-tenancy | module, either home | it needs nothing new: `examples/tenancy/` already proves the pattern, so a package is a convenience rather than a capability |
| Parallel fan-out | module, here, as an example | the backlog defers any runtime claim, so it needs ADR 0021 and the owner's sign-off before it exists at all |
| A revived `xyberos-db` | **retire, with a pointer** | `xyberos[database]` and the provider seam already answer it |
| `xyberos-metrics` | **retire, with a pointer** | its capability ships as a middleware class in `xyberos.http` here, so a 2.x release under the old name would be a second answer |
| `xyberos-mcp` | **reused there, for the other direction** | the extra here carries the client and the package carries the server, so one name answers one question instead of two |
| `check --json`, `--why`, `--schema`, the configuration schema | tooling here | nothing installs them; they are one binary's flags — ADR 0020 records the serialized documents as a contract |
| Session inspection of the journal | tooling here | read-only, and retention, pruning, and scheduling stay deferred |
| Sessions and CSRF | **moved to here**: `xyberos.http.SessionMiddleware` and `xyberos.http.CSRFMiddleware`, over a `SessionStore` contract whose implementations are a package there | [ADR 0018](adr/0018-capability-placement-rule.md) refused them on the grounds that Starlette ships both, which is true for sessions and false for CSRF. [ADR 0024](adr/0024-sessions-and-csrf-are-middleware-in-the-http-module.md) records the reversal and the split: the mechanism is here and the store policy stays with the application |
| An admin UI, OpenAPI, RAG and vector stores, job queues, rate limiting, feature flags | refused, unchanged | reverse one and it needs its own ADR, which is what the backlog and the feature matrix record |

**One row reconciles two statements the plan made in different places.** `xyberos-mcp` was described as *reused
as a rewrite* in the owner's decisions and as *retired with a pointer* here, and its client appeared in both the
extra and the package. The directions are separable, and that is the resolution: **the module here is the
client; the package there is `expose()`**, plus a stdio transport if the owner approves one. One name answers
one question, the owner's decision section says the same thing in its own words, and ADR 0018 records it.

The client needs no extra at all, which is the correction the implementation made to an earlier draft of this
paragraph: a streamable-HTTP client over `urllib` has no third-party dependency, so it is `xyberos.mcp` in core
like `xyberos.ai`, not `xyberos[mcp]`. The placement rule decides it — a module when the capability needs
nothing from PyPI, an extra when it does — and an extra that installs nothing is theatre.

**Why the rule beats a shim.** The tempting alternative is to publish `xyberos-mcp` 1.0.0 as a thin package
that depends on core and re-exports `xyberos.mcp`. It saves nothing and costs something: 2.0's `xyberos.runtime`
and `xyberos.plugins` are unrelated to the 1.x ones, so the package's body is a rewrite either way; the import
root changes (`xyberos_mcp` to `xyberos.mcp`), so the shim preserves no import a 1.x user could rely on; and a
second distribution answering one question inherits this repository's release cadence as a version constraint.
Retirement with a pointer — or, where a name still has a direction of its own to carry, a rewrite with an honest
first line — is the honest form of the same move, and it is the move
[ADR 0017](adr/0017-release-identity-and-lineage.md) already made for the core name.

**Work packages**

1. **Record the rule: ADR 0018.** A new ADR — **ADR 0018**, the next free number and a deliverable here rather
   than a link that resolves today — states the three kinds, the four placements, the middleware limit above,
   and the four rules that keep the split safe: a package may depend on core while core may never depend on a
   package or on another package; an extra owns a path under `xyberos.*` and a package owns a top-level import
   root of its own; configuration reaches a package as an explicit factory argument or as a `Plugin`'s typed
   section, never by adding a root key to `Settings`; and one distribution answers one question. It also records
   the placement table's candidate rows as an import-path decision, because the extra's path is a promise of
   this package and cannot be undone in a later release. **Evidence:** the ADR, linked from `CONTRIBUTING.md`
   and the Extend pages.
2. **`xyberos.storage`, with an implementation and a suite (ADR 0019). — implemented.** `Storage` — `put`,
   `get`, `delete`, `list_keys`, an explicit key space, bounded sizes, and errors mapped onto the existing
   taxonomy — plus a local-filesystem provider, an in-memory double in `xyberos.storage.testing`, and
   `assert_storage_contract` for the providers that live elsewhere, in the shape
   `tests/database/test_provider_contract.py` already sets. Keys are the
   security boundary and are treated as one: `validate_key` refuses an absolute key, an empty or `.` or
   `..` segment, a backslash, a control character, and the reserved `.xyberos-` segment prefix, and the
   filesystem provider checks containment again on the *resolved* path so a symlink out of the root is a
   refusal rather than a write, and refuses Windows device names on every platform. It is a **module, not
   an extra**: it needs nothing from PyPI, and an extra that installs nothing is theatre. **Evidence:** the
   suite passing for the filesystem provider and the double, failing for two deliberately broken ones — a
   `delete` that reports removing what was never there and a `list_keys` that ignores its prefix — plus
   the traversal, symlink, device-name, and ceiling refusals, and the settings-object path proven through
   the registry.
3. **`xyberos.mcp`, the client. — implemented.** One `Tool` per server tool, projected into the shipped
   `xyberos.ai.tools` `Tool`/`ToolSet` and the existing allowlist rather than a parallel tool model,
   namespaced `{server}_{tool}`, with arguments *validated* against the declared schema through the closed
   subset rather than coerced, a schema outside the subset refused at registration with the server, the tool,
   and the keyword named, servers named in settings with their tools opted into by name, a server's
   descriptions and results treated as data, and a reachable-server failure reported rather than inferred.
   The transport is **streamable HTTP**: a stdio transport spawns a process, which collides with the standing
   policy that the framework starts nothing and whose behaviour is platform-specific in a suite that has only
   ever run on Linux. The client subset is `initialize`, `tools/list` with bounded pagination, and
   `tools/call`; prompts, resources, sampling, and server-initiated notifications are refused rather than
   half-implemented, and the handshake reports no capabilities rather than claiming ones that do not exist.
   The stdlib-only claim is **re-proved**: the client uses `urllib.request` in a worker thread through
   `asyncio.to_thread`, because the standard library has no asynchronous HTTP client — a documented cost of
   one thread per request rather than a hand-rolled HTTP/1.1. It needs nothing from PyPI, so it is a
   **module** (`xyberos.mcp`) and not an empty extra, for the same reason `xyberos.storage` is. Its failures
   are its own family in the taxonomy (`McpError`, `McpConfigurationError`, `McpProtocolError`, and
   `McpTransportError`, which is also a `TransientError`), because an unreachable server, a JSON-RPC error,
   and a wrong tool name are three different things a caller has to be able to tell apart. **Evidence:**
   `tests/mcp/` — 23 cases against a stub MCP server on a real socket, covering the handshake, a negotiated
   protocol mismatch, pagination, session-ID echo, an event-stream response, a non-JSON body, the schema
   refusal, the opt-out that keeps a server usable, argument validation happening *before* the call leaves
   the process, the server's own `isError` becoming a failed result, the allowlist denial, and the facade
   running a projected tool end to end through `chat_with_tools`.
4. **Request metrics, inside `[http]`. — implemented.** Counters per route and status as a middleware
   class the application passes to `HttpAdapter`, with a readout a test can assert and no sink, exporter,
   or background task. The counters are keyed by the adapter's matched-route template rather than by the raw
   path, and they are bounded the way the storage key space is: a request that matched no route is one key,
   and past `max_routes` the rest fold into `<other>`, so a client cannot choose how much memory the counter
   map uses. Because the middleware sits inside error normalization it counts a failure at the status the
   client receives. It is the smallest candidate on the list, so it does not earn a release row of its own: an extra
   costs a release row, a CI row, a tier entry, a feature-matrix row, and a catalogue row, and one class does
   not repay them. A separate `[metrics]` extra is the documented upgrade path if the capability later grows
   a sink or a dependency. **Evidence:** `tests/http/test_metrics.py` (eight cases, including the template
   keying, the `<unmatched>` fold, and that nothing is counted when the application does not pass the
   middleware), a line in the feature matrix, and no new extra row in the release guide.
5. **The AI provider conformance suite. — implemented.** `assert_model_provider_contract`, with
   `assert_embedding_provider_contract` beside it, in `xyberos.ai.testing` — where the fake provider already
   lives. Its customers are the adapter packages in the other repository and any third party; a provider
   proves a refusal is reported rather than inferred, usage is reported rather than guessed, the closed schema
   subset is honoured, tools are called, cancellation is obeyed, and — the property that makes it usable
   against a live model — every capability claim is checked from **both sides**, so a provider that claims
   nothing is checked for refusing rather than skipped, and one that overclaims fails. Writing it found a real
   gap: `FakeModelProvider.stream` did not refuse a model that does not claim streaming, while the shipped
   Ollama adapter did, and the fake now matches. **Evidence:** `tests/ai/test_model_provider_contract.py`
   (eight cases, including two deliberately broken providers) and the opt-in live run against the shipped
   Ollama adapter in `tests/ai/test_live_ollama.py`.
6. **Retirement as a mechanism, not a sentiment.** For each name whose capability lands in an extra or in a
   class an extra ships, the 1.x line gets a metadata-only patch — `0.1.3`, `0.2.3`, and so on — whose
   description points at the replacement and which keeps the `xyberos>=1.0,<2` pin, so nothing moves under a 1.x
   user. `xyberos-metrics` points at `xyberos[http]`; `xyberos-db` points at `xyberos[database]`. No shim, no 2.x
   release under a retired name, and the pointer release is the same window the repin already used. A name is
   patched only where the patch reaches somebody: a satellite with no users is left alone, and that is recorded
   as a decision rather than left as an omission. **Evidence:** the patch release, and the catalogue row that
   records either the retirement or the decision not to patch.
7. **Book the cost of an extra once, in one place.** Each new extra adds one import-boundary case, its
   dependency to `PACKAGE_EXTRAS` when it has one, one `optional-installation` CI row, one release-guide row, one
   feature-matrix row, and the three registrations a new page needs (`mkdocs.yml`, `site/scripts/reference.py`,
   and the page). The CI shape stays bounded — core, each extra alone, and one job with every extra installed
   together — rather than exhaustive, and the all-extras leg asserts what the single-extra legs cannot: that no
   extra imports another extra's third-party dependency. The platform leg is the same kind of decision: one
   non-Linux job for the extras whose behaviour is platform-sensitive (`[database]`, `[durable]`, and anything
   that starts a process), because SQLite's WAL and file locking are where a 2.0.x bug report would come from.
   **Evidence:** `tests/test_import_boundary.py` and `tests/test_optional_dependencies.py` growing by exactly one
   case per extra, the matrix rows, and the release-guide row.

**Exit gate**

| Criterion | Evidence |
| --- | --- |
| The rule is written once and applied per candidate | ADR 0018, and a catalogue row for every candidate in the table above |
| Every extension point that ships here has a working implementation | `xyberos.storage` has a filesystem provider, `xyberos.mcp` has a client that passes its stub-server suite, request metrics has a class, and the AI suite runs against the shipped Ollama adapter |
| Every extension point that a package implements has a suite | storage, MCP, AI, and the database's, each run against deliberately broken or failing implementations so the suite is evidence rather than decoration |
| A capability can be configured without widening `Settings` | `FilesystemStorageSettings` plus `filesystem_storage(...)` is proven through the registry in `tests/storage/test_filesystem.py`, `McpServerSettings` carries a server and its opt-in, and `config.py` accepts no new root key |
| Each import path is decided before its code | ADR 0018's table names the path for every candidate — `xyberos.storage`, `xyberos.mcp`, and `xyberos.http` are promises of this package — and `tests/test_public_surface.py` records them |
| Every placement is booked once | a feature-matrix row, a stability row, a reference page, and a boundary case per capability — and no new extra row, because neither storage nor MCP nor metrics is an extra |
| A retired name points somewhere and moves nobody | *not yet: the pointer patches need an upload to the package index, and belong to the release that publishes them* |
| The mechanism 2.0 already has is enough | no change to `src/xyberos/__init__.py`, to the root keys `config.py` accepts, to the plugin protocol, to the provider registry, or to the routing API; the new names live in `xyberos.storage`, `xyberos.http`, `xyberos.ai.testing`, and the `xyberos.errors` taxonomy |
| The middleware limit is respected | metrics is a class the application passes, and nothing pretends a plugin can install middleware |

**Deliverables:** two ADRs (0018 and 0019), two new modules (`xyberos.storage` and `xyberos.mcp`) plus one
middleware class that ships inside `[http]`, three conformance suites and their doubles, and the catalogue,
feature-matrix, stability, plugin, and release documentation each one changes. The retirement patches for
the names that have somebody to tell remain **outstanding**, and they are an upload rather than a change
here.

### Phase 10 - the packages that stay in the ecosystem repository

**Status:** *implemented here; the ecosystem half is written there and unpublished.* The **ecosystem half** —
the packages, the ports, the retirement patches — is source in
[`xyberos/xyberos-plugins`](https://github.com/xyberos/xyberos-plugins), and nothing here can publish it. All
eight distributions are released — how to use each one is
[the packages guide](../site/extend/packages.md) — and each passes its own gates: its suite, a strict type
check, and a build that carries `py.typed`. The three that implement a seam this repository ships a suite for
pass that suite against a real service, which is a PostgreSQL server, an S3-compatible server, and a stub
OpenAI-compatible endpoint. They needed the core's `2.1.0` rather than `2.0.0`, because the modules and error
types they import landed after `2.0.0` was uploaded. Every one of them is `published` in the manifest, so the
compatibility job installs nine distributions from the index and runs each one's declared check — the first
time that job has done anything but skip. Landed
in this repository:
[`packages.toml`](../packages.toml) as the manifest of every name beside this line, with
`tests/test_packages_manifest.py` (15 cases) checking the plugin guide's catalogue, the feature matrix, and
the release guide against it and enforcing ADR 0018's import-root rule; [`tools/ecosystem.py`](../tools/ecosystem.py)
as the tested selector the job reads; the [compatibility workflow](../.github/workflows/compatibility.yml),
which installs the **published** core from the index, scaffolds against it, and grows one conformance leg per
published package; and the per-name wording in [the release guide](release.md#releasing-beside-the-published-1x-line).
Two honest limits are recorded rather than hidden: a GitHub Actions matrix cannot be empty, so the package
legs are *gated* and the manifest job announces the empty list in an annotation instead of passing in
silence; and the manifest lives here rather than in the ecosystem repository, because the documents checked
against it are here. Almost all of the rest is work in
[`xyberos/xyberos-plugins`](https://github.com/xyberos/xyberos-plugins), the ecosystem repository, so each work
package names both halves: what happens *there*, and what has to change *here* — usually a catalogue row and a
link, never a copied file. Its name, URL, and owner are settled in
[ADR 0022](adr/0022-ecosystem-repository-and-satellite-names.md).

**Objective:** keep this repository's dependency graph and promise count small, and give the ecosystem one
home. A capability that needs Jinja2, OpenTelemetry, `cryptography`, a database driver, or an object-store
client is a package with its own release — not an extra that quietly makes this line depend on all of them.

**Prerequisites:** Phase 9's ADR 0018, because the rule decides what lands here; the conformance suites,
because a provider package in this phase is proved against them; and the publication decision above, because it
is what decides the repository, the publisher, and each name before the first upload rather than during it.

**Work packages**

1. **The publication mechanics, decided once for every name.** *There:* one directory per subject and one per
   distribution inside it, each distribution with its own `pyproject.toml`, version, and changelog; discovery
   of the distribution directories, because a workflow that enumerates them by hand cannot see one that was
   added; the `packages.toml` manifest described under
   ["Where the ecosystem lives"](#where-the-ecosystem-lives-and-under-which-names), consumed from this
   repository rather than re-listed; one CI matrix that builds,
   tests, and lints every distribution and installs the **published** core rather than a checkout; a trusted
   publisher registered per distribution against whichever repository became the ecosystem home, once, before
   the first upload; a tag scheme one level deeper than the one in service — `vX.Y.Z` publishes every
   distribution, and `<subject>/<distribution>/vX.Y.Z` publishes one; the `project_urls` the satellites have never
   declared, Documentation first; a changelog whose first line states the break; and the pointer patches for
   retired names released from the same repository so that one place owns every `xyberos-*` name. *Here:* the
   catalogue rows, checked against the manifest rather than maintained beside it, and the release guide's
   per-name wording. **Evidence:** the first release, the manifest agreeing with the catalogue and the index,
   and the compatibility job passing against published artefacts. **Landed here:** the manifest, the checked
   catalogue, the feature-matrix placement, the per-name release-guide wording, and the compatibility job's
   core leg.
2. **`xyberos-mcp`, the server direction, and the stdio transport if the owner approves it.** *There:* the
   `expose()` direction and a stdio transport — the two things the core client `xyberos.mcp` refuses — and
   nothing that
   duplicates the client, because two names answering one question is what the placement rule exists to prevent.
   The authorization gap is stated rather than closed: [ADR 0014](adr/0014-no-identity-or-authorization-model.md)
   leaves the framework no model to put in front of an RPC surface, so the package says that the caller brings
   one. *Here:* a catalogue row that names which direction this name carries, and a recipe for the application
   that wants to expose its own tools. **Evidence:** the package's suite against a stub server, the recipe, and
   a negative test that the package exports no client.
3. **`xyberos-templates`.** *There:* an engine-neutral `Templates` contract — render a named template with a
   context, a static mount, and form reading — with Jinja2 as the one **shipped** implementation, declared
   alongside `python-multipart`, because `request.form()` raises without it; that library already sits in the
   `dev` extra for exactly that reason. The contract is engine-neutral for the same reason `DatabaseProvider`
   is: the seam is reusable, one implementation ships, and a team that would rather write typed components
   satisfies the same protocol instead of forking the package. Two properties are the package's reason to
   exist, because `starlette.templating.Jinja2Templates` provides neither:
   - **Rendering stays off the event loop.** Starlette's `TemplateResponse` renders synchronously inside
     `__init__`, so the whole cost lands on the loop. The package renders through
     `anyio.to_thread.run_sync(template.render, ...)` for CPU-bound work, and uses Jinja2's
     `enable_async=True` with `await render_async(...)` when a template itself awaits — and it documents the
     difference, because `render_async` yields but does not reduce CPU time.
   - **Autoescape is stated, not inherited.** `select_autoescape()` decides by file extension, so a page named
     `page.j2` would silently be unescaped. The package sets and documents its policy, and a test renders both
     the escaped and the explicitly-safe case.
   It owns its own import root, and takes its directory as an explicit settings object or a plugin section
   rather than from a new core key. *Here:* a catalogue row, and the traditional path's lessons keep teaching
   the shape it packages, minus the wiring the package replaces. **Evidence:** the package's tests, including
   the escaping pair, a render that does not stall a concurrent request, and the lesson cross-reference.
   **The placement test, applied before it is published:** this package earns a *distribution* only if it owns
   the off-loop renderer and the engine-neutral contract. If it reduces to a wrapper over `Jinja2Templates`,
   the rule's own cost test applies — the one that put request metrics inside `[http]` — and it ships as a
   **recipe** in the `examples/<name>/` plus integration-test pattern the tenancy example already uses.
4. **`xyberos-observability`.** *There:* one explicit call from the composition root that configures a handler,
   a level, a format, and the runtime's own `ContextLogFilter`; workflow and step spans from an `EventSink`
   subscription rather than from patching internals; and request spans keyed by the correlation id the adapter
   already mints. Its settings arrive as an explicit dataclass or through a `Plugin`'s `config_type`, and its
   import root is its own, never a path inside `xyberos.*`. *Here:* a catalogue row and a link from
   [the observability page](../site/production/observability.md). **Evidence:** the package's tests, including
   one that configuring a handler through it still redacts a field the runtime classifies as a secret.
5. **`xyberos-auth`.** *There:* keep the verification half — an assertion from a shared secret or a JWKS, a
   `Principal`, and stop — and drop the OAuth2 flows, the OIDC machinery, and the Auth0/Okta/Entra presets its
   published `0.1.2` bundles, with the changelog's first line saying what no longer happens. It owns its own
   import root, takes its key material from the environment or an explicit settings object rather than from
   committed configuration, and still registers nothing: [ADR 0014](adr/0014-no-identity-or-authorization-model.md)
   owns the policy half, so the package verifies an assertion and the application decides what it means.
   *Here:* the catalogue row, and the feature matrix's identity row still reading "Not provided, and it will
   not be". **Evidence:** the package's tests refusing an unsigned, an expired, and a wrong-audience assertion.
6. **The engine and adapter packages: `xyberos-postgres`, `xyberos-storage-s3`, and the AI adapters.**
   *There:* each runs the conformance suite that ships here, declares the extra or core it needs, is proved
   against the installed core, and tests its own declared floor as well as the newest published core. The
   PostgreSQL package also answers the two SQLite-specific promises the provider guide names, or refuses
   loudly; the storage package runs `assert_storage_contract`; each AI adapter runs
   `assert_model_provider_contract`. Each owns its own import root and takes its configuration as an explicit
   settings object plus a factory. *Here:* catalogue rows, and the provider guide's section on running a suite
   from another repository. **Evidence:** each package's CI, the PostgreSQL job against a service container, and
   the compatibility job below.
7. **Catch drift with a job, not a hope. — landed here.** A scheduled CI job — and a required one before a
   core release is tagged, and before a package release is tagged *there*, which an earlier draft left out —
   installs the published core and the published packages from the index into one environment and then runs
   each package's **conformance suite** rather than a smoke test. Version drift is the
   failure mode this arrangement invites, and this is the only place it can be caught, because neither
   repository owns the other's code. Two design decisions are worth recording because the first is a real
   constraint rather than a preference: a GitHub Actions matrix **cannot be empty**, so the package legs are
   gated on the manifest's published list and the empty case is announced in an annotation rather than
   passing in silence; and the job installs from the **index**, not from a checkout or a local wheel, because
   the `installed-artefact` job in `ci.yml` already covers the artefact this repository just built, and the
   one failure it cannot catch is a bad upload. The core leg therefore earns its keep today, before any
   package exists. **Evidence:** `.github/workflows/compatibility.yml` and
   `tests/test_packages_manifest.py`, which parses the workflow and asserts the gate, the manifest-derived
   matrix, the conformance call, and that nothing in the core leg installs a local build.

**Exit gate**

| Criterion | Evidence |
| --- | --- |
| Only the rule's cases land there | every package in this phase needs a dependency this line does not adopt, carries policy, or has its own cadence; Jinja2, OpenTelemetry, and `cryptography` are named with the reason |
| A ported name is a rewrite with an honest first line | it declares `xyberos>=2,<3`, the old version stays published and unedited, and the changelog says what changed |
| Compatibility is proved against what a user can install | every package's CI installs the published core and tests its own declared floor, and the compatibility job here runs the conformance suites against published artefacts |
| A retired name points somewhere, and a reused name is not a second answer | `xyberos-db` points at `xyberos[database]` with a pointer and an unchanged pin, `xyberos-metrics` at `xyberos.http` with no release to point from, and `xyberos-mcp` carries the server direction and exports no client |
| One repository publishes each name | no package release originates here, and the catalogue says where each one does |
| The names are claimed before the code is written | a pre-release placeholder holds every decided name, and no placeholder is a normal release |
| Trusted publishing is re-registered once, not once per release | the publisher list matches the ecosystem repository, and the first upload's provenance appears in the release guide |
| Nothing in the ecosystem reaches back into core | no `[project.dependencies]` or extra entry here names a package, and the compatibility job is the only place the pair is proved |
| A package release cannot be tagged on a red compatibility job | the job's matrix comes from the manifest, so a package marked `published` without a conformance target is refused before it is installed |
| A name is published only when a check this repository can run proves it | every published name declares a conformance target of one of the two documented shapes: the shipped suite for the three packages that implement a seam, or a self-check that imports the package's public names against the core it declares for the four that do not |
| The job installs what a user can install | the matrix is the manifest's published list, so the first release turned the package legs from skipped to running without a change to the workflow |
| The 1.x line's names are tracked in one place | `packages.toml` plus `tests/test_packages_manifest.py`, which keeps the catalogue, the feature matrix, and the release guide in step with it |
| A package that would only wrap something is a recipe | `xyberos-templates` is published only if it owns the off-loop renderer and the engine-neutral contract; otherwise the catalogue row points at the recipe, and either form is a decision rather than a default |

**Deliverables:** the packages, the ports, and the retirement patches in the ecosystem repository, with
`packages.toml` as the manifest that names them; here, the catalogue rows checked against that manifest, the
Extend-page links, the per-name wording in
[the release guide](release.md#releasing-beside-the-published-1x-line), and
[ADR 0022](adr/0022-ecosystem-repository-and-satellite-names.md) — which records the reused
names, the ecosystem repository, the five conditions, and supersedes that clause of
[ADR 0017](adr/0017-release-identity-and-lineage.md).

### Phase 11 - developer tooling and the contributor loop

**Status:** *implemented here.* Landed in this repository: **ADR 0020** (the introspection documents as
a versioned contract), `check --json` / `--why CONTRACT` / `--schema` with `DOCUMENT_VERSION = 1` and
the shipped `config.schema.json` (`tests/cli/test_introspection.py`, `tests/test_config_schema.py`,
`tests/test_compatibility.py`), the published copy at the `$id` the schema names
(`site/scripts/build.py`, checked by `tests/site/test_pages.py`); `xyberos durable status` with its
`--json` form, reading the journal through SQLite's `mode=ro` and never migrating it
(`tests/cli/test_durable_status.py`, `tests/durable/test_journal.py`); the contributor loop as three
files — [`.devcontainer/devcontainer.json`](../.devcontainer/devcontainer.json),
[`.pre-commit-config.yaml`](../.pre-commit-config.yaml), and the ordered loop in
[CONTRIBUTING.md](../CONTRIBUTING.md) — kept in agreement by `tests/test_contributor_loop.py`; and
`tests/integration/test_first_five_minutes.py`, which scaffolds a project, runs the two commands the
scaffold prints that need no install, and compares the block with the getting started guide. The one
thing not done as written is running the scaffold's own `pip install -e`, which installs into the
interpreter running the suite; the test asserts that command and runs the two after it, which establish
the property it would have.

**Objective:** make the framework legible to the tools a developer already has — an editor, a script, a CI
job — and make this repository's own loop reproducible by somebody who is not its author.

**Prerequisites:** none beyond Phases 0-8. Nothing here depends on Phases 9 and 10, which is why the three
phases of this plan may be delivered in any order; the one hard ordering is inside Phase 9, where a
conformance suite lands with its contract and before any implementation claims to pass it.

**Work packages**

1. **Introspection an editor and a script can consume.** `xyberos check` grows three outputs: `--json` emits
   settings, the provider graph with scopes, the route table, the plugin list, and the diagnostics as one
   machine-readable document; `--why Contract` prints the resolution path and scope for one contract, which is
   the sentence `App.validate()` already builds for a failure; and `--schema` emits the JSON Schema generated
   from the `Settings` dataclasses, which also ships in the wheel and is served from a stable URL on the site, so
   an editor validates and completes `xyberos.toml` with no extension to install. Two rules keep the outputs
   from becoming a second source of truth: `--json` reports a missing extra through
   `xyberos._extras.suggest_extra` and plugin state through `PluginInfo`, so the command and the runtime cannot
   give different answers to "which extra do I need" and "why is my plugin not loaded"; and `--schema` covers
   `schema_version`, `app`, and **each declared plugin's `config_type` section**, so a plugin author gets
   completion for `[plugins.<name>]` as well — while the opaque `[ai.<name>]` channel stays out of the schema,
   because core does not know its keys and a schema that guessed would be worse than none. **ADR 0020** records
   the serialized documents as a versioned contract, because a JSON key a tool reads is as public as a name, so
   `tests/test_compatibility.py` pins their keys and a drift test fails when a `Settings` field changes without
   the schema. **Evidence:** the new cases in `tests/cli/test_cli.py`, `tests/test_config_schema.py`, and the
   compatibility entry.
2. **One read-only command for the experimental surface: `xyberos durable status`.** Counts by state, the
   oldest non-terminal execution, the parked attempts with the reason each was parked, the journal's schema
   version, and its file size — read through `JournalStats`, `list_executions`, and `inspect`, which
   `xyberos.durable` already exposes, opening the journal read-only, and with `--json` for the same reason
   `check` has it. It never writes, never prunes, and never schedules, and its help says so rather than leaving
   that to the guide. Two behaviours belong to the contract rather than to the implementation: without the extra
   it fails with the `xyberos[durable]` command to install, exactly as the `installed-artefact` job asserts for
   `check`; and a journal written by a newer build is reported as the refusal the journal itself raises, not as a
   traceback. **What "read-only" cost.** Opening read-only needed three small additions rather than a promise:
   `SqliteSettings.read_only` (which opens the file through SQLite's `mode=ro` URI and installs no header
   pragma), `JournalSettings.read_only` (which checks the recorded schema version and refuses a newer one
   instead of migrating), and `JournalStore.oldest_non_terminal()`, because the longest wait is a query the
   existing readers could not answer — `list_executions` is newest-first. SQLite still creates an empty `-wal`
   and a `-shm` index beside a WAL database it opens, so "writes nothing" is stated as what it is: the
   journal's bytes are unchanged, and a test compares them. **Evidence:** `tests/cli/test_durable_status.py`
   (which includes the byte comparison, the refusal, the missing file, and a blocked-`sqlalchemy` subprocess),
   `tests/durable/test_journal.py`, the operator section in [the durable guide](durable.md), and the subcommand
   list in [the CLI guide](cli.md).
3. **The contributor loop, reproducible.** `.devcontainer/devcontainer.json` installs the extras CI installs,
   `.pre-commit-config.yaml` runs the two `ruff` commands **pinned to the same version range the `dev` extra
   declares**, so the hook and CI cannot disagree about a rule, `pre-commit` joins the `dev` extra, and
   CONTRIBUTING gains the ordered loop CI runs, with a test that the commands CONTRIBUTING lists and the
   commands the workflow runs are the same list. `.vscode/` is in `.gitignore`, so editor settings arrive by
   that negation or not at all — here through the container's own `customizations`, which is why the committed
   file is the devcontainer rather than a `.vscode/`. **Evidence:** `tests/test_contributor_loop.py`, which
   compares the two lists in order, asserts the loop's ordering (the site build precedes the tests), and keeps
   the hook's revision inside the declared range.
4. **A DX claim that is a test.** `tests/integration/test_first_five_minutes.py`: scaffold with `xyberos new`
   in a temporary directory, take the `next:` block the command prints — today a `cd`, an editable install,
   `pytest`, and `xyberos check`, so the harness performs the `cd` itself and runs the three that follow — and
   assert that each one succeeds and that the block names the same commands the getting-started page shows, so
   the scaffold and the guide cannot drift apart. That is how "five minutes to a running application" becomes a
   suite entry instead of a sentence. **One deliberate substitution:** the editable install writes into the
   interpreter running the suite, so the test asserts that command and runs the two after it, which establish
   the property the install would have; the getting-started block gained the `xyberos check` line the scaffold
   prints, so the two blocks are compared as equals rather than as one being a subset.

**Exit gate**

| Criterion | Evidence |
| --- | --- |
| What an editor validates is what the runtime reads | the schema ships in the wheel (`src/xyberos/config.schema.json`), `check --schema` regenerates it, `--app` types each declared plugin's section, `site/scripts/build.py` publishes it at the `$id` it names, and `tests/test_config_schema.py` + `tests/site/test_pages.py` fail on drift rather than a user |
| The introspection documents are contracts | ADR 0020 plus `tests/test_compatibility.py` (version and top-level keys, and the two information records) and `tests/cli/test_introspection.py` (nested shape, and that text and JSON describe one application) |
| The command and the runtime cannot disagree | `check --json` uses `suggest_extra` and `PluginInfo`, so a missing extra and a plugin's state have one answer, not two; `durable status` formats `JournalStore`'s own readers rather than re-querying |
| The experimental surface can be inspected without hand-written SQL | `durable status` opens the journal with `mode=ro`, never migrates it, refuses a newer journal, never creates a missing one, and a test compares the file's bytes before and after |
| A stranger can reproduce the loop | the devcontainer installs what CI installs, pre-commit runs what CI runs at the same `ruff` range, CONTRIBUTING gives the order, and `tests/test_contributor_loop.py` compares all three with the workflow |
| Five minutes is measured | `tests/integration/test_first_five_minutes.py` runs the scaffold's own printed commands and compares the block with the getting-started page |

**Deliverables:** one ADR (0020), three new `check` outputs (`--json`, `--why`, `--schema`) and one read-only
command with its `--json` form (`durable status`), the configuration and plugin-section schema including the
copy the site publishes, three files for the contributor loop (the devcontainer, the hook configuration, and
the ordered loop in CONTRIBUTING), the first-five-minutes suite entry, and the CLI and README documentation
they change.

**Consequences these three phases own.** The ripples are part of the work rather than something a failing
build discovers: [the CLI guide](cli.md) and the README's command block gain the new flags and the `durable`
command, while `PLAN.md` section 9's "four subcommands" note gains a pointer rather than being rewritten,
because it records Phase 7; the `installed-artefact` CI job gains a core-only leg asserting that
`xyberos durable status` names the `durable` extra, and keeps its `routes: 2 (handler signatures valid)`
assertion, which the route report it greps for did not change; a new guide under `docs/` means three registrations, not one —
`mkdocs.yml`'s Reference list, `site/scripts/reference.py`'s `_SUMMARIES`, and the file — with `tests/site`
failing when one is missed; and the wheel gains one data file and no import, which
`tests/test_release_artefacts.py` states rather than trusts. Three more follow from the placement rule. An
extra is a promise the release makes, so [the release guide](release.md) gains a row per new extra and the
version bump touches more than six files; [the release guide](release.md#releasing-beside-the-published-1x-line)'s
repin instruction becomes per-name rather than blanket, since retiring a name costs a metadata-only patch; and
the plugin guide's catalogue stops describing extensions as hypothetical and starts naming a repository that is
not this one. The site's snippet harness still reads this repository only, so a page about a *package* is a
link and a contract description rather than a page that runs its code — and the page says which it is, while a
page about an extra keeps the stronger guarantee because the extra is tested here. And the templates decision
lands in [positioning.md](positioning.md) rather than in a package README: the "you need X, reach for Y" table
gains the row that says which renderer each case wants — Jinja2 for pages a non-Python contributor edits, a
typed-component builder for markup that has to survive `mypy --strict`, and nothing at all for an application
that serves JSON — so the one genuinely contested choice in the traditional path is answered by the page that
decides fit.

Three more follow from the publication decision, and each is a correction rather than an addition.
[The release guide](release.md#releasing-beside-the-published-1x-line) still records the satellites'
pre-repin state — `xyberos>=1.0`, unpatched — while the three names it discusses have already shipped a
`xyberos>=1.0,<2` repin; the per-name wording has to state the version each name is actually at, or the guide
describes a repository that no longer exists. [The plugin guide](plugins.md#the-catalogue)'s catalogue becomes
generated-and-checked against this repository's [`packages.toml`](../packages.toml), where the manifest lives,
rather than maintained by hand beside it, which is the same move the navigation and the reference pages already
made. And
[the feature matrix](../site/feature-support.md) gains a row per new extra and per package, naming the import
path each one owns in its `Import path or tool` column — which is the column that makes the import-root rule
visible to a reader who never opens an ADR.

**What these phases will not do**, each carried forward with its reason:

- **No shim packages.** A 2.x release under a 1.x name exists only where the port is a rewrite with something
  to keep; where the capability moved into an extra, the name is retired with a pointer instead.
- **No new mechanism.** `register(app)`, `Plugin`, the provider registry, and extras already cover every
  candidate; a new protocol needs a candidate that none of them fits, and nothing on the list qualifies.
- **No plugin-registered middleware.** `HttpAdapter(app, middleware=(...))` is the application's call, so
  metrics, tracing, and logging presets are classes the application passes — never something installed for it.
- **No dependency added to core or to an existing extra.** Jinja2, OpenTelemetry, `cryptography`, database
  drivers, and object-store clients each belong to the package that needs them.
- **No discovery and no entry points.** [ADR 0007](adr/0007-trusted-plugins.md) is a supply-chain decision; a
  hand-maintained catalogue is the visibility that was actually missing.
- **No pytest plugin and no fixture library.** [The testing guide](testing.md) refuses it, and the doubles
  stay ordinary functions.
- **No template engine in the package, and no engine named in the contract.** The engine belongs to the
  application and to `xyberos-templates`, which is what keeps the comment in `pyproject.toml` true, and the
  contract names no engine, so a team that renders typed components is not opting out of the seam.
- **No identity, session, or authorization model in the framework.** `xyberos-auth` verifies an assertion and
  stops; reversing [ADR 0014](adr/0014-no-identity-or-authorization-model.md) would take an owner decision and
  its own ADR.
- **No revived `xyberos-db`.** Its published version stays and gains a pointer, because two answers to "how do
  I talk to a database" is one answer too many.
- **No blanket reuse of the 1.x satellite names.** The rest stay on the 1.x line under the repin they already
  shipped, until each passes the owner's five conditions.
- **No DAG, no scheduler, and no parallel step execution in the engine.** The fan-out module is an example,
  opt-in, signed off by the owner, and scoped to one step's attempt.
- **No retention, pruning, or scheduling in the durable surface.** `durable status` reads and reports, and the
  deferred backlog item stays deferred.
- **No new stable name.** Everything here is preview, and promoting any of it needs its own ADR.
- **No name revived without a customer, and no new name for a capability that already has one.** A retired name
  is patched only where the patch reaches somebody, the satellites with no candidate stay on the 1.x line
  untouched, and a capability with an answer does not get a second distribution.
- **No package owning a path inside `xyberos.*`.** Two distributions sharing `xyberos/` makes a partial install
  a half-existing directory and an uninstall a stale one, and it disarms the boundary tests. An extra's
  `xyberos.<name>` path is this package's promise, so it is chosen with the placement or not at all.
- **No widening of `Settings` for a package's benefit.** A package takes configuration as an explicit factory
  argument, or ships a `Plugin` to get a typed `[plugins.<name>]` section. The `extra = "allow"` root namespace
  stays unused until a candidate cannot be expressed either way.
- **No extra that one class does not pay for.** An extra costs a release row, a CI row, a tier entry, a
  feature-matrix row, and a catalogue row, so request metrics ships as a class inside `[http]` and a separate
  `[metrics]` extra is an upgrade path rather than a plan.

## Cross-phase controls

### Dependency and import boundaries

```text
core runtime/config/registry
        |
        +-- HTTP adapter -- SQLite application provider
        |
        +-- plugin protocol
        |
        +-- Workflow
        |
        +-- AI facade (core, no SDK) -- AI adapters (optional)
        |
        +-- durable executor (optional, separate journal)
```

Dependencies point downward in this diagram, and optional pieces hang off the core rather than off
each other. The runtime cannot import HTTP, AI, or durable modules; `xyberos.ai` imports neither a
vendor adapter nor `xyberos.execution`, so an AI call is usable with or without a workflow around it;
Workflow cannot import a particular AI SDK; and the durable executor consumes stable Workflow
definition contracts without replacing the in-process executor for ordinary work. The one dependency
between optional packages is deliberate and narrow: `xyberos.durable` imports the SQLite connection
plumbing in `xyberos.database.sqlite` for PRAGMAs, WAL, and the bounded retry on write contention,
while keeping its own file, schema, and tables. Building a second copy of that plumbing was rejected
as the larger risk.

The boundary now has an outside, and the capability-placement decision gives it two shapes with different
rules. An **extra** is this package's own surface: it lives under `src/xyberos/`, may import an optional
dependency only inside its own module through `src/xyberos/_extras.py`, and is released, tested, and promised
with everything else here. A **package** in the ecosystem repository is not: it may import documented
`xyberos` names and nothing else, exactly as a plugin may, and this repository may never import it, list it in
`[project.dependencies]` or in an extra, or prove it by running its code — the compatibility job in Phase 9 is
where the published pair is proved instead. That asymmetry is the reason an extra must ship a working
implementation while a package may ship only what its own suite can carry: the first is a promise made here,
and the second is a promise made there and checked here.

### Definition of phase completion

A phase is complete only when its documented public API, tests, examples, operational constraints, and exit gate are present. A demo, passing happy-path test, or unreviewed internal module is not completion. New work discovered during a phase belongs in one of three places: required to satisfy the accepted exit gate, a documented later-phase dependency, or the deferred backlog.

### Delivery cadence

At the end of each phase, conduct a short design and operational review: confirm import boundaries, run the phase exit suite from a clean environment, update ADRs/docs, walk the ADR consequence lists and confirm each item is satisfied, owned by a named phase, or in the deferred backlog, review public error messages and redaction, and decide whether the next public contract is ready to freeze. This makes the 10-18+ week estimate in `PLAN.md` measurable rather than calendar-only.

## First implementation contracts

These are the target shapes for the public API. Every one is implemented and executed by a contract
test rather than only documented: the runtime portion by
`tests/contracts/examples/phase1_minimal_app.py`, the routed handler by
`tests/contracts/examples/phase2_http_app.py`, and the Workflow builder by
`tests/contracts/examples/phase4_workflow.py`.

```python
from typing import Annotated
from xyberos import App, Inject

app = App()
app.provide(UserService, factory=UserService, scope="app")

@app.get("/users")
async def list_users(users: Annotated[UserService, Inject()]) -> list[User]:
    return await users.list_users()
```

`provide` should reject ambiguous registrations. `Inject()` is required for handler injection; the type annotation identifies the contract. Runtime validation reports a path such as `UserService -> DatabaseProvider` when resolution fails. Test overrides are scoped to an app or test context and must never mutate another `App` instance.

```python
workflow = (
    Workflow("support", version="1")
    .step("retrieve", retrieve_documents, retry=Retry(max_attempts=3))
    .step("answer", generate_answer, timeout=seconds(30))
    .edge("retrieve", "answer")
)
result = await workflow.run(input=request_data, timeout=seconds(45))
```

The initial Workflow state is an explicit input/result mapping, not mutable ambient state. Step functions receive only their declared input and an execution context containing cancellation/deadline/tracing facilities. Workflow definitions and policies are immutable after validation.

Two clarifications the implementation made explicit, both recorded in
[ADR 0009](adr/0009-workflow-engine-contract.md): public policies take *durations* while the
execution context exposes the derived absolute deadline, and a step's `timeout` bounds one attempt
rather than the whole step, so a retried step gets a fresh timeout each time.

## Durable executor state and storage requirements

Implement and test the transition table before writing a worker loop. At minimum, terminal states are `COMPLETED`, `FAILED`, `CANCELLED`, and `TIMED_OUT`; non-terminal states are `PENDING`, `RUNNING`, `RETRYING`, and `WAITING`. Every transition records event sequence, timestamp, reason, worker/lease identity when relevant, and a schema version.

Use a journal database such as `xyberos_journal.db`, distinct from `app.db`. On initialization, apply migrations and configure WAL, a bounded busy timeout, and a documented synchronous setting. Perform claims with a single conditional transaction; retain a lease token and require it in every completion, retry, heartbeat, and cancellation-sensitive update. Store payload/result references with size limits and redaction rules rather than unbounded sensitive JSON.

Recovery must be intentionally at-least-once for activities unless an activity provides idempotency/reconciliation. Each activity contract must state its idempotency key or its recovery policy. A restart test must cover crash-before-start, crash-after-result-persisted, crash-during-activity, expired lease, and cancellation race.

## Test and quality strategy

| Layer | Mandatory checks |
| --- | --- |
| Unit | Dependency graph/scopes, lifecycle order, config precedence, graph validation, policies, state transitions. |
| Integration | ASGI lifespan/routes, SQLite transactions and write contention, plugins, Workflow cancellation and timeouts, optional extras. |
| Fault injection | Provider startup failure, transaction lock/error, Workflow step failure, stale lease, controlled worker termination. |
| Packaging | Build wheel/sdist, clean install of core and each extra, public-import audit, supported Python matrix. |
| Static quality | Formatting, linting, strict type checking for public contracts, dependency audit, and documentation example tests. |

Use a monotonic clock abstraction for Workflow and durability tests. Avoid sleep-based timing assertions. Use a real temporary SQLite file, rather than only in-memory SQLite, for WAL, locking, migration, and restart coverage.

## Backlog deliberately deferred

- Distributed workers, multi-host coordination, and HA scheduling.
- Exactly-once effects, transparent replay, and arbitrary workflow code recovery.
- A custom ORM, migration engine, task queue, or plugin sandbox.
- Automatic plugin discovery, arbitrary third-party plugin isolation, and large project-generation CLI features.
- A step-executor boundary that can stop blocking work, such as process or thread isolation with
  real cancellation. Phase 4 rejects synchronous step functions and documents
  `asyncio.to_thread(...)` as the interim answer instead of force-terminating threads.
- A timeout policy object in place of the scalar `Step.timeout`, and a richer `input_type`
  contract than an `isinstance`-checked class, both deferred by
  [ADR 0009](adr/0009-workflow-engine-contract.md).
- Static analysis that proves branches merging into one step are mutually exclusive; Phase 4 fails
  such a merge at runtime instead.
- Parallel step execution and any claim of DAG scheduling; Phase 4 is sequential and conditional by
  design. The fan-out example in Phase 9 is the only thing that would revisit this, and it is written as
  conditioned on ADR 0021 and the owner's sign-off rather than as work that proceeds.
- Dynamic/imperative decorator Workflows until declarative Workflow semantics and introspection are stable.
- Knowledge/RAG subsystem until it has a bounded, independently useful provider contract; Phase 5
  ships embeddings and a tool allowlist, which is what a retrieval layer would need, but no
  storage/chunking/filtering/authorization contract is designed yet.
- Deriving tool schemas from type annotations, instead of requiring an explicit schema per tool
  ([ADR 0010](adr/0010-ai-facade-contract.md)).
- Streaming tool calls: a streaming response carries content only, and partially validated
  structured output is not actionable. Supporting this needs a new ADR, not a patch.
- Additional JSON Schema keywords (`oneOf`, `$ref`, `pattern`, numeric exclusivity). The subset is
  closed by decision, so widening it requires a new ADR rather than passing a schema that would
  validate more loosely than it reads.
- Pairing an embedding model with a chat model in a single provider contract; Phase 5 configures
  them separately (`model`, `embedding_model`) because one Ollama model does not serve both.
- Structural validation of a reconciler's returned output. The journal checks that a result is
  JSON-serializable and bounded, not that it matches the shape downstream steps expect; Phase 6
  documents the trap and shows the pattern to copy, and a real check would need the definition to
  declare a step's output type.
- Journal retention tooling: Phase 6 documents how to bound the file (delete terminal executions,
  which cascades) and deliberately ships no scheduler or command for it. Phase 11's
  `xyberos durable status` reads and reports and is not retention tooling.
- Promoting durable execution beyond experimental status. `PLAN.md` section 5.4 lists what has to be
  demonstrated; until then the API keeps warning.
- A separate `[metrics]` extra. Request metrics ships as a middleware class inside `[http]` because an extra
  costs a release row, a CI row, a tier entry, a feature-matrix row, and a catalogue row for one class; the extra
  is the upgrade path the day the capability grows a sink, an exporter, or a dependency.
- A stdio transport, and an `expose()` direction, inside this package. Both are refused by placement rather than
  by capability: spawning a process collides with "the framework starts nothing", and an RPC surface has no
  authorization model to stand behind it ([ADR 0014](adr/0014-no-identity-or-authorization-model.md)). Both live
  in `xyberos-mcp`, and the owner decides whether the transport ships at all.

**Non-goals, not deferred work.** Xyberos does not infer a refusal, a provider capability, or
structured-output support from response text. Only a provider-reported signal is trusted, because a
guess presented as a classification is worse than an absent one.

The disposition of the external review proposals — including the deferred decorator Workflow API and
the rejected reordering of the AI facade — is recorded in `PLAN.md` Appendix A.

## Remaining owner decisions

The license was the last Phase 0 blocker. **Decided:** the project is licensed under **Apache-2.0**
([ADR 0012](adr/0012-project-licence.md)), declared in `pyproject.toml` through PEP 639 metadata and
shipped as `LICENSE`. The adopted Python, database, TOML, Ollama, and versioning decisions remove the
rest.

**Decided for the AI surface.** These were the "before the relevant delivery phase begins" items, and
they are now settled rather than pending. Each is recorded where a reader will look for it, and each
is either enforced in code or stated as a policy:

| Decision | Value | Enforced by |
| --- | --- | --- |
| Supported Ollama release range | **≥ 0.5.0** | `MINIMUM_SUPPORTED_VERSION` in `src/xyberos/ai/ollama.py`; the adapter reports an older service as unhealthy and refuses later requests with the reason. Lowering it requires an explicit `minimum_version` setting |
| Smoke-test chat model | `llama3.2:3b` (~1.9 GB), tool-capable | `XYBEROS_OLLAMA_LIVE_MODEL` default in `tests/ai/test_live_ollama.py` |
| Smoke-test embedding model | **none**; the operator names one | `XYBEROS_OLLAMA_LIVE_EMBEDDING_MODEL` has no default, so the embedding tests skip |
| Capability-specific live tests | their own gate | `XYBEROS_OLLAMA_LIVE_TOOLS=1` for tool tests, so a model without tool support skips rather than fails |
| Model download and container policy | never pull, start, stop, upgrade, or deploy anything | `AIModelNotFoundError` names the `ollama pull` command; CI installs no models |
| **AI telemetry retention** | no AI content is persisted by the framework; usage metadata is retained only for as long as the execution that produced it | `LoggingPolicy.metadata_only()` by default; journal retention in [`docs/durable.md`](durable.md) |

**Decided: the release identity.** This line publishes as `xyberos` **`2.0.0`**, because the `xyberos`
name is held on the package index by the already-published 1.x line, which installs the same import
root and cannot be co-installed, so `0.1.0` would be unreachable through a plain `pip install` and
would read as a regression. The leading digit records lineage; maturity is carried by the
`Development Status` classifier and the tiers in [`stability.md`](stability.md). The decision, its
cost, and the trade it makes are in [ADR 0017](adr/0017-release-identity-and-lineage.md); its
procedural consequence is that a version bump touches six files rather than two.

**Still open, and owned by the project owner.** Contributor terms: whether to adopt a DCO, a CLA, or
copyright assignment. Nothing is due today, and the choice is easy to add later: a DCO is a
`CONTRIBUTING.md` line plus a `Signed-off-by:` trailer, and its enforcement is a CI check on the pull
request. A CLA is different in kind — it exists to keep the *option* to relicense, and that option
expires with the first outside contribution, so it cannot be added after the fact. The trigger to
decide is therefore one event, not a date: **settle it before merging the first pull request from
anyone other than the copyright holder** ([ADR 0012](adr/0012-project-licence.md)). Also still
owner-owned: any future promotion of durable execution beyond experimental status, whose criteria are
`PLAN.md` section 5.4. The first upload adds its own owner decisions — index access and the fate of the
documentation site — and they are listed as preconditions in
[the release guide](release.md#preconditions).

**Decided: two satellite names are reused, one is retired, and identity still stays out of the framework.**
The 1.x line published 23 satellites ([ADR 0017](adr/0017-release-identity-and-lineage.md)), and the three the
release guide names had already been repinned to `xyberos>=1.0,<2` — `xyberos-auth` `0.1.2`, `xyberos-db`
`0.1.2`, and `xyberos-mcp` `0.2.2` — which is why an unpinned install of any of them still resolves the 1.x
core today. The owner's decision for this line is:

- **The placement rule decides the home.** A dependency-free capability small enough for this line's suite
  ships here as a *module* when it needs nothing from PyPI (`xyberos.ai`, `xyberos.storage`, `xyberos.mcp`), as
  an extra when it needs something this line accepts (`[http]`, `[database]`, `[ollama]`, `[durable]`), or as a
  class inside an extra that already exists (request metrics, in `[http]`); anything needing
  Jinja2, OpenTelemetry, `cryptography`, a database driver, or an object-store client is a package in the
  ecosystem repository, and is released from there. One
  publishing path per name either way, and a name whose capability moved into an extra is retired with a
  metadata-only pointer rather than shimmed.
- **`xyberos-mcp` is reused, as a rewrite** that declares `xyberos>=2,<3`, while `0.2.2` stays published and
  unedited for the 1.x line. What this name carries is the **server direction** — `expose()` and, if the owner
  approves it, a stdio transport — while the **client** is the core module `xyberos.mcp` here, so one name
  answers one question instead of two. [ADR 0014](adr/0014-no-identity-or-authorization-model.md) leaves the
  framework no authorization model to put in front of an RPC surface, so the package says plainly that the
  caller brings one.
- **`xyberos-auth` is reused, carrying only the verification half.** The published `0.1.2` bundles OAuth2
  flows, OIDC, and Auth0/Okta/Entra presets; none of that returns, and the changelog's first line says so.
  The framework still owns no identity model, and the feature matrix's identity row is unchanged.
- **`xyberos-db` is retired for this line.** Its `0.1.2` stays published and gains a README pointer to
  `xyberos[database]` and the provider seam, because it duplicates an answer this line already has.
- **The other twenty satellites stay on the 1.x line** under the repin they already shipped. Reusing a name
  is not a sweep: it is a per-package decision that has to meet five conditions — the 2.x package is a
  rewrite rather than a shim; it declares `xyberos>=2,<3`; the old version stays published with the break in
  its README's first line; exactly one publishing path owns the name; and the subject is not already answered
  by core or an extra.

One consequence is a document change rather than a code change: [the release guide](release.md#releasing-beside-the-published-1x-line)'s
blanket repin instruction becomes per-name, and [ADR 0022](adr/0022-ecosystem-repository-and-satellite-names.md)
records this decision, the five conditions, and the name, URL, and owner of the ecosystem repository —
`xyberos/xyberos-plugins`, while `packages.toml` stays here, where the documents checked against it are — and
supersedes that clause of ADR 0017 for these two names. ADR numbers are taken when an ADR is written rather than
reserved in advance: 0018-0020 went to the placement rule, the storage contract, and the introspection
documents, and this decision took **0022**, the number the plan already used for it, leaving 0021 to the
deferred parallel-fan-out decision that the fan-out example is conditioned on.

**Still open, and owned by the project owner.**

1. **Whether the remaining new packages are published at all, and under whose names.** The reused names are
   settled above; what is not is the set this line has no 1.x predecessor for — `xyberos-templates`,
   `xyberos-observability`, `xyberos-auth`'s rewritten surface, `xyberos-postgres`, the S3 and AI adapter
   packages, and whatever tenancy becomes. Building them does not depend on the answer — a package is proved by
   its own suite against the installed core, and the compatibility job here proves the pair — but *listing* one
   as installable does, so a catalogue row says which form it currently is.
   [ADR 0007](adr/0007-trusted-plugins.md) already refuses discovery, so this is a naming and maintenance
   decision rather than a loading one. **Recommended, and separable:** settle the *names* in one sitting and
   claim them with pre-release placeholders, because an unclaimed name can be taken by somebody else while the
   code is being written, and leave the decision to *write* each package to the question of whether a candidate
   needs it. The whole cost of the naming half is a README and a version number per name, and it is the only
   part of the question that gets harder with delay.
2. **Whether parallel fan-out is un-deferred.** [The workflow guide](workflow.md#deliberate-limitations) and
   the backlog both record sequential execution as a design decision. The fan-out example is written as
   conditioned on ADR 0021 and the owner's sign-off, and it stays unbuilt until then.
3. **Whether the `xyberos-mcp` package may spawn a stdio server.** The standing policy is that the framework
   starts nothing — no model pull, no container, no serving path of its own. A stdio transport spawns a process
   the application names, so it is either a documented opt-in or a refusal; because the transport lives in the
   package *there* rather than in the extra here, the answer is a policy line in that package's README and no
   longer stands between Phase 9 and its client. It stays an owner decision, and it is the reason the name is
   reused rather than retired.

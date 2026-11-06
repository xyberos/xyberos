# Changelog

All notable changes to this project are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the versioning rules — including what the
leading digit means here — are in [the stability guide](docs/stability.md).

## [Unreleased]

## [2.2.0] - 2026-11-06

### Added

- **`xyberos.http.SessionMiddleware`, `xyberos.http.CSRFMiddleware`, and a `SessionStore` contract**,
  with an in-memory store. The cookie carries a signed session *id* rather than the payload, a session
  is written only when a handler changed it, and a state-changing request from another origin is refused
  ([ADR 0024](docs/adr/0024-sessions-and-csrf-are-middleware-in-the-http-module.md)). The recipe is
  [`examples/sessions`](examples/sessions/README.md).
- **`CSRFError`** in the error taxonomy: a `403` the adapter answers like any other `HttpError`.
- **What is absent, and what to do instead** ([`docs/capabilities.md`](docs/capabilities.md)): the index
  from every refusal to the seam, package, or recipe that answers it, checked against `packages.toml`.

### Changed

- **[ADR 0024](docs/adr/0024-sessions-and-csrf-are-middleware-in-the-http-module.md) supersedes the
  sessions/CSRF row of [ADR 0018](docs/adr/0018-capability-placement-rule.md)**, which refused them on
  the grounds that "Starlette ships both". Starlette ships sessions and **no** CSRF middleware, so the
  refusal's reason did not hold for half the row: the mechanism ships here, and the session store's
  policy stays with the application.

## [2.1.0] - 2026-10-14

Everything below landed after `2.0.0` was uploaded, and none of it was in that release: the tag's tree
and the published wheel were not the same snapshot, which is what this release corrects. A package
beside this line that declares `xyberos>=2,<3` and imports any of it needs `2.1.0`, not `2.0.0`.

### Added

- **`xyberos.storage`**: the `Storage` contract, a local-filesystem provider, an in-memory double, and
  `assert_storage_contract` — the suite a third-party provider proves itself with. Keys are the security
  boundary ([ADR 0019](docs/adr/0019-storage-contract.md)).
- **`xyberos.mcp`**: an MCP client over streamable HTTP, and the projection of a server's tools into the
  AI tool model. It is a dependency-free module, so it needs no extra.
- **`xyberos.http.RequestMetricsMiddleware`**: per-route and per-status counters as a middleware class
  the application passes. This is the capability `xyberos-metrics` used to provide, which is why that
  name is retired with a pointer rather than released again.
- **`assert_model_provider_contract`** and **`assert_embedding_provider_contract`** in
  `xyberos.ai.testing`: the suite an adapter author runs against their own backend. Every capability is
  checked from both sides — one the provider claims must work, and one it does not claim must be refused
  rather than attempted.
- **Introspection output** ([ADR 0020](docs/adr/0020-introspection-documents.md)): `check --json`,
  `check --why`, `check --schema`, the `config.schema.json` the package ships, and `durable status`. The
  provider descriptions the CLI explains a resolution path from are part of the runtime's own
  diagnostics, so there is one answer to "what depends on what" rather than two.
- **The storage and MCP error types** in the taxonomy: `StorageError` with its configuration, key,
  not-found, and size-limit subclasses, and `McpError` with its configuration, protocol, and transport
  subclasses.
- **The capability-placement rule** ([ADR 0018](docs/adr/0018-capability-placement-rule.md)), which
  decides whether the next capability is an extra here, a module here, a package beside this line, or a
  refusal.
- **A documentation site**: the learning paths, the production pages, and a reference tree generated
  from `docs/` rather than maintained twice ([the site plan](site/implementation.md)).

### Changed

- **`[http]` allows `starlette>=0.40,<2`.** The ceiling was `<1`, below the major the adapter is written
  against.
- **`SQLiteSettings.read_only`** opens the file through SQLite's `mode=ro` URI, so a diagnostic that
  reads a production database cannot change it. Only `busy_timeout` is applied, because the other
  PRAGMAs write to the file's header.
- **`[dev]` gained what the interface lessons and the site need** — `jinja2`, `python-multipart`,
  `mkdocs-material`, `pre-commit`, and `types-PyYAML`. The first two are still an application's
  dependencies rather than this package's, which is why they are here rather than in an extra.

## [2.0.0] - 2026-10-11

`2.0.0` is not an upgrade of the published `1.x` line: it is a different codebase under the same name,
which is why the number is a major one ([ADR 0017](docs/adr/0017-release-identity-and-lineage.md)). A
project that depends on the 1.x API should pin `xyberos<2`; the two lines install the same import root
and cannot share an environment. The 1.x releases stay published and unedited, and this file describes
only this line.

### Added

- **Runtime** — `App` composition with typed providers, three scopes (`app`, `request`,
  `transient`), a validated provider graph, explicit lifecycle (`validate` → `start` → `stop`),
  request contexts, cooperative cancellation tokens, context and logging helpers, and
  dependency-free route records ([ADR 0005](docs/adr/0005-phase-1-runtime-contract.md)).
- **Configuration** — typed TOML settings with `XYBEROS_` environment mapping and a documented
  precedence, a `schema_version`, and opaque per-capability sections
  ([ADR 0002](docs/adr/0002-configuration-and-database-stack.md)).
- **HTTP adapter** (preview, `http` extra) — Starlette behind one adapter, validated handler
  signatures, a fixed middleware order, correlation IDs, error normalization, and a test client
  ([ADR 0006](docs/adr/0006-http-and-database-adapters.md)).
- **SQLite provider** (preview, `database` extra) — SQLAlchemy Core with SQLite PRAGMAs, short
  explicit transactions, a bounded retry policy for write contention, and Alembic migrations run as a
  deploy step.
- **Plugins** — a trusted in-process capability contract with typed configuration, explicit
  ordering, provider source attribution, and diagnostics ([ADR 0007](docs/adr/0007-trusted-plugins.md)).
- **Workflow** — an immutable declarative definition with build-time validation, structured
  execution, bounded retries with backoff, deadlines, cancellation, and structured events; no
  persistence or recovery claimed ([ADR 0009](docs/adr/0009-workflow-engine-contract.md)).
- **AI facade** (preview, core) — provider-neutral chat, structured output, streaming, embeddings,
  and allowlisted tool calling, with a deterministic fake provider and an Ollama adapter behind the
  `ollama` extra ([ADR 0010](docs/adr/0010-ai-facade-contract.md)).
- **Durable execution** (experimental, `durable` extra) — a single-instance executor with a versioned
  journal, a persisted state machine, atomic claims, leases with fencing tokens, bounded retries,
  persisted cancellation, definition fingerprinting, and startup recovery
  ([ADR 0011](docs/adr/0011-durable-executor-contract.md)).
- **Command line** — `check`, `new`, `run`, and `migrate`, each wrapping an API the runtime already
  provides.
- **Documentation** — a guide per subsystem plus getting started, testing, troubleshooting, security,
  stability, and command-line guides; six tested examples.
- **Licence** — Apache-2.0 with an explicit patent grant ([ADR 0012](docs/adr/0012-project-licence.md)).

### Added

- **Boundary legibility.** [ADR 0014](docs/adr/0014-no-identity-or-authorization-model.md) records why
  there is no identity, tenancy, or authorization model and what to build instead;
  [ADR 0015](docs/adr/0015-durability-is-single-host.md) records why durability is single-host and how a
  queue owns delivery while the journal owns progress;
  [ADR 0016](docs/adr/0016-database-providers-are-an-extension-point.md) makes the database provider an
  extension point rather than a core feature. [The positioning page](docs/positioning.md) states who the
  framework is for, who it is not for, which alternative to reach for, and which seam replaces each
  default.
- **`assert_provider_contract`** in `xyberos.database.testing`: a conformance suite a third-party
  database provider runs against its own implementation, proving the same claims as the shipped SQLite
  provider. The suite is itself tested against two deliberately broken providers, and
  [the author guide](docs/database-providers.md) covers what to implement and what stays SQLite-specific.
- **Two tested integration recipes**: [`examples/tenancy`](examples/tenancy/README.md) shows a verified
  principal as an explicit argument, with tests proving a payload cannot choose its tenant, and
  [`examples/broker_worker`](examples/broker_worker/README.md) shows idempotent submission on a broker
  delivery id, with a test proving redelivery does not repeat an effect.
- **Capacity guidance with measured numbers**: a write-throughput baseline, about 2 000 writes per
  second from one writer, and the finding that under contention the retry backoff rather than the disk
  sets the pace ([performance](docs/performance.md#capacity-where-the-wall-is)).
- A catalogue section in the [plugin guide](docs/plugins.md#the-catalogue): what is known to exist, the
  four rules a plugin follows, and how to be listed.

### Changed

- The release identity is decided: this line publishes as `xyberos` `2.0.0`, because the `xyberos` name
  is held on the package index by the published 1.x line, which is a different codebase and installs
  the same import root ([ADR 0017](docs/adr/0017-release-identity-and-lineage.md)). The leading digit
  now records lineage, and the maturity claim moves to the `Development Status` classifier (now
  `4 - Beta`) and to the tiers in [the stability guide](docs/stability.md).
- The stable public surface is now declared and frozen per module, and `docs/stability.md` states
  which tier each surface is in ([ADR 0013](docs/adr/0013-stable-surface-and-versioning.md)).
- `xyberos.http` no longer advertises its handler-compilation internals, and `xyberos.plugins` no
  longer advertises `PLUGIN_API_MAJOR`. Both remain importable from the module that defines them.
- Settings are read from `app.settings.app`, not from attributes on `App`; the earlier documentation
  was wrong, and the correction is part of this release.
- The Ollama adapter requires a service at or above `0.5.0` and refuses work below it instead of
  failing somewhere less clear.

### Deprecated

- Nothing yet. `xyberos.deprecation` ships in this release so the first deprecation has a mechanism
  rather than an improvised warning.

### Fixed

Nothing here is a fix *for a user*, because every one was caught before the first release rather than
after it, which is the point of testing recovery with a real process-kill harness and of reviewing
secrets handling before publishing. They are recorded because they are the kind of defect a first
release should be able to say it already survived.

- An expired lease was counted for any non-terminal execution, so a yielded execution looked like an
  orphaned claim. Only `running` executions count now, and the lease row survives because it carries
  the fencing token.
- Resuming a parked `outcome_unknown` execution could silently re-run an effect of unknown status. It
  now waits for a decision instead.
- A missing optional dependency now names the extra to install, including when the failure comes from
  a user's module importing a third-party package directly.
- A database URL containing a percent sign no longer fails Alembic's configuration, which used to
  raise with the whole URL — password included — in the message. See "Security" above.
- A rejected Ollama `base_url` no longer repeats the URL it rejected, which could include a credential.

### Security

No security issue is known in this release. The phase 7 threat and abuse review found two
credential-echo defects, both fixed before the first release:
a database password could be quoted in a traceback when a migration URL contained a percent sign,
and a rejected Ollama `base_url` could repeat a credential it carried. The first is now impossible
because the URL survives Alembic's configuration intact, and the second because the credential rule
runs first and no message describes the configured value.

The trust model, the secrets handling rules, and the resource limits are documented in
[the security guide](docs/security.md); the reporting process is in [SECURITY.md](SECURITY.md).

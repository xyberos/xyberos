---
title: Feature support
status: verified
---

# Feature support

What the framework actually provides, what it defines as an extension point, and what the lesson
teaches you to build. Each lesson on this site carries one of these labels, and
`tests/site/test_lessons.py` checks that a lesson's label agrees with the
[stability guide](reference/stability.md), so this table is enforced rather than aspirational.

| Label | Meaning |
| ----- | ------- |
| **Built-in** | Ships in the framework. An `(extra)` note means an optional install. |
| **Extension point** | The framework ships the contract and a conformance suite; you ship the implementation. |
| **You add it** | A third-party library or server the framework deliberately does not depend on. |
| **You build it** | Nothing ships. The lesson is the implementation. |

## What ships, and where it comes from

<!-- generated:inventory -->

_Generated when the site is built, and checked by `site/scripts/matrix.py --check`, so this inventory cannot describe a tree that no longer exists._

**Modules.** What this package ships, and what a reader has to install for it. The `Needs` column is read from the code rather than remembered: a module that refuses to import without an extra names it in its own import guard, and the rollup follows each package's own entry point, which is why `xyberos.ai` is core while its Ollama adapter is not.

| Module | What it provides | Needs |
| ------ | ---------------- | ----- |
| `xyberos` | Composition, dependency injection, lifecycle, configuration, routing, context, workflow engine, error taxonomy | core |
| `xyberos.ai` | Provider-neutral AI facade: chat, streaming, structured output, tools, and a closed JSON Schema subset | core |
| `xyberos.cli` | The `xyberos` command's implementation; the command and its options are the promise, not these modules | core |
| `xyberos.database` | SQLite provider, connection and transaction handling, Alembic runner, provider conformance suite | `[database]` |
| `xyberos.durable` | Experimental single-host durable execution: journal, store, scheduler, worker, recovery | `[durable]` |
| `xyberos.execution` | In-process workflow engine: steps, edges, retries, timeouts, cancellation, events | core |
| `xyberos.http` | Starlette adapter, route compiling, middleware, request metrics, sessions, CSRF protection, test client | `[http]` |
| `xyberos.mcp` | Model Context Protocol client over streamable HTTP, and the projection of a server's tools into the AI tool model | core |
| `xyberos.plugins` | The plugin protocol and registry: trusted, ordered, no discovery | core |
| `xyberos.runtime` | Dependency scopes, context binding, correlation ids, deadlines | core |
| `xyberos.storage` | Storage contract, filesystem provider, in-memory double, conformance suite | core |

**Extras.** One install each, and the modules that cannot be imported without it. `dev` is the contributor's toolchain rather than a user's: it is what makes the two libraries an *application* brings — Jinja2 and python-multipart — available to the test suite that documents them.

| Extra | Declares | Needed by | What it adds |
| ----- | -------- | --------- | ------------ |
| `[database]` | `aiosqlite>=0.20,<1`, `alembic>=1.13,<2`, `sqlalchemy>=2.0,<2.1` | `xyberos.database.contracts`, `xyberos.database.migrations`, `xyberos.database.sqlite`, `xyberos.database.testing` | A single-file SQLAlchemy-friendly database, and the migrations that go with it |
| `[dev]` | `build>=1.2,<2`, `hatchling>=1.25,<2`, `httpx>=0.27,<1`, `jinja2>=3.1,<4`, `mkdocs-material>=9.5,<10`, `mypy>=1.11,<2`, `pre-commit>=3.7,<5`, `python-multipart>=0.0.18,<1`, `pytest>=8,<10`, `ruff>=0.6,<1`, `tomli>=2,<3`, `types-PyYAML>=6.0,<7` | — | The contributor's toolchain, and the two libraries this line expects an *application* to bring: Jinja2 and python-multipart |
| `[durable]` | `aiosqlite>=0.20,<1`, `alembic>=1.13,<2`, `sqlalchemy>=2.0,<2.1` | `xyberos.durable.journal`, `xyberos.durable.store` | Persistence for workflow progress, single host and at-least-once |
| `[http]` | `httpx>=0.27,<1`, `starlette>=0.40,<2` | `xyberos.http.adapter`, `xyberos.http.csrf`, `xyberos.http.metrics`, `xyberos.http.middleware`, `xyberos.http.requests`, `xyberos.http.routing`, `xyberos.http.sessions`, `xyberos.http.testing` | Routing an application's routes as an ASGI application |
| `[ollama]` | `httpx>=0.27,<1` | `xyberos.ai.ollama` | The first AI provider: a local Ollama service |

**Packages outside this repository.** Every name this line knows about, from [`packages.toml`](https://github.com/xyberos/xyberos/blob/master/packages.toml) — the manifest the compatibility job also reads. `planned` means decided and no distribution is written, `written` means the distribution exists and this line has no release of it, and `published` means a release exists that the job installs and proves.

| Package | Import root | Status | Declares | Subject |
| ------- | ----------- | ------ | -------- | ------- |
| `xyberos-mcp` | `xyberos_mcp` | published | `xyberos[http]>=2.1,<3` | The server direction: exposing an application's tools over MCP; a stdio transport only with the owner's approval |
| `xyberos-templates` | `xyberos_templates` | published | `xyberos[http]>=2,<3`, `jinja2>=3.1,<4`, `python-multipart>=0.0.18,<1` | Server-rendered pages: an engine-neutral Templates contract with Jinja2 shipped, a static mount, and form reading |
| `xyberos-observability` | `xyberos_observability` | published | `xyberos[http]>=2,<3`, `opentelemetry-api>=1.20,<2`, `opentelemetry-sdk>=1.20,<2` | One explicit call that configures a logging handler and spans, fed by the runtime's own event sink |
| `xyberos-auth` | `xyberos_auth` | published | `cryptography>=42,<47` | Verification only: an assertion from a shared secret or a JWKS, and a Principal |
| `xyberos-postgres` | `xyberos_postgres` | published | `xyberos[database]>=2,<3`, `asyncpg>=0.29,<1`, `sqlalchemy>=2.0,<2.1` | A DatabaseProvider for PostgreSQL, proved against the shipped conformance suite |
| `xyberos-storage-s3` | `xyberos_storage_s3` | published | `xyberos>=2.1,<3`, `aioboto3>=13,<16` | A Storage provider for S3-compatible object stores, proved against the shipped conformance suite |
| `xyberos-openai-compatible` | `xyberos_openai_compatible` | published | `xyberos>=2.1,<3`, `httpx>=0.27,<1` | A ModelProvider for OpenAI-compatible chat and embedding endpoints |
| `xyberos-crud` | `xyberos_crud` | published | `xyberos[database]>=2,<3`, `sqlalchemy>=2.0,<2.1` | Query construction over the provider contract: filtering, sorting, and pagination as values rather than entities |
| `xyberos-memory` | `xyberos_memory` | written | `xyberos[database]>=2,<3` | Persistent conversation history and explicitly scoped facts over DatabaseProvider |
| `xyberos-knowledge` | `xyberos_knowledge` | written | `xyberos>=2,<3` | Document chunking, embedding, retrieval, and citations over an application-supplied vector store |
| `xyberos-db` | `xyberos_db` | retired → `xyberos[database]` | — | Retired: the capability is xyberos[database] and the provider seam |
| `xyberos-metrics` | `xyberos_metrics` | retired → `xyberos.http` | — | Retired: request metrics ship as xyberos.http.RequestMetricsMiddleware |

<!-- generated:end -->

Every module above that needs an extra says so because of the code rather than because of this page:
the guard that raises `ModuleNotFoundError` names the extra to install, and the inventory reads it
from there. So a capability cannot be installed, documented, and forgotten about in the same commit.

## Capabilities, extension points, and absences

The inventory above is what exists. This table is what the framework *promises* about each capability
— which is a decision rather than a fact about the tree, so it is written by hand. Everything named
here is either shipped, or explicitly not shipped.

Packages named in the last column are either **released** (`published`) or written but not yet
available to install (`written`). What a reader installs is the framework plus the one published
package a capability needs — `pip install xyberos xyberos-templates`, for instance — and each
release carries a check this repository's compatibility job runs against the published pair. What
each one gives you, and the install line, is [the packages guide](extend/packages.md); the manifest that generates the inventory above is
[`packages.toml`](https://github.com/xyberos/xyberos/blob/master/packages.toml).

| Capability | Where it lives | Tier | Ships with |
| ---------- | -------------- | ---- | ---------- |
| Application composition, dependency injection, scopes, lifecycle | `xyberos` | Built-in | core |
| Typed configuration (`Settings`, `xyberos.toml`, `XYBEROS_*`) | `xyberos` | Built-in | core |
| Context and logging helpers, error taxonomy | `xyberos` | Built-in | core |
| Workflow engine: retries, branches, timeouts, cancellation | `xyberos` (`Workflow`, `WorkflowExecutor`, `direct`) | Built-in | core |
| Trusted plugins | `xyberos` (`Plugin`, `PluginRegistry`) | Built-in | core |
| AI facade, contracts, tools, JSON Schema subset, fake provider | `xyberos.ai` | Built-in | core |
| Object storage: filesystem provider and in-memory double | `xyberos.storage` | Built-in | core |
| MCP tools: consuming a server's tools over streamable HTTP | `xyberos.mcp` | Built-in | core |
| HTTP routing over Starlette | `xyberos.http` | Built-in (extra) | `[http]` |
| Middleware: correlation id, request scope, error mapping, request metrics, sessions, CSRF | `xyberos.http` | Built-in (extra) | `[http]` |
| SQLite provider and Alembic migrations | `xyberos.database` | Built-in (extra) | `[database]` |
| Ollama adapter | `xyberos.ai.ollama` | Built-in (extra) | `[ollama]` |
| Test doubles: `ManualClock`, `FakeModelProvider`, `InMemoryStorage`, `temporary_database`, `create_test_client` | the `*.testing` modules | Built-in | with the module they double |
| Command line: `new`, `check`, `run`, `migrate`, `durable status` | the `xyberos` command | Built-in | per command |
| Durable executor | `xyberos.durable` | **Experimental** | `[durable]` |
| Database provider contract and conformance suite | `xyberos.database.testing` | Extension point | `[database]` |
| Storage provider contract and conformance suite | `xyberos.storage.testing` | Extension point | core |
| AI provider contract and conformance suite | `xyberos.ai.testing` | Extension point | core |
| Plugin protocol, and the catalogue of packages that implement one | `xyberos.plugins`, [the plugin guide](reference/plugins.md) | Extension point | core |
| HTML templates, static files, form reading | Starlette and Jinja2, wrapped by `xyberos-templates` | You add it | `xyberos-templates` |
| MCP server direction: exposing an application's tools | `xyberos-mcp`, over the HTTP adapter | You add it | `xyberos-mcp` |
| Logging handler and tracing spans | `xyberos-observability`, fed by the runtime's event sink | You add it | `xyberos-observability` |
| PostgreSQL, MySQL, MariaDB providers | `xyberos-postgres`, proved by the database conformance suite | Extension point | `xyberos-postgres` |
| S3-compatible object storage | `xyberos-storage-s3`, proved by the storage conformance suite | Extension point | `xyberos-storage-s3` |
| OpenAI-compatible chat and embedding endpoints | `xyberos-openai-compatible`, proved by the AI conformance suite | Extension point | `xyberos-openai-compatible` |
| CRUD query construction: filtering, sorting, pagination | `xyberos-crud`, over the database provider contract | You add it | `xyberos-crud` |
| Persistent conversation history and scoped facts | `xyberos-memory`, over `DatabaseProvider` | Written; not yet published | `xyberos-memory` |
| Document chunking, embeddings, retrieval, and citations | `xyberos-knowledge`, over `EmbeddingModel` and an application-supplied `VectorStore` | Written; not yet published | `xyberos-knowledge` |
| Redis | — | You add it | — |
| Identity, roles, tenancy model | — | Not provided, and it will not be | `xyberos-auth` verifies an assertion and stops |
| Vector-store backend, intent classification, agent coordination | — | You build it | — |

## The refusals are features

Three rows above are absences by decision rather than by omission, and each has a recorded reason:

- **No identity or authorization model.** Authorization is a product decision; the framework would get
  it wrong for most users and would own security it cannot verify. The sanctioned shape — verify an
  assertion upstream, pass the principal as an argument, scope queries by it — is in
  [ADR 0014](reference/adr/0014-no-identity-or-authorization-model.md) and is tested in
  [the tenancy example](https://github.com/xyberos/xyberos/tree/master/examples/tenancy).
- **One database provider, and a documented extension point.** SQLite ships; the seam is any async
  SQLAlchemy dialect, and a third-party provider proves itself with `assert_provider_contract`
  ([ADR 0016](reference/adr/0016-database-providers-are-an-extension-point.md)).
- **Durable execution is experimental.** Single host, one journal, at-least-once effects — contract
  terms rather than caveats ([ADR 0011](reference/adr/0011-durable-executor-contract.md)).

**Sessions and CSRF left this list.** They were refused on the grounds that Starlette ships both, which
is true for sessions and false for CSRF — Starlette ships no CSRF middleware, so that half never cost a
reader an install. They now ship as `xyberos.http` middleware over a `SessionStore` contract, with the
policy that belongs to the application — the store, the login, and the authorization model — left
where it was ([ADR 0024](reference/adr/0024-sessions-and-csrf-are-middleware-in-the-http-module.md)).
[The sessions example](https://github.com/xyberos/xyberos/tree/master/examples/sessions) is the
recipe, and [what is absent, and what to do instead](reference/capabilities.md) is the index from every
gap to its answer.

## What is never implied

Nothing on this site describes a capability as "supported" unless a test in this repository exercises
it. Where a lesson needs something the framework does not provide, the lesson says so at the top of the
page and shows the code that supplies it.

## Where the labels come from

The inventory at the top of this page is generated, not maintained: `site/scripts/matrix.py` reads
the modules from `src/xyberos/`, the extras from `pyproject.toml`, and the packages from
[`packages.toml`](https://github.com/xyberos/xyberos/blob/master/packages.toml) — the same manifest the
compatibility job reads — and every build regenerates it. `python site/scripts/build.py --check` fails when
it has drifted, `tests/test_packages_manifest.py` checks that the catalogue and the release guide agree
with the same manifest, and `tests/site/test_matrix.py` checks the generator itself. A package that does
not exist cannot appear here as shipped, and one that does exist cannot be missing.

The tables *below* that one are written by hand on purpose, because they are decisions rather than
descriptions: a capability the framework refuses, and a package that does not exist yet, cannot be
derived from a tree that does not contain them.

Two 1.x names are retired for this line rather than reused. `xyberos-db` keeps its published 1.x
release and gains a pointer to `xyberos[database]` and the provider seam, so nothing moves under a user
who pinned it. `xyberos-metrics` is retired with nothing to point *from*: no release under that name
resolves on the index, so this line publishes no patch for it, and the capability ships here as
`xyberos.http.RequestMetricsMiddleware` instead.

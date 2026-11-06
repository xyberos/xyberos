# What is absent, and what to do instead

> Status: Phase 8. Every row below is a decision with a reason, not an unfinished edge. This page is
> the index from a gap to its answer, so a reader who notices something missing finds the seam, the
> package, or the recipe that closes it without leaving the framework for a batteries-included one.

The placement rule is [ADR 0018](./adr/0018-capability-placement-rule.md): a capability is an **extra
here**, a **module here**, a **package there**, or a **refusal**. The row that matters most is the
third, because "there" is the answer to *"do I have to adopt Django for this?"* — no, the capability
arrives as a small distribution that builds on a contract this line already ships, and `pip install
xyberos` never pulls it in.

## The four gaps a reader notices first

Each has a recorded reason and a documented way through. None of them requires a framework.

### Identity and authorization — verify an assertion, pass the principal

**Absent by decision** ([ADR 0014](./adr/0014-no-identity-or-authorization-model.md)): authorization is
a product decision, and a framework that guesses owns security it cannot verify.

**What to do instead:** verify the assertion upstream, then pass the principal as an argument.
`xyberos-auth` does the verifying half and stops; the scoping half is a service signature.

```python
from xyberos_auth import AuthSettings, PrincipalVerifier

verifier = PrincipalVerifier(AuthSettings(audience="checkout", secret=os.environ["AUTH_SECRET"]))

@app.get("/orders")
async def list_orders(request: Request) -> dict[str, object]:
    principal = verifier.verify(request.headers["Authorization"].removeprefix("Bearer "))
    return {"orders": await orders.for_tenant(principal.tenant)}   # the tenant is an argument
```

`pip install xyberos-auth` — verification only, shared secret or JWKS. The tested shape, including the
case that matters most, is [the tenancy example](../examples/tenancy/README.md).

### Sessions — a middleware here, the store there

**Shipped as middleware** (`xyberos.http.SessionMiddleware`, [ADR 0024](./adr/0024-sessions-and-csrf-are-middleware-in-the-http-module.md)),
because the *store* is the deployment's decision and the mechanism is not:

```python
from starlette.middleware import Middleware
from xyberos.http import HttpAdapter, InMemorySessionStore, SessionMiddleware

store = InMemorySessionStore()          # swap for a package beside this line in production

adapter = HttpAdapter(
    app,
    middleware=(Middleware(SessionMiddleware, store=store, secret=os.environ["SESSION_SECRET"]),),
)

@app.get("/me")
async def me(request: Request) -> dict[str, object]:
    return {"user": request.session.get("user")}      # Starlette's own spelling
```

The cookie is a signed session **id**, not the data, so a handler's values never reach the client; the
session is written **only when a handler changed it**; and a durable store is a package there, reached
through the `SessionStore` protocol. The recipe is [the sessions example](../examples/sessions/README.md).

### CSRF — a middleware here, because there is nothing to install

**Shipped as middleware** (`xyberos.http.CSRFMiddleware`). Starlette ships sessions but **no** CSRF
middleware, so unlike sessions it is not a marshalling of an existing dependency:

```python
adapter = HttpAdapter(app, middleware=(Middleware(CSRFMiddleware),))

@app.get("/order-form")
async def order_form(request: Request) -> dict[str, str]:
    return {"csrf_token": get_csrf_token(request)}    # one line, and a page can embed it
```

A state-changing request whose `Origin` (or `Referer`) names another site is refused with a `403`; a
presented `X-CSRF-Token` that does not match the issued one is refused too. A request with neither is
not a browser cross-site request and is allowed, which is why `curl` still works. Set
`trusted_origins` behind a proxy.

### A second database — write a provider, prove it with a suite

**Absent by decision** ([ADR 0016](./adr/0016-database-providers-are-an-extension-point.md)): SQLite
ships, and the seam is **any async SQLAlchemy dialect** rather than "any database".

**What to do instead:** `pip install xyberos-postgres` (published, 0.1.0), or implement
`DatabaseProvider` — three members over an `AsyncConnection` — and prove it with one call:

```python
from xyberos_postgres import PostgresSettings, postgres_provider
from xyberos.database import DatabaseProvider

app.provide(
    DatabaseProvider,
    factory=postgres_provider(PostgresSettings(host="db.internal", database="app")),
    eager=True,
)
```

`assert_provider_contract` is the whole conformance requirement, and services do not change: they use
`transaction()`, `retrying()`, and `health()` either way. See
[writing a database provider](./database-providers.md).

## Everything else that is absent

| You notice | Placement | What to do instead |
| --- | --- | --- |
| An ORM, models, repository base classes | Refused ([positioning](./positioning.md)) | Use SQLAlchemy Core directly over the provider; `xyberos-crud` adds filtering, sorting, and pagination as **values** |
| An admin UI | Refused | Build the screens; `xyberos-crud` and `xyberos-templates` are the pieces |
| OpenAPI generation, an admin API explorer | Refused | Serialize `app.diagnostics()` and the route registry yourself ([ADR 0020](./adr/0020-introspection-documents.md)) |
| Persistent conversation history and scoped facts | Package there, written but not yet published ([ADR 0025](./adr/0025-memory-and-knowledge-packages.md)) | `xyberos-memory` uses the application's `DatabaseProvider`; the application still owns scope authorization |
| Document ingestion, embedding, retrieval, and citations | Package there, written but not yet published ([ADR 0025](./adr/0025-memory-and-knowledge-packages.md)) | `xyberos-knowledge` uses `xyberos.ai.EmbeddingModel` and an application-supplied `VectorStore`; prompt assembly and generation stay with the application |
| Job queues, a scheduler | Refused | Durable execution is single-host ([ADR 0015](./adr/0015-durability-is-single-host.md)); use a queue as the delivery layer and keep the worker single-host per journal |
| Rate limiting, request size limits, TLS | Refused | They belong to the ASGI server and the reverse proxy (`docs/security.md`) |
| Feature flags | Refused | Configuration and plugins; nothing framework-owned |
| Multi-host durable execution, exactly-once external effects | Refused | Temporal, Argo, or a managed workflow service; this line runs the worker role well |
| An entry-point plugin registry | Refused ([ADR 0007](./adr/0007-trusted-plugins.md)) | `app.add_plugin(...)` explicitly, so startup stays readable |
| Templates, static files, form reading | Package there | `pip install xyberos-templates` (Jinja2 shipped, render off the event loop, escaping stated) |
| Logging preset, tracing spans | Package there | `pip install xyberos-observability` |
| Exposing your own tools over MCP | Package there | `pip install xyberos-mcp` (`expose(app, tools)`); the client half is core `xyberos.mcp` |
| S3-compatible object storage | Package there | `pip install xyberos-storage-s3`, proved by `assert_storage_contract` |
| An LLM provider other than Ollama | Package there | `pip install xyberos-openai-compatible`, proved by `assert_model_provider_contract` |
| CRUD query construction | Package there | `pip install xyberos-crud` |
| Migrations | Already ships | `xyberos[database]`: `run_migrations` and `apply_migrations` drive Alembic |
| Request validation | Already ships | `xyberos.ai.schema`: `validate_payload`, `check_schema`, `describe_schema` |
| Request metrics | Already ships | `xyberos.http.RequestMetricsMiddleware` |

## The retired names

Two 1.x names are retired rather than reused, so a pinned dependency keeps resolving:
`xyberos-db` points at `xyberos[database]` and the provider seam, and `xyberos-metrics` points at
`xyberos.http.RequestMetricsMiddleware`. Neither is re-released under the old name.

## Adding one yourself

If the row you need is not here, [ADR 0018](./adr/0018-capability-placement-rule.md) says where a new
capability goes and what it costs. The short version: an extra is a promise the release makes, a module
here must need nothing from PyPI, and anything else is a package there with an import root of its own.
[The plugin guide](./plugins.md) is the how-to.

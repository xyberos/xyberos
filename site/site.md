# XYBEROS 2.0 Tutorial Plan

The best approach is to build a progressive, project-based tutorial series similar to W3Schools: start with a working application using minimal code, then introduce one concept at a time until readers can build complete traditional, AI-powered, and hybrid applications.

The central teaching principle should be: every tutorial adds one capability to a working application. Beginners should not have to learn the entire architecture before they can build something useful.

## 1. Recommended tutorial structure

Part 1 — XYBEROS Fundamentals

Learn the runtime, write minimal code, and understand how an application starts.

Part 2 — Traditional Applications

Databases, tables, authentication, APIs, HTML templates, and complete CRUD applications.

Part 3 — AI-Powered Applications

Models, structured output, memory, knowledge retrieval, tools, intents, and workflows.

Part 4 — Hybrid Applications

Combine conventional business logic, databases, web interfaces, and AI capabilities.

Part 5 — Extending XYBEROS

The provider registry, modules, plugins, custom providers, testing, deployment, and advanced architecture.

## 2. Part 1 — XYBEROS fundamentals

The first section should feel as easy as starting with FastAPI. A beginner should be able to run an application within the first few minutes.

| Lesson | Tutorial                             | What the reader learns                              |
| ------ | ------------------------------------ | --------------------------------------------------- |
| 1      | What is XYBEROS?                     | Runtime, providers, plugins, workflows              |
| 2      | Install XYBEROS                      | Python range, extras, and what core does not import |
| 3      | Create a project                     | `xyberos new`, the layout it writes, and running it  |
| 4      | Your first application               | Minimum working code                                |
| 5      | Run your application                 | Startup, configuration, and shutdown                |
| 6      | Understand the application lifecycle | What happens when the app starts                    |
| 7      | Add configuration                    | `xyberos.toml`, `XYBEROS_*`, and `Settings`         |
| 8      | Use dependency injection             | How providers are registered and resolved           |
| 9      | Choose a scope                       | App, request, and transient lifetimes               |
| 10     | Understand the provider registry     | `app.provide`, `Inject()`, and `app.diagnostics()`  |
| 11     | Read `xyberos check`                 | Settings, the provider graph, and handler signatures |
| 12     | Organize your project                | Files, folders, imports, and conventions            |
| 13     | Write your first test                | Test doubles, and why the AI path needs no model    |
| 14     | Handle errors and logging            | Diagnose common problems                            |
| 15     | Use the command line                 | `new`, `check`, `run`, and `migrate`                |

Teaching requirement: show the smallest valid program first. Explain each line only after the reader has a working result.

### Where the fundamentals content comes from

This path retires `docs/tutorial.md` rather than competing with it. That page was a thirteen-chapter tutorial whose every chapter module runs in CI and whose every printed output block is compared with the real output it produces, so it is the starting point. **The fundamentals chapters have moved, and the path is now complete:** all fifteen lessons are published and verified. **The Traditional Apps path is complete too:** twelve lessons, ending in the growing application in `examples/user_management/`. The chapters that belong to the paths not yet written stay where they are until their path exists.

| `docs/tutorial.md` chapter | Home in the site | Status |
| -------------------------- | ---------------- | ------ |
| 1 first app | Lesson 4 here | **Migrated** |
| 2 injection | Lesson 8 here | **Migrated** |
| 3 scopes | Lesson 9 here | **Migrated** |
| 4 settings | Lesson 7 here | **Migrated** |
| 5 HTTP, 6 requests and errors | Traditional path, lessons 1–2 | **Migrated** |
| 7 SQLite | Traditional path, lesson 3 | **Migrated** |
| 8 testing | Lesson 13 here | **Migrated** |
| 9 plugins | Plugins chapter | Stays until that chapter is written |
| 10 workflows | AI and hybrid paths | Stays until those paths are written |
| 11 AI | AI path | Stays until that path is written |
| 12 durable | Extend XYBEROS, fenced as experimental | Stays until that section is written |
| 13 the command line | Lesson 15 here | **Migrated** |

The one rule the retirement follows: **a chapter has exactly one home and exactly one suite.** Content is never in two places and never checked twice — a chapter that has moved is deleted from `docs/tutorial.md`, and a chapter that has not moved is not on the site. Deleting the rest before their paths exist would leave that content nowhere.

Three rules follow, and they apply to every lesson in every path:

- **A lesson page contains no hand-written code.** Code is included from a file under `examples/` by path, so the page and the file CI runs cannot disagree. An exercise's answer is a file too, which is what stops an answer from rotting while the lesson stays correct.
- **A lesson's printed output is a claim.** The existing `<!-- output: <module> -->` convention is the assertion; a page whose documented output differs from the real output fails the suite.
- **A lesson says how it is checked**, in its front matter: `verify: output` runs the example and compares what it printed, `verify: pytest` runs it as a test (a lesson about testing has no output to compare), and `verify: command` runs the command the page quotes.

Use a consistent lesson format throughout the series:

1. What you will build.
2. Prerequisites.
3. Complete working code.
4. How to run it.
5. Expected output.
6. Explanation of each important line.
7. Common mistakes.
8. A small exercise.
9. Link to the next lesson.

## 3. Part 2 — Traditional applications

Build one project progressively: a simple User Management Application. Start with no database and no classes; introduce additional concepts only when needed.

Recommended project progression

Stage A — Minimal application

- Create and run an application.
- Add a simple endpoint or handler.
- Return text and JSON.
- Understand routing and responses.

References: [SQLite SQL syntax](https://www.sqlite.org/lang.html) and the [SQLAlchemy 2.0 Core tutorial](https://docs.sqlalchemy.org/en/20/core/tutorial.html)

Stage B — Database fundamentals

- Connect to SQLite.
- Execute basic queries.
- Create tables and insert records.
- Learn transactions, migrations, and connection lifecycle.
- Meet the provider contract: `DatabaseProvider` is portable, `SqliteSettings` is not, and PostgreSQL arrives as an extension point rather than as a shipped provider.

Reference: [Tailwind CSS documentation](https://tailwindcss.com/docs)

Stage C — Data models and CRUD

- Create users and roles.
- Add, list, view, edit, and delete records.
- Introduce validation and relationships.
- Add pagination, filtering, and error handling.

References: [HTMX documentation](https://htmx.org/docs/) and [Alpine.js](https://alpinejs.dev/start-here)

Stage D — HTTP, APIs, and identity

- Routes, path parameters, query parameters, and request bodies.
- Start, configure, and serve the application.
- Identity arrives from upstream: a component verifies a signed assertion and returns a principal, the principal is passed to the service as a required argument, and the tenant comes from the principal — never from the request payload, and never from a context variable.
- Authorization is a product decision the application makes, and this series does not build one. XYBEROS ships no identity or authorization model and will not (ADR 0014); sessions and CSRF ship as middleware the application passes (ADR 0024, which changed their placement after this plan was written), and the tested identity shape is the tenancy example, including the case where a payload that claims another tenant changes nothing.
- Protected endpoints, `401` versus `403`, and stripping the assertion header at the edge.

References: [Starlette templates](https://www.starlette.io/templates/) and [Starlette static files](https://www.starlette.io/staticfiles/)

Stage E — Server-rendered interfaces

Boundary first: XYBEROS ships no template engine and no static-file mount. A route handler may return any Starlette `Response`, so HTML rendering works — the engine and the asset pipeline belong to the application, exactly like the ASGI server does. This stage uses Starlette's `Jinja2Templates` and `StaticFiles`, both of which are prerequisites rather than XYBEROS APIs. Nothing in this stage is a XYBEROS feature. **Superseded in part by ADR 0024:** sessions and CSRF *do* ship now, as `xyberos.http` middleware the application passes, so a form stage uses `CSRFMiddleware` rather than reaching for a third-party one.

- HTML templates and template inheritance.
- HTMX for partial page updates.
- Alpine.js for lightweight client-side interactions.
- Tailwind CSS for styling.
- Forms, validation messages, tables, modals, and pagination.

### Continue to complete applications

After the user management project, cover:

- File uploads and downloads.
- Email and notifications.
- Background jobs and scheduled tasks.
- Caching.
- External API integrations.
- Application settings and secrets.
- Logging, testing, and error handling.
- Production deployment and security.

### Database coverage

Teach databases by comparing concepts rather than assuming every backend works identically.

**One database ships, and the seam is the lesson.** XYBEROS ships SQLite through SQLAlchemy Core and `aiosqlite` and nothing else (ADR 0016). Do not imply that a backend is supported until it is verified against the implementation, and label every page with where it sits:

| Database        | Status             | What to teach                                                                  |
| --------------- | ------------------ | ------------------------------------------------------------------------------ |
| SQLite          | **Shipped** (`xyberos.database`) | Easiest starting point; local storage, basic SQL, transactions, and migrations |
| PostgreSQL      | **Extension point** | `DatabaseProvider` is portable and `SqliteSettings` is not; the seam is any async SQLAlchemy dialect, and a third-party provider proves itself with `assert_provider_contract` |
| MySQL/MariaDB   | **Extension point** | The same contract and conformance suite; no provider ships, and none is promised |
| Redis           | **Not provided**    | A client library the application adds; the runtime is not involved, so no XYBEROS import appears in the example |
| Vector database | **Not provided**    | Semantic retrieval is application code over `AIFacade.embed`, introduced in the AI section |

## 4. Part 3 — AI-powered applications

Use a second progressive project: an AI Assistant. Start with a working application that does not require an AI model, then add each capability independently.

**Every lesson is labelled with who provides the capability.** XYBEROS ships a provider-neutral AI facade, structured output over a closed JSON Schema subset, an allowlisted tool layer, and a deterministic fake provider — and nothing else. There is no memory store, no document loader, no vector index, no intent classifier, and no agent loop in the package, so those lessons teach you to build one and say so on the page.

| Lesson | Tutorial                      | Learning outcome                                   | Provided by                  |
| ------ | ----------------------------- | -------------------------------------------------- | ---------------------------- |
| 1      | Build an AI-ready application | Application runs without a model                   | Built-in                     |
| 2      | Understand AI providers       | Provider abstraction and declared capabilities      | Built-in                     |
| 3      | Connect your first model      | Send a prompt and receive a response               | Built-in (`ollama` extra)    |
| 4      | Switch models/providers       | Separate application logic from provider choice    | Built-in                     |
| 5      | Generate structured output    | Validate model responses against a schema          | Built-in                     |
| 6      | Handle errors and timeouts    | Manage failed or slow model calls                  | Built-in                     |
| 7      | Add conversation history      | Preserve context across turns                      | You build it                 |
| 8      | Add memory                    | Store and retrieve useful information              | You build it                 |
| 9      | Add knowledge                 | Load documents and retrieve relevant passages      | You build it                 |
| 10     | Build a RAG application       | Ground responses in retrieved knowledge            | You build it (over `embed`)  |
| 11     | Add tools                     | Let the model request controlled operations        | Built-in                     |
| 12     | Add intents                   | Classify requests and route them appropriately     | You build it (over `structured`) |
| 13     | Build workflows               | Compose explicit steps and conditional branches    | Built-in                     |
| 14     | Add agent behavior            | Combine reasoning, tools, and bounded execution    | You build it (tools + workflow) |
| 15     | Test the AI path              | Exercise every prompt, tool, and failure with no model service | Built-in (`FakeModelProvider`) |
| 16     | Evaluate AI quality           | Test accuracy, grounding, latency, and cost        | You build it                 |
| 17     | Secure AI applications        | Access control, prompt injection, tool permissions | Built-in boundaries, application code |

### The progression matters

Teach these concepts separately before combining them:

- Model: generates a response.
- Memory: retains or retrieves information across interactions.
- Knowledge: supplies external information relevant to a question.
- Tool: performs an operation through a defined interface.
- Intent: represents a classification or routing decision.
- Workflow: specifies how steps are executed.
- Agent: uses a model and available tools to pursue a bounded objective.

A beginner should understand what each component contributes before encountering a complex agent architecture.

## 5. Part 4 — Hybrid traditional + AI applications

This should be one of the most important sections because it demonstrates why XYBEROS is useful beyond a standalone AI chatbot.

Build a Smart Support Desk incrementally.

Web interface

HTMX · Alpine.js · Tailwind CSS

XYBEROS application runtime

Routing · Dependency injection · Configuration

Traditional services

Users, tickets, permissions, status, audit logs

AI services

Classification, knowledge search, summaries, suggested replies

Database and external integrations

### Hybrid tutorial sequence

1. Create support tickets using ordinary CRUD operations.
2. Add a verified principal and the access checks the application owns (ADR 0014).
3. Add AI-based ticket classification.
4. Add knowledge retrieval for suggested answers.
5. Generate draft replies without sending them automatically.
6. Add human approval before sensitive actions.
7. Use workflows to coordinate classification, retrieval, drafting, and review.
8. Add background processing for slower AI tasks.
9. Log model usage, costs, decisions, and outcomes.
10. Deploy the complete application.

Use this project to teach an important architectural rule: AI should augment conventional business logic, not replace it.

For example, ticket permissions, billing, and status transitions should be enforced by application code. An AI model may recommend an action, but it should not bypass authorization.

Other hybrid projects can follow:

- AI-assisted CRM.
- Document processing and approval systems.
- Inventory forecasting.
- Internal knowledge assistants.
- AI-enhanced reporting dashboards.

## 6. Part 5 — The provider registry and dependency injection

This topic deserves its own tutorial sequence, separate from the first application tutorial. There is no "capability registry" in XYBEROS 2.0, and the tutorial must not invent one: the names below are the actual API. Note that *capability* already means something else in this codebase — a declared model capability, checked before any call is made — so this part is titled after the provider registry and says so.

### Start with a simple analogy

A provider is something the application supplies to itself: a database handle, an email sender, a model facade. `app.provide(...)` registers it, `Annotated[T, Inject()]` asks for it, and `app.diagnostics()` answers "where did this come from?".

Registration happens once, while the application is still being composed. Choosing an implementation is a decision the application makes at composition time, not a lookup the runtime performs per request.

### Conceptual example

The application chooses, at composition time

`app.provide(DatabaseProvider, factory=sqlite_provider(SqliteSettings()))`

The registry records the provider, its scope, and its source

`ProviderRegistry`

A handler declares what it needs and the runtime supplies it

`Annotated[DatabaseProvider, Inject()]`

### Recommended lesson sequence

| Lesson | Topic                                                   |
| ------ | ------------------------------------------------------- |
| 1      | What is a provider?                                     |
| 2      | What problem does the registry solve?                   |
| 3      | Register a provider                                     |
| 4      | Resolve a provider: by injection and by `app.resolve`    |
| 5      | Define a contract (a type or a `Protocol`)              |
| 6      | Choose a factory, an instance, or a class               |
| 7      | Scope: app, request, and transient                      |
| 8      | Handle a missing provider (`MissingProviderError`)      |
| 9      | Understand dependencies, ordering, and validation       |
| 10     | Test registration and resolution, with `with_overrides`  |
| 11     | Design contracts and compatibility                      |
| 12     | Read `xyberos check` and `app.diagnostics()`            |

Use small runnable examples. Start with a simple notification provider before moving on to database and AI providers.

Trust boundaries belong to the plugin chapter, not here: plugins are ordinary trusted in-process Python code, there is no sandbox, and the security lesson in Part 7 says so before it shows how to load one.

### Explain what the registry is not

Beginners should learn the distinction between:

- Provider registry: records which implementation answers a contract, and where it came from.
- Dependency injection: supplies a registered provider to a component that declares it.
- Module: a package plus a composition root; there is no runtime "module" object to register.
- Plugin: extends the application through a defined contract, and is the mechanism for reusable functionality.
- Workflow engine: coordinates a sequence of operations.

These mechanisms may interact, but they should not be taught as interchangeable concepts. The tutorials should follow XYBEROS 2.0's actual contracts rather than inventing a parallel abstraction.

## 7. Part 6 — Creating modules

Teach modules as the way to organize reusable application functionality.

Use one example throughout: a reusable User Management module.

### Tutorial sequence

1. What is a module?
2. When should functionality become a module?
3. Create a minimal module.
4. Define its public interfaces.
5. Register its providers with `app.provide`.
6. Integrate it with the application lifecycle (eager providers, and `start`/`stop` where it owns resources).
7. Add configuration.
8. Expose its providers to the application.
9. Connect the module to a database.
10. Add tests.
11. Package and reuse the module in another application.
12. Handle module dependencies and initialization failures.

### Example module architecture

### User Management Module

Public interface

UserService · UserRepository contract

Business logic

Create users, update profiles, validate rules

Infrastructure

Database adapter, migrations, queries

Runtime integration

Register dependencies, configuration, and lifecycle hooks where supported

Xyberos has no runtime "module" object: a module is an application package plus a composition root, and the runtime extension mechanism is the trusted plugin contract. Teach the actual registration API — `app.provide`, `app.add_plugin`, and `Plugin.register` — not a hypothetical one.

## 8. Part 7 — Creating and using plugins

Modules and plugins deserve separate chapters because their responsibilities can overlap without being identical.

A useful teaching distinction is:

- A module packages functionality and its dependencies.
- A plugin extends or customizes an existing application's or runtime's behavior through a defined extension point.

For example, a notification module might provide notification services. Separate plugins might register an email provider or a custom notification handler—if XYBEROS's plugin contracts support those extension points.

### Plugin tutorial sequence

| Lesson | What to cover                           |
| ------ | --------------------------------------- |
| 1      | What plugins are and why they exist     |
| 2      | Module vs. plugin                       |
| 3      | Explore the plugin contract             |
| 4      | Create a minimal plugin                 |
| 5      | Register the plugin                     |
| 6      | Configure and initialize it             |
| 7      | Add a custom handler or provider        |
| 8      | Use a plugin in an application          |
| 9      | Manage plugin dependencies and ordering |
| 10     | Test, debug, and distribute plugins     |
| 11     | Handle plugin failures                  |
| 12     | Security and trust boundaries           |

Important security lesson: if plugins execute as trusted in-process Python code, they are not sandboxed. Only install trusted plugins, and explain the implications before showing how to load third-party extensions.

## 9. Part 8 — Advanced topics

After the beginner and intermediate tutorials, add a reference-oriented section for experienced developers.

- Custom dependency providers.
- Advanced configuration and lifecycle hooks.
- Custom HTTP handlers and middleware, where supported.
- Database migrations and transaction boundaries.
- Workflow branching, retries, timeouts, and error handling.
- Multi-step work that outlives the process, using the durable executor — experimental, single host, one journal, at-least-once effects (ADR 0011).
- AI provider adapters and structured output.
- Custom tools, and the embedding-based retrieval you build yourself (there is no knowledge provider to configure).
- Observability, metrics, tracing, and cost tracking.
- Testing modules and plugins independently.
- Performance and concurrency.
- Security hardening.
- Deployment and operational troubleshooting.
- Architecture internals and extension design.

A future Cognitive Kernel section can demonstrate how to build a specialized cognitive module on top of the runtime without making the kernel a prerequisite for ordinary applications.

## 10. Make the documentation behave like W3Schools

The tutorial structure is only half the project. The presentation and learning experience matter just as much.

Runnable examples

Every lesson includes a complete example that readers can copy, run, and modify, and the page shows that example by including the file rather than restating it: code lives under `examples/`, one module per lesson, and the module is what CI runs. Keep examples small enough to understand without navigating multiple files.

Exercises and quizzes

Include a small task after each lesson, followed by an optional solution and explanation. Ask learners to predict behavior before running the code.

Progressive examples

Reuse the same application throughout each learning path. Show the code changes between lessons rather than replacing the entire project every time.

Tutorials plus API reference

Tutorials teach a concept step by step. Reference pages document every public API, parameter, return value, exception, and configuration option. Keep the two types of documentation separate.

The reference is generated from the repository's `docs/` directory from the first release, rather than linked out to GitHub and migrated later. `docs/` stays the only copy of each guide: the build copies it into the rendered output under `/reference/`, and CI asserts the copy is generated rather than committed, so no guide is ever maintained in two places.

### Suggested website layout

- Left sidebar: tutorial chapters and lessons.
- Main content: explanation, diagrams, code, and exercises.
- Right sidebar: page contents, prerequisites, and related topics.
- Code examples: copy button, expected output, and links to complete examples.
- Navigation: Previous lesson, Next lesson, and learning-path progress.

An online code playground would be useful eventually, but it is not necessary for the first release. Because XYBEROS applications can use databases and external AI providers, local runnable examples with clearly documented setup instructions are a practical starting point.

## 11. Recommended development order

Do not write every tutorial before validating the underlying APIs.

All seven phases below belong to the first release, and all three learning paths ship together. The sequence is a delivery order — Fundamentals and Traditional, then AI, then Hybrid — not a publishing order.

## Documentation roadmap

The counters and the phase list are generated from lesson front matter (`path`, `lesson`, `status`, `tier`) at build time, so they cannot go stale. A hand-typed "0 of 7" is wrong after the first merge.

Phase 1 — Verify

Audit the architecture, source code, public APIs, examples, and tests. Create a feature-support matrix, and stand up the site build with the `/reference/` pages generated from `docs/`.

**Complete.**

Phase 2 — Fundamentals

Publish installation, project creation with `xyberos new`, the minimal application, lifecycle, configuration, dependency injection, and the provider registry tutorials.

**Complete:** fifteen lessons, all verified.

Phase 3 — Traditional apps

Build the User Management application from minimal code to a working web application.

**Complete:** twelve lessons, from a first route to a deploy step, over one application in `examples/user_management/`.

Phase 4 — AI apps

Build the AI Assistant progressively, verifying each model, tool, and workflow integration, and labelling the memory, knowledge, and retrieval lessons as application code the reader writes.

**Complete:** seventeen lessons, from the facade and its capability checks to evaluation and security, each running with no model service. Nine are labelled *you build it*, and the durable page states its experimental tier.

Phase 5 — Hybrid apps

Build the Smart Support Desk using traditional business logic plus AI capabilities.

**Complete:** ten lessons over one application in `examples/support_desk/`, from ticket CRUD to settled
usage rows, all written to the [design](hybrid-design.md) that was fixed before the first line of it —
and the boundary that design draws is asserted by `tests/integration/test_hybrid_support_desk.py` rather
than described by it.

Phase 6 — Extensibility

Document module creation, plugin creation, registration, configuration, testing, and distribution.

**Complete:** four verified pages under `site/extend/` — the provider registry, modules, plugins, and
database providers — each built on a walkthrough module in `examples/learn_extend/` that the site harness
runs and compares with the page's own output block, plus the two integration tests that hold the claims a
transcript cannot ([`tests/integration/test_extension_provider.py`](../tests/integration/test_extension_provider.py),
[`tests/integration/test_extension_plugins.py`](../tests/integration/test_extension_plugins.py)).

Phase 7 — Production

Add deployment, security, observability, troubleshooting, and advanced architecture guides.

**Complete:** seven verified pages under `site/production/` — the section index, deploy, observability,
troubleshooting, security boundaries, performance and concurrency, and internals — built on eleven
walkthrough modules in `examples/learn_production/` that the harness runs and compares with each page's
own output block. Three integration tests hold what a transcript cannot
([`tests/integration/test_production_deploy.py`](../tests/integration/test_production_deploy.py),
[`test_production_shutdown.py`](../tests/integration/test_production_shutdown.py),
[`test_production_boundaries.py`](../tests/integration/test_production_boundaries.py)), and
`site/extend/index.md` dropped its `planned` status with every deferred topic given a home, which is
what opens the release gate.

## Final recommendation

Organize the documentation around three learning paths and one extensibility reference:

1. Build Traditional Apps — from minimal code to a complete web application.
2. Build AI Apps — from the first model call to workflows and agent behavior.
3. Build Hybrid Apps — combine business logic, persistence, web interfaces, and AI.
4. Extend XYBEROS — understand the runtime, the provider registry, modules, plugins, and advanced integrations.

Before publishing, validate every example against the current repository and run it in a clean environment. Mark features as built-in, optional integration, third-party dependency, or planned so that beginners never confuse a conceptual example with a supported XYBEROS feature.

The first milestone is a complete Fundamentals section and one working Traditional Apps tutorial: that establishes the teaching format and verifies the framework's real developer experience before the remaining lessons are written. It is not a release boundary. All three learning paths, and the extensibility reference, ship together in the first release.

## 12. Decisions taken

These were open when this plan was written and are now settled. The execution detail — repository layout, the build, the verification harness, phases, and exit criteria — is in [implementation.md](implementation.md).

| Decision | Resolution | Consequence |
| -------- | ---------- | ----------- |
| Host | This site replaces the content of `docs.xyberos.com`, and the 1.x line's documentation is served from that line's own repository | **Done.** The stale Cloudflare deployment that held the domain was deleted, the 1.x repository was subsequently renamed to `xyberos/xyberosv1.0-deprecated`, the domain is attached to this line's Cloudflare Worker, and `[project.urls] Documentation` is `https://docs.xyberos.com/` — release-guide precondition 4 |
| Site build | MkDocs with the Material theme: `mkdocs.yml` at the repository root, `docs_dir: site` | The content stays Markdown and the toolchain stays Python; nothing under `site/` becomes an importable package, because `site` is a standard-library module |
| `docs/tutorial.md` | Retired into the Fundamentals path | Its chapter modules and `<!-- output: -->` blocks move with it, so the suite that already runs every chapter keeps working |
| API reference | Generated from `docs/` from the first release | One copy of every guide is maintained; the build copies it into `/reference/` and CI asserts the copy is generated rather than committed |
| Release scope | All three learning paths ship in one release, delivered in this order: Fundamentals + Traditional, then AI, then Hybrid | The seven phases below are all inside the first release. The order is a delivery order, not a publishing order: the release waits for all three paths |
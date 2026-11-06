# Xyberos 2.0 documentation site — implementation plan

Companion to [site.md](site.md). That page decides *what to teach and in what order*. This page
decides *how it is built, where the content lives, and what has to change in the plan before the
first page is written*.

Status: proposal. Nothing here is implemented yet.

## 1. Purpose

`site.md` describes a progressive, project-based tutorial series in seven parts, with three learning
paths (traditional, AI, hybrid) plus an extensibility reference. The shape is sound. What it lacks is
the part that decides whether the result is trustworthy:

- **A correction pass.** Several lessons teach a framework that Xyberos 2.0 deliberately is not — an
  authentication system, a multi-database integration layer, a template engine, a memory/RAG layer.
  Each of those is a refusal with a recorded reason, and a tutorial that teaches against a decision is
  the fastest way to make a reader distrust the rest.
- **A single source of truth for code.** The repository already runs every tutorial chapter and
  compares its real output with the output printed in the documentation
  ([`tests/integration/test_tutorial.py`](../tests/integration/test_tutorial.py)). A second,
  hand-written set of examples would drift within one release.
- **A site build.** There is no static-site generator, no theme, and no CI job that renders pages
  today. `docs/` is plain Markdown rendered by GitHub.

This plan keeps `site.md`'s structure, corrects what the code contradicts, and reuses the verification
machinery the project already has rather than inventing a parallel one.

## 2. How this review was done

Every factual claim below is checked against the repository at the current commit. Sources:

| Claim area | Evidence read |
| --- | --- |
| Public surface, tiers | [`src/xyberos/__init__.py`](../src/xyberos/__init__.py), [`docs/stability.md`](../docs/stability.md) |
| Runtime API shape | [`src/xyberos/app.py`](../src/xyberos/app.py), [`src/xyberos/runtime/dependencies.py`](../src/xyberos/runtime/dependencies.py) |
| HTTP capabilities and limits | [`src/xyberos/http/adapter.py`](../src/xyberos/http/adapter.py), [`src/xyberos/http/routing.py`](../src/xyberos/http/routing.py), [`src/xyberos/http/middleware.py`](../src/xyberos/http/middleware.py) |
| Database scope | [ADR 0016](../docs/adr/0016-database-providers-are-an-extension-point.md) |
| Identity refusal | [ADR 0014](../docs/adr/0014-no-identity-or-authorization-model.md) |
| AI scope | [`src/xyberos/ai/`](../src/xyberos/ai), [`docs/ai.md`](../docs/ai.md) |
| Plugin trust model | [`src/xyberos/plugins/protocol.py`](../src/xyberos/plugins/protocol.py), [ADR 0007](../docs/adr/0007-trusted-plugins.md) |
| Install and version range | [`pyproject.toml`](../pyproject.toml), [`docs/stability.md`](../docs/stability.md) |
| Existing tutorial and its harness | [`docs/tutorial.md`](../docs/tutorial.md), [`examples/tutorial/`](../examples/tutorial), [`tests/integration/test_tutorial.py`](../tests/integration/test_tutorial.py) |
| CI expectations | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) |
| Documentation URL constraint | [`docs/release.md`](../docs/release.md) precondition 4 |

Both questions left open in the first draft of this plan — the public host and the site generator — were
owner decisions rather than facts to verify, and both are now answered in section 13.

## 3. What `site.md` gets right — keep it

1. **One capability per lesson, working code first.** The "smallest valid program first, explain it
   after it runs" rule matches the repository's own [`getting-started.md`](../docs/getting-started.md)
   and is the correct teaching order here.
2. **The lesson template** (what you build, prerequisites, code, run it, expected output, line
   explanation, common mistakes, exercise, next). Nine headings is more structure than most tutorial
   sites have, and it is exactly what makes a page mechanically checkable — see section 9.
3. **Separating concepts that are genuinely separate** (model, memory, knowledge, tool, intent,
   workflow, agent) before combining them. The runtime does the same: the workflow engine, the AI
   facade, and the plugin registry are three modules that never import each other.
4. **"AI augments business logic, it does not replace it."** This is the repository's own position
   ([ADR 0014](../docs/adr/0014-no-identity-or-authorization-model.md), [`docs/positioning.md`](../docs/positioning.md)),
   and the Smart Support Desk is the right worked example for it.
5. **`site.md` §10's "explain what the registry is not"** — the list separating registry, dependency
   injection, module, plugin, and workflow. Keep the intent, fix the names (section 4.1).
6. **Validating every example in a clean environment before publishing.** Already the project's
   release habit.

## 4. Corrections to make before the first page is written

Each item is: what `site.md` says, what the code says, and the required change. These are ordered by
how badly the uncorrected version would mislead a reader.

### 4.1 "Capability Registry" is not a runtime concept — teach the provider registry

**`site.md` §6** gives the Capability Registry a twelve-lesson sequence and a diagram in which the
application asks for an email service and the registry *picks* an implementation at runtime.

**The code** has no `CapabilityRegistry`, and no runtime provider selection. What exists is:

- `ProviderRegistry` and `app.provide(contract, factory=… | instance=…, scope=…, eager=…, close=…)`
  — registration is explicit and happens at composition time.
- `app.resolve(T)` and `Annotated[T, Inject()]` — resolution, with `Scope.APP`, `Scope.REQUEST`,
  `Scope.TRANSIENT`.
- `PluginRegistry` and `app.add_plugin(...)` — plugins register providers *during* `Plugin.register`,
  and `source` in diagnostics records which plugin registered what.
- `app.diagnostics().render()` and `ProviderInfo` — the answer to "where did this provider come
  from?". This is the closest thing to a registry *view*, and it is the feature worth a tutorial.
- The word "capability" already means something else in the codebase: declared *model* capabilities
  (`ModelCapabilities`, enforced by `AIUnsupportedCapabilityError`) and plugin-provided capabilities
  ([`plugins/protocol.py`](../src/xyberos/plugins/protocol.py)).

**Required change.** Retitle Part 5 to *"The provider registry and dependency injection"*. Replace the
runtime-selection diagram with a composition-time one: the application chooses the factory, the
registry records it, `Inject()` resolves it. Delete lesson 12 ("capability permissions and trust
boundaries") and move its content to the plugin chapter (trust boundary = trusted in-process code,
ADR 0007). Add a lesson that does not exist in `site.md`: **read `xyberos check` output and
`app.diagnostics().render()`**, because that is the debugging loop a reader needs on day two.

### 4.2 Authentication: teach the sanctioned shape, not sign-up and sessions

**`site.md` §3 Stage D** lists "Register, log in, log out, and manage sessions" and "Role-based access
control" for the User Management project.

**The code** refuses this on purpose. [ADR 0014](../docs/adr/0014-no-identity-or-authorization-model.md):
no identity, tenancy, or authorization model, and none will be added. *Sessions and CSRF were later
split out of that refusal by
[ADR 0024](../docs/adr/0024-sessions-and-csrf-are-middleware-in-the-http-module.md): they ship as
`xyberos.http` middleware, while the identity and authorization decisions stay exactly where this
section puts them.* The sanctioned shape is
a component that *verifies* an incoming assertion and returns a principal, the principal passed to
services as a required argument, and the tenant taken from the principal — never from the payload or
`contextvars`. [`examples/tenancy/`](../examples/tenancy) is that pattern, tested, including the case
where a payload claims a different tenant.

**Required change.** Replace Stage D's lesson with *"Trusted identity arrives from upstream"*: verify
an assertion header (and strip it at the edge), pass the principal as an argument, scope queries by
it, answer `401`/`403` through `HttpError`, and fake the principal in tests with `app.with_overrides`.
If the series also wants a "roll your own login" chapter, it must live in the *third-party patterns*
section, be labelled as application code the reader writes, and repeat ADR 0014's reason. A beginner
tutorial that quietly builds a half-auth layer reproduces the exact failure ADR 0014 exists to avoid.

### 4.3 Databases: one shipped provider, and an extension point with a conformance suite

**`site.md` §3's database table** presents PostgreSQL, MySQL/MariaDB, Redis, and a vector database as
things to teach "by comparing concepts", with a caution note at the end.

**The code** ships SQLite through SQLAlchemy Core and `aiosqlite`, and nothing else
([ADR 0016](../docs/adr/0016-database-providers-are-an-extension-point.md)). `DatabaseProvider` is
three members — `transaction()`, `retrying()`, `health()` — over an `AsyncConnection`; the honest scope
of the seam is **any async SQLAlchemy dialect**. `xyberos.database.testing.assert_provider_contract`
exists so a third-party provider can prove itself in one call. Redis is not a `DatabaseProvider` at
all, and no vector store, embedding index, or retrieval layer ships anywhere in the repository.

**Required change.** Split the table into three columns — *shipped*, *extension point*, *not provided* —
and keep the caution note, promoted from a footnote to the section's opening sentence. PostgreSQL
becomes a two-lesson sequence: (a) `DatabaseProvider` is portable, `SqliteSettings` is not; (b) write a
provider package and run the conformance suite. Redis and vector search move to "you add a client
library; the runtime is not involved", with no Xyberos import in the code sample.

### 4.4 Server-rendered HTML: say who supplies the templates

**`site.md` §3 Stage E** teaches template inheritance, HTMX, Alpine.js, and Tailwind as part of the
framework progression.

**The code**: `xyberos.http` ships route compilation, the ASGI adapter, and the middlewares the
application passes (correlation ID, error mapping, request scope, request metrics, sessions, CSRF).
There is **no** template engine and **no** static-file mount. A handler *may* return any Starlette
`Response` —
[`tests/http/test_adapter.py`](../tests/http/test_adapter.py) returns a `PlainTextResponse` from a
handler and the adapter passes it through — so `HTMLResponse` and Starlette's `Jinja2Templates` work;
they are simply application-supplied, exactly like `uvicorn` is.

**Required change.** Keep the Stage E lessons — this is genuinely useful content and the hybrid project
needs it — but open the stage with a one-paragraph boundary statement: *the framework routes and
serializes; you choose the template engine, and this chapter uses Starlette's.* Add Jinja2 and
`starlette` (for `StaticFiles`) to the chapter's prerequisites, and say that nothing in the chapter is
a Xyberos API. That also protects the AI sections, which are read by the same audience.

### 4.5 AI: separate what ships from what the reader builds

**`site.md` §4** lists sixteen lessons, including memory (8), knowledge (9), RAG (10), intents (12),
and agent behaviour (14).

**The code** ships, in core with no SDK dependency: the provider-neutral `AIFacade` (`chat`,
`structured`, `stream`, `embed`, `health`, `invoke_tools`, `chat_with_tools`), the contracts,
structured output over a **closed JSON Schema subset** (`check_schema`, `validate_payload`), an
allowlisted tool layer (`Tool`, `ToolSet`, `ToolContext`, `ToolResult`), and the deterministic
`FakeModelProvider`. Ollama is the one vendor adapter and needs the `ollama` extra. There is **no**
memory store, **no** knowledge/document loading, **no** vector index, **no** intent classifier, and
**no** agent loop in the package.

**Required change.** Split every AI lesson into what the runtime provides and what the reader writes,
and mark it in the lesson header (`Built-in` / `You build it` / `Third-party`). Concretely:

- Memory, knowledge, and RAG become *"you build it"* lessons whose only framework imports are
  `AIFacade.embed`, a table in SQLite, and `structured`. Say plainly that there is no framework
  retrieval layer, so no reader waits for one.
- Intents become a `structured`-output classification lesson — which is how you would build one today.
- Agent behaviour becomes a lesson that composes `ToolSet` with the workflow engine, and states that
  the runtime has no agent loop.
- Add one lesson `site.md` omits: **test the AI path with no model service** using
  `FakeModelProvider` and declared `ModelCapabilities`. The repository treats this as a
  differentiator; a tutorial that only shows a live Ollama call hides it.

### 4.6 Durable execution is experimental — name it once, and fence it

**`site.md` never mentions durable execution.** It exists ([`xyberos.durable`](../src/xyberos/durable),
[ADR 0011](../docs/adr/0011-durable-executor-contract.md)) and is the only **experimental** tier
surface ([`docs/stability.md`](../docs/stability.md)), with single-host, one-journal, at-least-once
effects as contract terms rather than caveats.

**Required change.** Add one page under *Extend Xyberos* (not on any learning path) titled
*"Multi-step work that outlives the process (experimental)"*, opening with the tier and the
non-guarantees verbatim in spirit. It is the single most interesting thing in the repository for a
senior reader, and leaving it out of the plan means the site launches without it.

### 4.7 Remove the CDN image links

**`site.md`** links out to five `https://images.openai.com/static-rsc-4/...` URLs as if they were
references (three dashboards, a SQL walkthrough, a chapter listing). They are ephemeral image-CDN
handles attached to a chat session: they expire, they cite nothing, and one points at a commercial
third-party course. A documentation plan is judged by its citations.

**Required change.** Delete all six. Replace with primary sources: Starlette's own documentation for
templates/static files, the HTMX and Alpine.js project docs, and, where a design reference is wanted,
an openly-licensed example the project can actually credit. If a visual is needed, keep it in the
repository.

### 4.8 Compute the roadmap counters

**`site.md` §11** has "Documentation roadmap — 0 of 7 complete" and a "Phase 1 — Verify" list. Typed
counters become wrong on the first merge.

**Required change.** Each lesson file carries front matter (`path`, `part`, `lesson`, `status`,
`tier`, `verified_at`). The roadmap page is generated from that front matter at build time, so the
counter, the sidebar, and the previous/next links all come from one place. Section 8 covers the
layout; section 9 makes `status: verified` mean something.

### 4.9 Do not write a second set of examples

[`docs/tutorial.md`](../docs/tutorial.md) was already a thirteen-chapter tutorial whose every chapter
module runs in CI and whose every printed output block is compared with the real output — the
`<!-- output: chapter1_first_app -->` convention, which the site now carries as
`<!-- output: fundamentals04_your_first_application -->`. [`examples/`](../examples) holds ten worked
example directories, each exercised by an integration test. A new site with its own hand-written
snippets would be unverified content, and it would be the second place to update when an API moves.

**Required change.** The site is a *view* of content that already runs:

- Lesson code is included from files by the snippet-include mechanism, never retyped.
- Lesson output is the existing `<!-- output: ... -->` convention, extended to site pages.
- New lesson code is added to `examples/tutorial/` (or a new `examples/learn_*` directory) first, with
  a `main()` entry point, so the existing harness runs it before the page is published.

Section 8 gives the file layout; section 9 gives the test that enforces it.

### 4.10 Put the CLI and the test doubles in the beginner path

Neither appears in `site.md` Part 1, and both are the fastest route to a reader's first success:

- `xyberos new` writes a project that imports, runs, and passes its own test — CI asserts exactly that
  against the built wheel ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)). Lesson 3 should
  be `xyberos new`, not a blank file. Add lesson *"Read `xyberos check`"* immediately after: it
  validates settings, the provider graph, and handler signatures without starting the application.
- `create_test_client`, `temporary_database`, `FakeModelProvider`, and `ManualClock` are preview-tier
  *shipped* test doubles. The current plan defers testing to Part 8; the repository's strongest claim
  is that an AI path is testable with no SDK and no model service, so one testing lesson belongs in
  Part 1 and the AI testing lesson in Part 3 (see 4.5).

## 5. Feature-support matrix

The `site.md` closing instruction is to "mark features as built-in, optional integration, third-party
dependency, or planned". The matrix is published as
[`site/feature-support.md`](feature-support.md), which is its only copy: it is the source of the
per-lesson label, and the label is enforced rather than decorative.

Four labels, and one rule about them — nothing is described as supported unless a test in this
repository exercises it:

| Label | Meaning |
| --- | --- |
| **Built-in** | Ships in the framework. An `(extra)` note means an optional install. |
| **Extension point** | The framework ships the contract and a conformance suite; you ship the implementation. |
| **You add it** | A third-party library or server the framework deliberately does not depend on. |
| **You build it** | Nothing ships. The lesson is the implementation. |

Three refusals appear in that matrix as absences by decision rather than by omission, and each is
published with its reason: no identity or authorization model
([ADR 0014](../docs/adr/0014-no-identity-or-authorization-model.md)), one shipped database provider
plus a documented extension point
([ADR 0016](../docs/adr/0016-database-providers-are-an-extension-point.md)), and durable execution
marked experimental with its non-guarantees stated
([ADR 0011](../docs/adr/0011-durable-executor-contract.md)).

## 6. Terminology map

Use the plan's left-column words in prose and the code's own names in code. The map is published as
[`site/terminology.md`](terminology.md), which is its only copy.

The entry that matters most is the one that no longer exists: there is no "Capability Registry". A
provider is registered with `app.provide`, resolved through `Annotated[T, Inject()]` or `app.resolve`,
and inspected with `app.diagnostics()` — and *capability* already means a declared model capability,
checked before any call is made.

## 7. Content architecture

Keep `site.md`'s three learning paths and add the reference surface as a fourth, top-level section.
Number lessons **within a path**, so inserting a lesson never renumbers a published URL.

```
/learn/traditional/   1..n   Build Traditional Apps
/learn/ai/            1..n   Build AI Apps
/learn/hybrid/        1..n   Build Hybrid Apps
/learn/fundamentals/  1..n   Shared prerequisites (site.md Part 1)
/extend/              …      Registry, modules, plugins, providers, durable, internals
/reference/           …      Existing docs/ guides, linked or mounted (section 10)
```

`site.md`'s Parts 1–8 map onto this as: Part 1 → `/learn/fundamentals`; Parts 2 and 5 → the traditional
path (Part 5 becomes the registry chapter inside it); Parts 3 and 4 → the AI path and the hybrid path;
Parts 6, 7, 8 → `/extend`. The mapping is recorded in the site's front matter so a reader can find a
lesson from either numbering.

Every lesson file:

```markdown
---
path: traditional
lesson: 4
title: Routes, path parameters, and request bodies
tier: built-in
status: draft          # draft | reviewed | verified
prerequisites: ["/learn/fundamentals/3"]
example: examples/tutorial/traditional04_routes.py
verified_at:            # set by the harness, not by hand
---

<!-- snippet: examples/tutorial/traditional04_routes.py -->
<!-- output: traditional04_routes -->
```

## 8. Repository layout and content pipeline

```
mkdocs.yml                   # repository root; docs_dir: site, site_dir: build/site (section 10)
site/
  site.md                    # the content plan, linked from the navigation
  implementation.md          # this file, linked from the navigation
  index.md                   # the home page
  feature-support.md         # the availability matrix, canonical (section 5)
  terminology.md             # the term-to-API map, canonical (section 6)
  hybrid-design.md           # the design phase 5 is written to (critical path, section 11)
  learn/fundamentals/*.md    # lessons, one page each
  learn/{traditional,ai,hybrid}/index.md
  extend/index.md
  appendices/*.md            # service-dependent pages, outside every path
  reference/                 # generated from docs/ by scripts/reference.py; git-ignored
  roadmap.md                 # generated from front matter by scripts/roadmap.py; git-ignored
  scripts/frontmatter.py     # page metadata: front matter parsing, lesson contract, navigation
  scripts/roadmap.py         # writes roadmap.md; --check and --release are the gates
  scripts/reference.py       # renders docs/ into site/reference/, rebasing links
  scripts/snippets_hook.py   # renders `<!-- snippet: -->` markers; checks the built pages for them
  scripts/build.py           # one command: generate, then mkdocs build --strict, then verify
examples/
  tutorial/                  # the chapters that still have no home in a path
  user_management/           # the application the Traditional Apps path grows (phase 3), plus its
                             # migrations/ and migrate.py entry point (lesson 7)
  learn_fundamentals/        # lesson code, one module per lesson, each with main()
  learn_traditional/
  learn_ai/
  learn_hybrid/
tests/
  site/                      # the harness in section 9: site_pages.py and four test modules
```

Rules that make the pipeline work:

1. **Code lives in `examples/`, prose lives in `site/`.** A lesson page contains no code it does not
   include by snippet. Reviewing a lesson means reviewing a page and a module together. The page's form
   is `<!-- snippet: path -->`, which is what the harness reads; `scripts/snippets_hook.py` turns that
   marker into MkDocs's own `--8<--` directive, and `build.py` then checks the *built pages* for a
   marker that survived — because a missing hook publishes every lesson headless, claiming code and
   showing none, and no test of the source can see it.
2. **One `main()` per lesson module**, printing its result, so the existing harness pattern applies
   without modification. `examples/tutorial/chapter*.py` already follows this and `tests/integration/
   test_tutorial.py` imports `module.main`.
3. **Output blocks are claims.** `<!-- output: <module> -->` plus a `text` fence is the assertion
   (section 9). Renaming a module renames its output block in the same commit.
4. **Front matter is data.** `scripts/roadmap.py` reads it to write `roadmap.md`, and its `--check`
   gate refuses a lesson that is not in the navigation, that reuses a `path` and `lesson` pair, or
   that declares no example. The navigation itself is written explicitly in `mkdocs.yml`: a page
   reaches the sidebar by being listed, not by being discovered.
5. **Windows and POSIX commands are both shown**, as content tabs, because CI is Linux and the
   repository's own instructions are PowerShell. `site.md` assumes a single shell throughout.
6. **Nothing under `site/` is importable as a package.** `site` is a standard-library module that
   Python imports during start-up, so a `site/` directory with an `__init__.py` — or an invocation
   such as `python -m site.scripts.roadmap` — can bind to it and fail in a way that looks unrelated to
   the site. Build tools are run by file path (`python site/scripts/roadmap.py`), the directory holds
   no `__init__.py`, and the harness in section 9 lives in `tests/site/`, which is not on the
   application path.
7. **`/reference/` is generated from `docs/`, and `docs/` stays the only copy.** The build copies the
   guides into the rendered output under `/reference/`; CI asserts the rendered copy matches a fresh
   copy of `docs/`, so a guide cannot be edited in two places. No guide is rewritten to suit the site,
   and a site page links to a `docs/` path rather than restating it.
8. **`site/` is the source directory, so the build writes elsewhere.** `site_dir` is `build/site`,
   because MkDocs's default output directory is `site/` — now the tracked source, which a build would
   overwrite. The repository's `.gitignore` no longer ignores `site/` either: an ignore rule on the
   source directory is how a carefully written plan ends up in no commit at all, which is what
   happened before this plan was applied.
9. **Service-dependent content lives in `/appendices/`, outside every path.** A page that needs a live
   model service is not a lesson: the lesson teaches the mechanism offline, and the appendix shows the
   real service with a command-level assertion instead of an output block (section 9). This is what
   keeps "every lesson is runnable in CI" true rather than aspirational.

## 9. Verification harness

The project's existing convention is that documentation is a set of claims the suite checks. Extending
it is cheaper than any alternative and it is the reason a reader can trust the pages.

`tests/integration/test_tutorial.py` already:

- imports each chapter module and runs `main()`;
- compares the captured stdout with the `<!-- output: ... -->` block in `docs/tutorial.md`;
- asserts every chapter module has a documented output, in both directions;
- checks that every relative link in the tutorial points at a file that exists;
- verifies a quoted `uvicorn --factory` target actually constructs a Starlette application.

Because `docs/tutorial.md` is retired into the Fundamentals path (section 13, decision 3), the harness
follows the content: the chapter modules move to `examples/learn_fundamentals/` and the output blocks
move to the corresponding lesson pages in the same commit. A gradual move would leave the content the
suite checks and the content a reader reads in different places, so it is atomic.

Extend the same pattern, in a new `tests/site/` package, to cover the site. This is what was
built in phase 1 — `tests/site/site_pages.py` loads the pages and calls the scripts, so a rule lives
in one place and the suite is its second reader:

| Test | Assertion | Built |
| --- | --- | --- |
| `test_the_run_guards_its_own_environment` | `xyberos` imports from this checkout, so a version mismatch reports as an environment failure rather than as lesson drift | `test_lessons.py` |
| `test_there_is_at_least_one_lesson` | a suite over an empty set does not pass for the wrong reason | `test_lessons.py` |
| `test_every_example_module_is_claimed_by_a_lesson` | every module under `examples/learn_*/` is shown by some page — as a lesson's example, or as an answer a page includes | `test_lessons.py` |
| `test_every_documented_output_is_produced_by_its_module` | parametrised over *every* output block on the site, including an exercise answer's: real stdout equals the documented block | `test_lessons.py` |
| `test_a_testing_lesson_passes_as_a_test` | a lesson whose subject is testing is verified by running it as a test, since its output is pytest's own timing | `test_lessons.py` |
| `test_a_command_lesson_prints_what_the_page_says` | a lesson that quotes a command has its real transcript compared with the block | `test_lessons.py` |
| `test_lesson_snippet_includes_resolve` | every include exists, and lives under `examples/` | `test_lessons.py` |
| `test_every_page_marker_becomes_a_directive` | every marker a page writes renders a directive that names that page's own snippet paths — a claim that is merely *named* is not a claim | `test_pages.py` |
| `test_mkdocs_loads_the_snippet_hook` | `mkdocs.yml` wires the hook that performs that translation, and the file it names exists | `test_pages.py` |
| `test_the_snippet_hook_renders_the_canonical_marker` | the hook translates the marker, including the spaced spelling, and leaves other text alone | `test_pages.py` |
| `test_a_snippet_is_fenced_by_its_own_language` | the fence names the language and the file, so an include is highlighted and attributable | `test_pages.py` |
| `test_an_included_file_renders_as_a_code_block` | the hook's own output, converted with the extensions the build declares, puts the file's code *inside* a code block — a bare directive splices it into the Markdown stream instead, which is how every snippet on the site once rendered as prose | `test_pages.py` |
| `test_the_navigation_names_every_reference_guide` | the generated reference and the navigation agree in both directions, so a new guide cannot go missing from the Reference tab | `test_pages.py` |
| `test_a_surviving_marker_is_found_in_the_built_output` | the build's post-build check finds a marker in a built page, and does not report a clean one — a gate that always passes is not a gate | `test_pages.py` |
| `test_a_lesson_page_contains_no_hand_written_python` | Python on a lesson page arrives by include — this is what stops the drift in 4.9 | `test_lessons.py` |
| `test_the_pages_satisfy_the_build_rules` | the same gate the build runs, called rather than restated | `test_pages.py` |
| `test_the_stability_guide_is_parseable` | the tier check cannot silently pass because the table stopped parsing | `test_pages.py` |
| `test_an_experimental_import_is_labelled_experimental` | a lesson reaching `xyberos.durable` must say "experimental" on the page | `test_pages.py` |
| `test_a_lesson_imports_only_documented_public_names` | every `xyberos` name a lesson imports is in that module's `__all__` | `test_pages.py` |
| `test_the_site_links_only_to_files_that_exist` | relative links resolve; a link into `/reference/` is checked against `docs/` | `test_pages.py` |
| `test_rendered_reference_matches_docs` | the rendered reference is byte-identical to a fresh render from `docs/` | `test_pages.py` |
| `test_no_appendix_documents_an_output_block` | an appendix may quote a transcript but makes no claim the suite could check | `test_live_appendices.py` |
| `test_appendix_commands_name_real_targets` | every quoted `python -m …` and `python …py` resolves | `test_live_appendices.py` |
| `test_the_live_appendix_runs` | opt-in only: runs the appendix's own commands against the real service | `test_live_appendices.py` |

Every lesson declares how it is checked, and the four modes exist because one mode cannot describe
every subject:

| Mode | What it checks |
| --- | --- |
| `verify: output` | runs the example and compares what it printed — the default |
| `verify: pytest` | runs the example as a test, because a lesson *about* testing has no output to compare: its output is pytest's own timing |
| `verify: command` | runs the command the page quotes and compares the transcript |
| `verify: scaffold` | runs a command in a throwaway directory and compares the *files* it wrote, because a scaffolding command prints absolute paths and its file list is the claim worth checking |

`roadmap.py` refuses a lesson whose mode is missing what that mode needs: an example, a command, an
output block, or a snippet include.

Two of those replace rows this plan originally listed: `test_no_nav_page_is_draft` became part of the
build gate (`roadmap.py` refuses it on every run rather than only in the suite, which is stronger), and
`test_every_lesson_declares_a_tier_and_a_path` became one assertion inside
`test_the_pages_satisfy_the_build_rules` so the check exists once.

CI additions, appended to the existing `quality` job in
[`.github/workflows/ci.yml`](../.github/workflows/ci.yml). The site is built **before** `pytest`,
because two of its pages are generated and the suite verifies the rendered reference against `docs/`:

```yaml
      - run: python -m pip install -e ".[dev,http,database]"
      - run: python site/scripts/build.py --check   # generate, gate, and build strictly
      - run: python -m pytest
      - run: ruff check src tests examples site/scripts
      - run: mypy
```

`--strict` and the two gates are load-bearing: a broken link, an unlisted page, a `draft` lesson in the
navigation, or a lesson with no output block all fail the build. The documentation tooling is in the
`dev` extra (`mkdocs-material`, plus `types-PyYAML` for `mypy`), so the wheel's metadata is unchanged
and the `installed-artefact` job still proves a core-only install imports no optional capability.

A third workflow, opt-in and never gating, runs the live appendices. It is
[`.github/workflows/site-live.yml`](../.github/workflows/site-live.yml): `workflow_dispatch` only,
installing the `ollama` extra, running `site/scripts/build.py`, then
`python -m pytest tests/site/test_live_appendices.py` with `XYBEROS_OLLAMA_LIVE=1`.

It exists so the Ollama appendix is not untested code; it is separate so a missing model service can
never fail a pull request, which is the property the existing live test already protects.

Two harness decisions worth writing down, because both were deliberate in the existing tests:

- **A lesson must be runnable offline, and no released lesson is a draft.** `status: draft` is a working
  state, not a shipped one: `mkdocs build --strict` fails when a nav page is still `draft`, and
  `site/scripts/roadmap.py --check` fails when a lesson has no `<!-- output: -->` block, so a path cannot
  be declared complete while one of its lessons is unverified. The gate is a build failure rather than a
  promise made in a planning document.
- **Service-dependent content is an appendix, not a lesson.** Anything that needs a live model service
  moves to `/appendices/`, outside every learning path, and its assertion is command-level rather than
  output-level: the module imports, the factory constructs a real object, and any quoted command names
  a target that exists — the same check the harness already applies to the tutorial's
  `uvicorn --factory` line. Those appendices are exercised by an opt-in workflow
  (`workflow_dispatch`, `XYBEROS_OLLAMA_LIVE=1`) that mirrors
  [`tests/ai/test_live_ollama.py`](../tests/ai/test_live_ollama.py), and it never gates a pull request
  or the release.
- `status: verified` is set by a script, once the page's tests pass against an installed wheel — not
  against the source tree — so a lesson cannot be verified by an editable install that happens to
  include a symbol the shipped artefact lacks.

## 10. Site stack and UX

**Decided (section 13, decision 2): MkDocs with the Material theme**, pinned, configured by
`mkdocs.yml` at the repository root with `docs_dir: site` and `site_dir: build/site`.

`site_dir` is not cosmetic. MkDocs writes to `site/` by default, which is where this plan's source
lives, and the repository's `.gitignore` already ignored `site/` as a build directory — so the two
defaults together would build the site on top of its own source and keep `site.md` out of every
commit. `build/` is already ignored, the bare `site/` ignore rule is gone, and the strict build in CI
is what proves the ordering.

The reasons for that choice, in order: the content is Markdown and stays Markdown, so a lesson is reviewable as a diff and
usable on GitHub without the build; the toolchain is Python, which the project already installs and
caches in CI, rather than a second (Node) ecosystem; snippet includes, content tabs for Windows/POSIX,
per-page contents, previous/next, and built-in search cover everything `site.md` §10 asks for; and
`mike` adds versioned docs later without a redesign. An Astro/Starlight build is the better host for a
code playground, and a playground is explicitly *not* required for the first release — revisit when the
playground is real, not before.

The nav is written explicitly. `site.md` and this file are **linked** from it rather than built into
the site: their links are repository-relative, which is what makes them correct where they are read,
and a documentation build resolves links against its own source directory. They are excluded with
`exclude_docs`, so the strict build does not report their links as broken.

Three navigation decisions were settled by measuring the built site, and each replaced a guess:

- **Areas are tabs, and that is what fixed the sidebar.** `navigation.tabs` splits the four learning
  paths, the extension guides, the reference, and the project pages into eight top tabs, so the sidebar
  holds one area rather than every page: without them all four paths and the reference rendered into one
  sixty-entry list, which is the state a reader reported. `navigation.instant` then keeps that sidebar
  and the search index across a click instead of re-fetching them per page.
- **`navigation.prune` is deliberately not used.** It is the documented way to shrink a large
  navigation, and it was tried: with it, a page under `reference/adr/` rendered *no* sidebar at all,
  whether the reference was grouped into sections or listed flat. The evidence was the built HTML, not
  the documentation for the flag.
- **The reference is named in the nav, one entry per guide.** A Reference tab whose sidebar was a
  single link to its index page is a dead end for a section a reader browses;
  `test_the_navigation_names_every_reference_guide` now fails when the named set and the generated tree
  disagree, so `docs/` gaining a file is a failing test rather than a page nobody can reach. The entry
  for `implementation.md` is absent on purpose: it is excluded from the build, and the same test is what
  keeps an excluded page out of the navigation.

Two structural choices follow, and one of them was only discovered by building the site:

1. **The existing `docs/` guides stay where they are, and `/reference/` is generated from them.** One
   copy of each guide is maintained; `site/scripts/reference.py` renders `docs/` into `site/reference/`
   before the build, the rendered tree is git-ignored, and `test_rendered_reference_matches_docs`
   compares it byte for byte with a fresh render. The script's one transformation is link rewriting: a
   guide's links are written for GitHub, so a link that stays inside `docs/` is rebased for its new
   location and a link that escapes `docs/` becomes a repository URL — otherwise a guide that reaches
   `../docs/plugins.md` would break the moment it moved.
2. **The host is decided: this site replaces the content of `docs.xyberos.com`.** The 1.x line's
   documentation points at that line's own repository docs, so this plan does not carry it. That
   resolves [`docs/release.md`](../docs/release.md) precondition 4, and `[project.urls] Documentation`
   now reads `https://docs.xyberos.com/`: the domain serves this line's site, and Cloudflare manages the
   record and the certificate because it is attached to this repository's Worker rather than to a Pages
   site. The site also publishes at its GitHub Pages address, which is the preview the domain switch was
   made against — see section 11's publish order. What the domain actually was, checked rather than
   assumed on 2026-10-12: a **Cloudflare-hosted deployment of a stale 1.x build**, carrying a custom
   theme the current 1.x repository does not have and missing its newest lesson. It was not that
   repository's Pages custom domain, so no setting there had to change.

Two details the build settled, both recorded because they are easy to get wrong again:

- **The home page is `site/index.md`, not `site/overview.md`.** MkDocs only writes `index.html` at the
  site root for a page named `index.md`; with any other name the site's front page is a 404 and the
  navigation's first entry points at a different URL.
- **`build/` does not shadow the `build` package** that `python -m build` runs, even though the docs
  build writes to `build/site/`. A directory without `__init__.py` is a namespace portion, and an
  installed regular package wins over it, so the release step and the docs step can share the
  workspace in either order.

UX work, sized by value: search (free with Material) > previous/next and per-path progress from front
matter > copy button on every code block > prerequisite callouts > diagrams. Diagrams last, and only
where a diagram replaces a paragraph: the app lifecycle, the composition-time provider registry, and
the hybrid request path in the Smart Support Desk.

## 11. Delivery phases

`site.md` §11's seven phases are kept; the exit criteria are added, because "phase complete" is
otherwise unfalsifiable. Effort is a rough estimate for one contributor, not a commitment.

**All seven phases are in the first release** (section 13, decision 5). Phases 2–5 are a delivery
order — Fundamentals and Traditional first, then AI, then Hybrid — not a publishing order: the release
waits for all three paths, so a slip in phase 4 or 5 moves the release rather than shipping a partial
site.

| Phase | Work | Exit criteria | Effort |
| --- | --- | --- | --- |
| 0. Decisions | **Complete.** `site.md` amended in place for the corrections in section 4, and all five questions answered (section 13) | `site.md` §12 and section 13 agree | S — complete |
| 1. Verify | **Complete** (see below). A feature-support page, a terminology page, the hybrid design page, an updated [`.gitignore`](../.gitignore), `mkdocs.yml` with `docs_dir: site` and `site_dir: build/site`, `site/scripts/` (front matter, roadmap, reference, build), the `tests/site/` harness, and one seeded lesson that proves the pipeline end to end | All four met: `mkdocs build --strict` passes with no warnings; `git status` lists `site/` as untracked rather than ignoring it; the harness fails on a deliberately wrong output block and passes when it is restored; `/reference/` renders all 39 guides from `docs/`; the hybrid design fixes the lifecycle, the permission matrix, and the approval boundary before phases 3–5 begin | M — complete |
| 2. Fundamentals | **Complete: 15 of 15 lessons.** Seven were migrated from `docs/tutorial.md` — 4, 7, 8, 9, 13, and 15, with their modules and output blocks — and eight are new material: 1, 2, 3, 5, 6, 10, 11, 12, and 14. Eight exercise answers are files the suite runs rather than blocks on a page | Every lesson `status: verified`; the roadmap reports 15 of 15; the moved chapters are deleted from `docs/tutorial.md` rather than duplicated | L — complete |
| 3. Traditional apps | **Complete: 12 of 12 lessons.** Lessons 1–3 were migrated from `docs/tutorial.md` chapters 5, 6, and 7 with their output blocks and exercise answers. Lesson 4 begins the path's own application, `examples/user_management/`: one project the remaining lessons grow, driven by a script per lesson, as section 4.9 requires. Lessons 5–7 add query-parameter validation and paging, the rest of CRUD, and Alembic revisions that delete the stand-in schema. Lesson 8 builds the ADR 0014 identity shape — a verifier, a principal passed as an argument, and the `external_subject` column that links them — and lesson 9 adds roles, `403`, and the edge obligation. Lessons 10 and 11 render the interface (Jinja2, forms, HTMX partials, Tailwind) and lesson 12 documents the deploy step, including a readiness check that notices a schema behind the code | Every published lesson `status: verified`; the migrated chapters are deleted from `docs/tutorial.md`; the final application is an `examples/` directory under integration test; the roadmap reports 27 of 27 | L — complete |
| 4. AI apps | **Complete: 17 of 17 lessons**, plus the fenced durable page in section 4.6. The path is one capability per lesson over `FakeModelProvider`, with every page labelling who provides the capability: the facade and its capability checks, the first call, provider switching, structured output, the error taxonomy, conversation history, memory, knowledge, retrieval over `embed`, tools behind an allowlist, intents, workflows, bounded agent behaviour, testing with no model service, evaluation against labelled cases, and security. Nine of the seventeen are labelled *you build it*, because there is no memory, retrieval, intent, agent, or evaluation layer in the package | No lesson needs a live model to run; the fenced page states the tier and the non-guarantees; the roadmap reports 17 of 17 in this path | L — complete |
| 5. Hybrid apps | **Complete: 10 of 10 lessons.** The Smart Support Desk lives in `examples/support_desk/`: ticket CRUD over the same project layout as the traditional path, a signed principal with a tenant and the permission matrix in the service, an audit row written in the transaction it describes, classification with a response schema, retrieval over `embed`, drafts stored as rows that have no send path, approval that records the principal and the body, a workflow that ends at a draft, background triage behind a job row, and usage rows settled by the outcome. Lessons 1–3 were written here rather than in phase 3, because the design page had already fixed what they needed | The boundary is stated and tested: a model recommends, application code authorizes; every transition, permission, and approval in the lessons appears in the phase 1 design page, and `tests/integration/test_hybrid_support_desk.py` asserts the four boundary rules plus one full workflow run against the fake provider | L — complete |
| 6. Extensibility | **Complete: four pages plus the durable page.** [`site/extend/registry.md`](extend/registry.md) documents what a registration says, the three scopes, what is refused at registration, and `with_overrides` as a clone rather than a mutation; [`site/extend/modules.md`](extend/modules.md) the composable-unit convention, contract-versus-registration, and the argument-free factory the CLI needs; [`site/extend/plugins.md`](extend/plugins.md) the trust boundary, metadata, configuration precedence, requirement ordering, the eight refusals, and the packaging and testing pattern; [`site/extend/database-providers.md`](extend/database-providers.md) the three-member contract, the semantics behind each promise, error mapping, and the conformance suite that refuses a provider committing rolled-back work. Every page's code is a module under `examples/learn_extend/` that the suite runs | A provider walkthrough passes `assert_provider_contract` in [`tests/integration/test_extension_provider.py`](../tests/integration/test_extension_provider.py), and the one that commits rolled-back work is refused; the plugin walkthrough's ordering, configuration, refusals, and lifecycle are asserted in [`tests/integration/test_extension_plugins.py`](../tests/integration/test_extension_plugins.py); the plugin distribution pattern is the fixture CI installs and imports as an installed package ([`tests/integration/test_plugin_packages.py`](../tests/integration/test_plugin_packages.py)), whose manifest this suite also checks; `examples/learn_extend` is in mypy's `files`, so the example code is type-checked to the same standard as `src/` | M — complete |
| 7. Production | **Complete: seven pages under `site/production/`** — [the section index](production/index.md), [deploying it](production/deploy.md), [observability](production/observability.md), [troubleshooting](production/troubleshooting.md), [security boundaries](production/security.md), [performance and concurrency](production/performance.md), and [internals](production/internals.md). Every page's code is a module under `examples/learn_production/` that the site harness runs and compares, and `site/extend/index.md` lost its `planned` status with each of its seven deferred topics given a real home | Each page names the shipped feature it relies on, or says it is application-side: the three transcripts that make the point are the failed start (`DependencyResolutionError`, state `failed`), the held lock (`TransientDatabaseError` after each attempt count), and the error that is replaced in the body while its message reaches the log. The claims a transcript cannot hold are asserted in [`tests/integration/test_production_deploy.py`](../tests/integration/test_production_deploy.py), [`test_production_shutdown.py`](../tests/integration/test_production_shutdown.py), and [`test_production_boundaries.py`](../tests/integration/test_production_boundaries.py); `examples/learn_production` is in mypy's `files` | M — complete |

Roughly 58–81 working days for one contributor, with the release gated on the critical path below
rather than on the sum.

Two sequencing constraints, both from this repository rather than from preference:

- **Phase 1 before phase 2.** The corrections in section 4 change lesson inventories, so writing pages
  first means rewriting them.
- **The `docs/tutorial.md` retirement is one commit.** Moving the chapter modules, the output blocks,
  and the harness together is what keeps the suite meaningful; a gradual move leaves the checked
  content and the read content in different places. Phase 1 prepares the ground, phase 2 does it.

### The critical path

The longest chain was phase 1 → 2 → 3 → 4 → phase 5, because the hybrid path consumes CRUD and templates
from phase 3 and retrieval and workflows from phase 4. The release date is set by the end of that chain, so
two schedule decisions followed from it. Both are now settled, and one of them was wrong in a way worth
recording.

- **Phase 5's design is fixed in phase 1**, not discovered in phase 5: the ticket states and their
  allowed transitions, the permission matrix, where human approval sits, which AI touch points are
  built-in and which are application code, the lesson list with its `examples/` modules, and the
  integration test that phase 5's exit criteria demand. Deciding this before phases 3 and 4 build the
  contracts the hybrid path reuses is what kept phase 5 from becoming a redesign — and because decision 5
  puts all three paths in one release, a phase 5 redesign would have been a release slip rather than a
  deferred path. The design page needed two corrections when the path was written, both recorded there:
  the matrix gained the row for editing a ticket, and the tool row became "not used" rather than a
  `ToolSet`, because the desk gives the model a ticket body and one passage and nothing else.
- **The plan to write phase 5's lessons 1–3 during phase 3 did not happen.** The reasoning was sound —
  they are the traditional path's material — but the traditional path's own application was still moving
  underneath it, and writing hybrid lessons against a moving `examples/user_management/` would have meant
  rewriting them. They were written with the rest of the path instead, which cost nothing: the design page
  had already fixed what they needed, and the shared conventions carried over as intended.

The hybrid application also shares the traditional path's skeleton — the same project layout, the same
`DatabaseProvider` usage, the same template approach, and the same `HttpError` shape — so phase 5 extends
conventions that already exist instead of introducing a third codebase to review. That is why the two
applications read as one set of rules applied twice rather than two sets of rules.

### Publishing

The site publishes before the release does, and in three steps rather than one, because the domain it
will eventually serve is occupied by the other line. [`docs/release.md`](../docs/release.md)
precondition 4 records the same order.

| # | Step | Where it happens |
| --- | --- | --- |
| 1 | **Publish the preview.** [`.github/workflows/site.yml`](../.github/workflows/site.yml) builds with the same command CI uses and deploys to `https://xyberos.github.io/xyberos/` — **live**, 54 of 54 lessons. While phases 6 and 7 were unwritten the roadmap page reported two sections still `planned` | This repository, on a push that touches the site or by hand |
| 2 | **Move the domain off the 1.x site.** Its guides were served from the 1.x repository, now renamed to `xyberos/xyberosv1.0-deprecated`, so what moved was the domain, not the documentation — **done 2026-10-12**: the Cloudflare deployment that held `docs.xyberos.com` was deleted | The 1.x repository and the Cloudflare account that held the domain — out of scope here, and nothing in this repository can change them |
| 3 | **Point the domain at this site**, then move `[project.urls] Documentation` to it — **done 2026-10-12**: the domain is attached to this line's Cloudflare Worker (`wrangler.jsonc`), and `Documentation` is `https://docs.xyberos.com/` | The Cloudflare Workers project, and `pyproject.toml` |

Step 2 is smaller than it looked, and the evidence is a lookup rather than an assumption: the 1.x line's
guides serve at `https://xyberos.github.io/xyberosv1.0-deprecated/` because that repository's `docs/` tree is its own
MkDocs site, deployed from its `gh-pages` branch, and its build now declares that address as `site_url`,
so its next deploy carries a canonical link on every page. The domain was the part that needed looking
up, and it was not what the first reading of it assumed: `docs.xyberos.com` was a
**Cloudflare-hosted deployment of a stale build** — a custom theme this repository does not have,
extensionless URLs behind `307` redirects, and the newest 1.x lesson answering `404` — so there was no
Pages setting to clear on either side, and no content to rescue from it. Public resolvers returned
nothing for the name after the deletion, and `https://docs.xyberos.com/` answers Cloudflare's `530`
rather than a site.

What remains is nothing on the site's side: the domain is attached to this line's Cloudflare Worker, so
Cloudflare holds the DNS record and the certificate, and the GitHub Pages workflow keeps publishing the
preview at `https://xyberos.github.io/xyberos/`. The first reading of this step assumed a GitHub Pages
custom domain and a `docs` CNAME, and the site turned out to be hosted by Cloudflare instead — the record
is Cloudflare's to manage, and no change to it was needed from here.

Step 1 shipped the two sections while they were still `planned`, which is what made it a preview rather
than a release: `build.py --check` validates every page, and only `roadmap.py --check --release` refuses
a section that is unfinished. The preview's honesty about its own state came from the roadmap page rather
than from a note that would be wrong on the release — and now that phase 7 is written, that gate passes
and reports no planned sections at all.

Step 1 needs one thing this repository cannot do for itself: a Pages site, because a workflow token
cannot create one. It exists now, and the setting is Settings → Pages → Source: GitHub Actions. The
build and the tests run whether or not it exists — the URL is derived rather than read from
`actions/configure-pages`, which fails when the site is missing — and the deploy job's first step checks
the Pages API and prints what it answered, which is how the missing setting was identified rather than
inferred. Step 3's custom domain is the only other part of this sequence that is not automated.

The build takes its canonical URL from `site_url`, which reads `!ENV [SITE_URL, "https://docs.xyberos.com/"]`
so one configuration serves both addresses: the workflow passes the Pages URL, and a local build takes
the release default.

## 12. Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Two content sources diverge during the retirement of `docs/tutorial.md` | A reader follows the wrong tutorial; the tested one becomes the stale one | The retirement is a single commit (section 11); until it lands the output-block harness covers `docs/tutorial.md`, and after it the site. The hand-written-Python-block test stops the drift afterwards |
| Preview-tier APIs move under the pages (HTTP, database, AI, CLI) | Lessons rot in a minor release | `verified_at` in front matter; the output-block harness fails on drift; `docs/stability.md`'s tier is repeated on every lesson it applies to |
| A lesson teaches a framework-shaped feature that is application code (templates, vector search, auth) | The reader blames the runtime for a gap it documented as a boundary | The four labels in section 5, plus `test_claimed_tier_matches_stability_guide` |
| The AI path becomes untestable in CI (live model, network) | The suite loses its "no service needed" property | Fake provider and declared capabilities in every AI lesson; no output block for anything that cannot run offline |
| Scope: three full application projects ship in one release (decision 5) | The release is gated on the slowest path, so a slip in phase 4 or 5 delays everything | Deliver in the decided order so each path is reviewable as it completes; keep paths independent, so no lesson links forward across paths except as a prerequisite; start the Smart Support Desk (phase 5) once the hybrid design is fixed rather than after the AI path is finished, because it is the critical path to the release |
| The 1.x documentation keeps serving `docs.xyberos.com` | A reader at that URL gets the wrong line's documentation | **Resolved 2026-10-12.** Decision 1 splits the two: this site takes `docs.xyberos.com` and the 1.x site keeps serving from its own repository, now named `xyberosv1.0-deprecated`. What the domain actually was turned out to be neither repository's Pages site but a Cloudflare deployment of a stale 1.x build; it was deleted, the 1.x repository now names its own address, and the name resolves nowhere until this line's site claims it |

## 13. Decisions taken

Settled by the owner. Each is mirrored in `site.md` §12, so the plan and this file agree.

| # | Question | Decision | Consequence for this plan |
| --- | --- | --- | --- |
| 1 | Host | This site replaces the content of `docs.xyberos.com`; the 1.x line's documentation is served from that line's own repository | **Done 2026-10-12.** The stale Cloudflare deployment that held the domain was deleted, the 1.x repository (now `xyberos/xyberosv1.0-deprecated`) names its own address (`8c8a49f`), the domain is attached to this line's Cloudflare Worker (`wrangler.jsonc`), and `[project.urls] Documentation` is `https://docs.xyberos.com/` ([`docs/release.md`](../docs/release.md) precondition 4). The GitHub Pages workflow keeps publishing the preview |
| 2 | Stack | MkDocs + Material: `mkdocs.yml` at the repository root, `docs_dir: site` | Section 10 is a decision rather than a recommendation, and no Node toolchain enters CI |
| 3 | `docs/tutorial.md` | Retired into the Fundamentals path | The chapter modules and their output blocks move in one commit and the harness follows them; `site.md` §2 records the chapter-to-lesson map |
| 4 | Reference sourcing | Generated from `docs/` from the first release | The `/reference/` copy step moves from phase 6 to phase 1, and the "one copy of each guide" rule is enforced from the start |
| 5 | Release scope | All three learning paths ship in **one release**, delivered in this order: Fundamentals + Traditional, then AI, then Hybrid | Phases 3, 4, and 5 are all inside the first release, and the release is gated on all three; the AI and hybrid paths are no longer additive work that can follow after publishing |

Nothing in this plan is waiting on an owner decision now.

## 14. Definition of done

The site is done when all of the following hold:

- `mkdocs build --strict` renders the whole site in CI with no warnings, and no page in the nav points
  at a missing file or anchor.
- Every lesson declares a path, a lesson number, one of the four availability labels, and one of the
  four verification modes; the label agrees with [`docs/stability.md`](../docs/stability.md), and the
  mode's requirement is met.
- No lesson contradicts a recorded decision: no identity model (ADR 0014), one shipped database
  provider and a documented extension point (ADR 0016), no sandbox for plugins (ADR 0007), durable
  execution marked experimental (ADR 0011).
- The traditional path is walkable end to end on a clean machine by someone who has only installed
  Python, and the resulting application is an `examples/` directory under integration test.
- Fundamentals and all three learning paths — Traditional, AI, and Hybrid — are `verified` in the same
  release (section 13, decision 5); `/learn/hybrid/` is complete rather than stubbed.
- No page in the nav is `draft`, and every lesson has an offline output block the harness reproduces;
  service-dependent walkthroughs are appendices, validated at command level and exercised by the opt-in
  workflow.
- The hybrid path is built to the phase 1 design page: every ticket transition, permission, and approval
  boundary that appears in a lesson appears in that design, and the integration test asserts the
  boundary rather than the prose describing it.
- `/reference/` renders every guide from `docs/`, and CI asserts the rendered copy matches a fresh copy
  of `docs/` — one copy of each guide, generated rather than duplicated.
- `[project.urls] Documentation` points at the site, and the 1.x line's documentation has moved to that
  line's repository docs, so neither URL advertises the wrong codebase.

## 15. Next actions

1. **Done.** `site.md` is amended in place for the corrections in section 4 — terminology (4.1),
   identity stage (4.2), database table (4.3), the template boundary (4.4), AI labels (4.5), the durable
   page (4.6), and the CDN links (4.7) — with 4.8–4.10 folded in, because decisions 3 and 4 depend on
   them.
2. **Done.** Section 13 records the four decisions: host, stack, the retirement of `docs/tutorial.md`,
   and generating the reference from the start.
3. **Done.** `mkdocs.yml` and the `tests/site/` harness, wired into the `quality` CI job together with
   the reference render. The assertions are listed in section 9. The build gates and the suite were
   both checked against a deliberately broken page, not only against a green run.
4. **Partly done, and deliberately partly.** The `docs/tutorial.md` chapters whose subject is the
   runtime itself moved to the Fundamentals path in one commit — chapters 1, 2, 3, 4, 8, and 13 —
   with their modules, output blocks, exercise answers, and harness coverage. The remaining chapters
   stay in `docs/tutorial.md` until the path that owns them exists, because deleting them now would
   leave that content with nowhere to live. The rule the migration follows is per chapter: exactly one
   home, exactly one suite.
5. **Done.** The host handover is complete. At the time, the 1.x repository (`xyberos/xyberos`, now
   `xyberos/xyberosv1.0-deprecated`) no longer pointed at `docs.xyberos.com`: its README, its `[project.urls]`,
   and its `mkdocs.yml` `site_url` name
   `https://xyberos.github.io/xyberosv1.0-deprecated/`, committed as `8c8a49f`. The domain turned out to be a Cloudflare
   deployment of a stale 1.x build rather than a Pages custom domain; it was deleted, and the domain was
   then attached to this line's Cloudflare Worker, which is what [`wrangler.jsonc`](../wrangler.jsonc)
   configures. [`docs/release.md`](../docs/release.md) precondition 4 and `[project.urls] Documentation`
   in [`pyproject.toml`](../pyproject.toml) both name `https://docs.xyberos.com/` now, in the order
   section 11 fixed: the domain served this line's site before the metadata advertised it.
6. **Done.** `mkdocs.yml` with `docs_dir: site` and `site_dir: build/site`, with the navigation naming
   the two plan documents where they are readable rather than copying them in, and `exclude_docs`
   keeping their repository-relative links out of the strict build. `git status` lists `site/`, and the
   generated `site/reference/` and `site/roadmap.md` are ignored.
7. **Done.** [`site/hybrid-design.md`](hybrid-design.md) fixes the ticket states and transitions, the
   permission matrix, the approval boundary, the AI touch points, the ten lessons with their example
   modules, and the integration test. [`site/appendices/index.md`](appendices/index.md) states what an
   appendix is, and [`.github/workflows/site-live.yml`](../.github/workflows/site-live.yml) is the
   opt-in workflow that will exercise them.
8. **Done.** Phase 6, Extend Xyberos: four verified pages under `site/extend/` — the provider
   registry, modules, plugins, and database providers — each built on walkthrough modules in
   `examples/learn_extend/` that the site harness runs and compares, with integration tests holding the
   two claims that matter (the conformance suite passes a real provider and refuses a broken one; plugin
   ordering, configuration, and refusals behave as the page says). The section index stayed `planned`
   while phase 7 was unwritten, so the release gate refused until item 9 below.
9. **Done.** Phase 7, Production: seven pages under `site/production/` — deployment, observability,
   troubleshooting, security boundaries, performance and concurrency, and internals, plus the section
   index — each built on a module in `examples/learn_production/` that the harness runs and compares,
   and each naming the shipped feature it relies on or the part that is application-side. The three
   claims a transcript cannot hold are asserted in
   [`tests/integration/test_production_deploy.py`](../tests/integration/test_production_deploy.py),
   [`test_production_shutdown.py`](../tests/integration/test_production_shutdown.py), and
   [`test_production_boundaries.py`](../tests/integration/test_production_boundaries.py). `site/extend/index.md`
   lost its `planned` status, and every topic it had deferred is named with the page that now owns it.
   The release gate that refused since phase 1 now passes.

Phases 1–7 are complete: the Fundamentals path is fifteen verified lessons, the Traditional Apps path
twelve, the AI Apps path seventeen, and the Hybrid Apps path ten — 54 lessons in one pipeline, where every
lesson's code is a file the suite runs, every documented output is compared with the real thing on every
build, and the transcripts of earlier lessons survive the later ones changing the application underneath
them. No path needs a model service, the durable page states its experimental tier, and the roadmap reports
54 of 54 verified. Alongside the paths, the Extend section documents the four extension points with the
same discipline: each page's code is an `examples/learn_extend/` module the suite runs. The Production
section does the same for the operational surfaces, including the two it can only describe: what a
deployment has to do in what order, and which security decisions are the application's.

Phase 5 was written as ten lessons at once rather than three in phase 3 and seven later, because the
design page had already fixed the shape they share: `examples/support_desk/` is one application — tables,
a service with the matrix and the audit trail, a knowledge base, a transactional outbox, a workflow, and a
job runner — and the ten modules in `examples/learn_hybrid/` drive it. `tests/integration/test_hybrid_support_desk.py`
holds the boundary the path teaches: the four assertions the design page states, plus one full triage run
against the fake provider.

Two conventions were settled while writing the earlier paths, and phase 5 inherits both. The path's
application lives in [`examples/user_management/`](../examples/user_management) as a package of small
files, and each lesson's own module in `examples/learn_traditional/` drives it through its routes; the
hybrid path mirrors that with [`examples/support_desk/`](../examples/support_desk) and
`examples/learn_hybrid/`. A lesson that needs a different application says so on its page rather than
quietly starting a second one.

The other convention came out of the hybrid path itself, and it is worth recording because it cost an
afternoon: a domain method named `close` on a provided instance is a lifecycle hook as far as the runtime
is concerned, so `TicketService.close_ticket` keeps its name and the ticket service shuts down cleanly.

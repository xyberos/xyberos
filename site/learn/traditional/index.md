---
title: Traditional Apps
status: verified
---

# Build Traditional Apps

One application, built from nothing: a minimal program that answers HTTP, then a database, then CRUD,
then a server-rendered interface — and finally the identity lesson, which is not a login form.

Each lesson adds one capability to the application the previous lesson left working, and each is
checked before it is published: the code you read is the code the suite runs, and the output you see is
the output it really produced.

## Lessons

| # | Lesson | You will learn | Availability |
| - | ------ | -------------- | ------------ |
| 1 | [An application that answers HTTP](01-http.md) | Routes, JSON responses, and the ASGI adapter | Built-in (extra) |
| 2 | [Read a request, and say no to one](02-requests-and-errors.md) | Path and query parameters, bodies, and `HttpError` | Built-in (extra) |
| 3 | [Store data in SQLite](03-database.md) | The database provider, transactions, and rollback | Built-in (extra) |
| 4 | [Create and list users](04-users.md) | A service, its rules, and the shape of a collection | Built-in (extra) |
| 5 | [Validation and pagination](05-pagination.md) | Query parameters, the two layers of validation, and paging | Built-in (extra) |
| 6 | [View, edit, and delete](06-crud.md) | Missing rows, partial edits, and a delete that repeats | Built-in (extra) |
| 7 | [Migrations](07-migrations.md) | Revision files, batch mode, and the deploy step | Built-in (extra) |
| 8 | [Identity from upstream](08-identity.md) | A verified principal, passed as an argument | You build it |
| 9 | [Protected endpoints](09-protected.md) | `401` versus `403`, roles, and the edge obligation | You build it |
| 10 | [Server-rendered interfaces](10-pages.md) | Templates, forms, and validation messages | You add it |
| 11 | [Partial updates and styling](11-partials.md) | HTMX and Tailwind over the same handlers | You add it |
| 12 | [Deploying it](12-deploy.md) | The deploy step, readiness, and the operational facts | Built-in (extra) |

**All twelve lessons are written.** The [roadmap](../../roadmap.md) is generated from each page's own
status rather than typed here, so it is what the path's completeness is read from; the AI and hybrid
paths are still to come.

## What you need

The setup from [lesson 1 of the Fundamentals path](../fundamentals/index.md), plus two extras:

=== "PowerShell"

    ```powershell
    python -m venv .venv
    .venv\Scripts\python -m pip install "xyberos[http,database]" uvicorn
    ```

=== "POSIX"

    ```bash
    python -m venv .venv
    .venv/bin/python -m pip install "xyberos[http,database]" uvicorn
    ```

`uvicorn` is the web server these lessons use. It is *not* part of Xyberos: a framework that refuses to
depend on an HTTP library should not force a server on you either.

## Three things to know before it starts

**The application grows, and the pages show it growing.** From lesson 4 the path builds one application
in `examples/user_management/`, and each lesson's own module in `examples/learn_traditional/` drives it.
A page shows the project's files as the path leaves them, so an earlier lesson may show a file a later
lesson also changed — the lesson that changed it says so on its own page.

**Identity is not built here.** Xyberos ships no identity, tenancy, or authorization model and will
not, and this path does not quietly build one. Sessions and CSRF *do* ship, as middleware the
application passes ([ADR 0024](../../reference/adr/0024-sessions-and-csrf-are-middleware-in-the-http-module.md)),
with [the sessions example](https://github.com/xyberos/xyberos/tree/master/examples/sessions) as
their recipe. The identity lesson shows the sanctioned shape instead: something verifies an incoming
assertion, the principal is passed to the service as a required argument, and the tenant is taken from
the principal rather than from the payload
([ADR 0014](../../reference/adr/0014-no-identity-or-authorization-model.md)).

**Templates are not a framework feature.** The framework routes and serializes; a handler may return any
Starlette response. The interface lessons use Starlette's own template support and static files, and say
so on every page, because it is application code rather than a Xyberos API.

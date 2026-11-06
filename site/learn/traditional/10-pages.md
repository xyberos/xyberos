---
title: Server-rendered interfaces
path: traditional
lesson: 10
tier: third-party
status: verified
verify: output
example: examples/learn_traditional/traditional10_pages.py
prerequisites: ["/learn/traditional/09-protected"]
---

# Lesson 10 — server-rendered interfaces

## What you will build

The application's first interface. Everything so far returned JSON, and the service underneath did not
care; this lesson adds pages, forms, and the three shapes that make a form safe — post, then redirect;
re-render the form when a submission is refused; and refuse a submission that came from another site,
with the cross-site check the framework ships
([ADR 0024](../../reference/adr/0024-sessions-and-csrf-are-middleware-in-the-http-module.md)).

**This lesson is application code, not a framework feature.** Xyberos routes and serializes; it ships no
template engine, no HTML helper, and no static-file convention. The engine here is Jinja2 through
Starlette's `Jinja2Templates`, which is the shortest path from the routes you already have to a page a
person can use.

## What you need

Two dependencies the framework does not bring, and does not want to:

=== "PowerShell"

    ```powershell
    python -m pip install jinja2 python-multipart
    ```

=== "POSIX"

    ```bash
    python -m pip install jinja2 python-multipart
    ```

Jinja2 renders the page. `python-multipart` is what Starlette parses a submitted form with: without it
`request.form()` raises instead of reading the body, because the parser is a separate library rather
than part of Starlette.

The cross-site check brings **nothing**. `xyberos.http.CSRFMiddleware` is in the `[http]` extra the
adapter already needs, and it needs no secret, no store, and no third-party package — which is why the
framework ships it rather than pointing you at one
([ADR 0024](../../reference/adr/0024-sessions-and-csrf-are-middleware-in-the-http-module.md)).

## The templates

`examples/user_management/templates/` holds two files. A layout, so a page is a page:

<!-- snippet: examples/user_management/templates/base.html -->

And the page itself. It renders the same bounded collection the JSON route returns, then a form:

<!-- snippet: examples/user_management/templates/users.html -->

Autoescaping is on (Starlette's `Jinja2Templates` uses `autoescape=True`), which is why
`{{ user.display_name }}` is safe to write and why this lesson's transcript ends by proving it. The two
ways to lose that are worth naming now: `|safe`, and `Markup`, and building HTML with an f-string before
a template ever sees it.

## The routes

`examples/user_management/app.py` gains two page routes and one small helper. Nothing about the service
changed: the page reads the same `list_users()` the API does, with the same bound, and the form calls the
same `create_user()` with the same rules:

<!-- snippet: examples/user_management/app.py -->

Three decisions are in those twenty lines:

- **A successful submission is a `303` to the list, not a rendered page.** A browser that reloads a
  rendered `POST` re-submits it; a redirect makes a reload a `GET`. The driver asserts the status and the
  `Location` header rather than following the redirect, because `create_test_client` follows redirects by
  default and would hide the whole point.
- **A refused submission re-renders the form with `422`**, carrying the message *and* what the client
  typed. Losing their input is the fastest way to make a form feel broken, and the status tells a
  programmatic client that the write did not happen.
- **The refusal is caught by class, not by `except Exception`.** `DuplicateEmailError` and
  `UserValidationError` are the two ways a valid form can still be refused; a `401`, a `403`, or a crash
  must not be turned into a polite page.

One more thing to note, because it is the same rule as lessons 8 and 9: a browser cannot send the
administrator's assertion. In a deployment the proxy authenticates the person, sets the assertion
headers, and the page routes check them exactly as the API routes do. Nothing about the HTTP shape
changes; the assertion just arrives from a different client.

## Making the form safe against another site

A browser attaches its cookies to any request a page makes — including one that a page on another site
told it to make. The cross-site check is what refuses that, and here it is one line on the adapter —
`HttpAdapter(app, middleware=(Middleware(CSRFMiddleware),))`. The middleware reads headers only — the
`Origin` a browser attaches, and an optional `X-CSRF-Token` — so it never consumes the body the handler
still has to read. A request with neither header is not a browser cross-site request, so it is allowed,
which is why this lesson's own client, which sends no `Origin`, posts successfully throughout. The last
two lines of the transcript are the check working: a `POST` carrying `Origin: https://evil.example`
answers `403`, and the row it tried to create is not there.

A real browser form needs one line more than this lesson shows, because a `POST` from a rendered page
carries a genuine origin: render the token into the form with `get_csrf_token(request)` and the
middleware compares it. That is exactly what
[the sessions example](https://github.com/xyberos/xyberos/tree/master/examples/sessions) does,
together with the session the form belongs to.

## What the lesson runs

<!-- snippet: examples/learn_traditional/traditional10_pages.py -->

## How to run it

=== "PowerShell"

    ```powershell
    $env:PYTHONPATH = "src;examples"
    python -m learn_traditional.traditional10_pages
    ```

=== "POSIX"

    ```bash
    PYTHONPATH=src:examples python -m learn_traditional.traditional10_pages
    ```

## What it prints

<!-- output: traditional10_pages -->
```text
GET /pages/users -> 200 text/html; charset=utf-8
an empty table and a form: True True
POST /pages/users -> 303 /pages/users
the new row appears: True
POST with a bad address -> 422
the form keeps what was typed: True
and the refusal is text, not markup: True
POST with markup -> 303
the markup is escaped: True
and none of it is raw: True
cross-site post -> 403
and it never reached the form: True
```

| Line | What it establishes |
| ---- | ------------------- |
| `GET /pages/users -> 200 text/html; charset=utf-8` | a handler may return any response; the framework stops serializing JSON when you do |
| `POST /pages/users -> 303 /pages/users` | the form wrote, then redirected: a reload is now a `GET` |
| `POST with a bad address -> 422` | the refusal is a status, not a message on a `200` |
| `the form keeps what was typed` | the re-render carries the submitted value back |
| `the refusal is text, not markup` | an error message is escaped like any other value |
| `the markup is escaped` / `and none of it is raw` | a display name containing `<script>` renders as text, and never as a tag |
| `cross-site post -> 403` | a submission from another site is refused before the handler runs |
| `and it never reached the form` | the refused write left no row: the check is a refusal, not a delay |

## Common mistakes

- **`|safe`, `Markup`, or HTML built in Python.** Autoescaping protects exactly one thing: the values it
  is allowed to escape. The moment a page marks a user-supplied value as safe, the interface is an
  injection point — the last two lines of the transcript are the test that says so.
- **Rendering instead of redirecting after a write.** Double-submitted forms are an ordinary consequence
  of a reload, and the fix is one line: `RedirectResponse(..., status_code=303)`.
- **Answering `200` for a refusal.** A client that reads the status cannot tell a rejected write from an
  accepted one; `422` is the same status the JSON API uses for the same failure.
- **Doing business rules in the template.** A template that filters, sorts, or limits is a second service
  layer with no tests. Render `list_users()`'s page, not the table.
- **Trusting a form value to be a string.** `request.form()` returns `str | UploadFile`; a submitted file
  field is an object, and the service's `isinstance` check is what refuses it.
- **Forgetting the page routes in the route table review.** These routes are new endpoints with their own
  authorization, exactly like the API's.
- **Reaching for a third-party CSRF library.** The framework ships one
  ([ADR 0024](../../reference/adr/0024-sessions-and-csrf-are-middleware-in-the-http-module.md)); it needs
  no store and no secret, and it composes with `SessionMiddleware` when the form belongs to a session.

## Exercise

Add the edit form: `GET /pages/users/{user_id}/edit` renders the current name, and `POST` to the same
path saves it — redirecting on success, re-rendering with `422` on a refused name, and letting a missing
user stay lesson 6's `404`.

<details>
<summary>Show the answer</summary>

<!-- snippet: examples/learn_traditional/templates/edit.html -->

<!-- snippet: examples/learn_traditional/traditional10_exercise.py -->

<!-- output: traditional10_exercise -->
```text
GET the edit form -> 200 prefilled: True
POST the edit -> 303 /pages/users
the list shows the new name: True
POST an empty name -> 422
and says why: True
GET a form for a missing user -> 404
```

The answer's template directory is *added* to the project's rather than replacing it —
`Jinja2Templates(directory=[...])` takes a list, and Jinja's loader searches in order — so the exercise
can extend the project's `base.html` without copying it. Two more details carry forward from lesson 6:

- **`update_user` is the same method the `PATCH` route calls**, so the normalisation and the collision
  rule are shared: a form is a client, not a second implementation.
- **A missing user is still a `404`.** The answer catches only `UserValidationError`, so
  `UserNotFoundError` reaches the adapter and answers `404`, which is the right answer to a form for a
  row that is not there — and the last line of the transcript is that distinction, checked.
</details>

## Next

Lesson 11 makes the interface feel like an application: partial updates with HTMX, styling with
Tailwind, and the same handlers serving both.

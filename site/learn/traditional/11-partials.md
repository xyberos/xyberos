---
title: Partial updates and styling
path: traditional
lesson: 11
tier: third-party
status: verified
verify: output
example: examples/learn_traditional/traditional11_partials.py
prerequisites: ["/learn/traditional/10-pages"]
---

# Lesson 11 — partial updates and styling

## What you will build

An interface that behaves like an application. One route answers two clients — a browser that wants a
page and a script that wants one row — and the row is defined once, in a template the page also
includes. Styling arrives at the same time, because a table nobody can read is not finished work.

Both additions are application choices, like lesson 10's template engine. The framework does not know
what HTMX is, and this lesson's route proves it: the difference between the two answers is one request
header the *application* reads.

## What you need

Nothing new. The two scripts are in `base.html`, and neither is required for the application to work:
without them the buttons are ordinary form buttons and the pages still function.

<!-- snippet: examples/user_management/templates/base.html -->

Tailwind's play build is a prototyping tool — it compiles styles in the browser — and a deployment
builds the stylesheet it actually uses. HTMX is a single script with no build step. Both are things you
add and later replace, which is why they are two tags rather than a framework feature.

## One row, two ways to arrive at it

`examples/user_management/templates/_row.html` is the row. It is a fragment: no `<html>`, no `<table>`,
just a `<tr>` with an `id` a client can target:

<!-- snippet: examples/user_management/templates/_row.html -->

Three attributes are the whole mechanism. `hx-post` says where the button posts; `hx-target="closest tr"`
says which element will be replaced; `hx-swap="outerHTML"` says replace it entirely, including itself.
The page includes the same file, per user, inside its table body — so a row rendered by the list and a
row rendered by the fragment cannot drift apart:

<!-- snippet: examples/user_management/templates/users.html -->

## The route that answers both

<!-- snippet: examples/user_management/app.py -->

`toggle_user` does the write once and then chooses a representation:

- **`HX-Request` present** → render `_row.html` for the updated row. That is what HTMX swaps in, and it
  is why the fragment must contain exactly one element: a swap target with two roots produces whichever
  one the browser keeps.
- **no such header** → `303` back to the list, exactly as lesson 10's form does.

Note what the header is *not*: authorization. Any client can send `HX-Request: true`, and a script that
sends it deliberately is a script that prefers HTML. Access is decided by the assertion in lesson 9,
before any of this; a request that fails that check never reaches the branch.

One shipped detail if you add the cross-site check here: HTMX sends whatever the page puts in
`hx-headers`, so `hx-headers='{"X-CSRF-Token": "..."}'` is all `CSRFMiddleware` needs — a button is
protected exactly as lesson 10's form is
([the sessions example](https://github.com/xyberos/xyberos/tree/master/examples/sessions)).

## What the lesson runs

<!-- snippet: examples/learn_traditional/traditional11_partials.py -->

## How to run it

=== "PowerShell"

    ```powershell
    $env:PYTHONPATH = "src;examples"
    python -m learn_traditional.traditional11_partials
    ```

=== "POSIX"

    ```bash
    PYTHONPATH=src:examples python -m learn_traditional.traditional11_partials
    ```

## What it prints

<!-- output: traditional11_partials -->
```text
toggle without HTMX -> 303 /pages/users
toggle with HTMX -> 200 text/html; charset=utf-8
the answer is one row: True
no page around it: True
the row carries the swap target: True
and the button now offers the other state: True
the list renders the same row: True True
with the styling in place: True
```

The two `toggle` lines are the lesson: the same route, the same write, two answers a client can use.
The rest are the properties a partial has to have to be useful — one row, no page around it, the `id`
the swap needs, and the button already offering the *next* state, because the fragment was rendered from
the database rather than from the request. The last line is styling: the list page is the same markup,
with classes.

## Common mistakes

- **Returning a whole page into a swap target.** It works in a small test and destroys the layout in a
  browser. A fragment endpoint returns one element; that is why `_row.html` has no `<table>`.
- **Assuming the client toggles the state.** The button posts and the server decides: a fragment
  rendered from the request ("say the opposite of what the client sent") shows the wrong state the
  moment two tabs are open.
- **Treating `HX-Request` as a permission.** It is a preference, and it is trivially forged. The
  authorization check comes first, always.
- **Two definitions of a row.** A page that renders rows one way and a fragment that renders them another
  way is a bug report waiting for a styling change; `{% include %}` is the fix.
- **Shipping the play CDN.** It is explicit about being for prototyping. A deployment builds its
  stylesheet, so the page does not pay for a compiler in the browser.
- **Forgetting `id` on the fragment root.** `hx-target="closest tr"` needs to find an element, and a
  list of rows with no identifiers is a list you cannot address.

## Exercise

Add `GET /pages/users/rows`, which returns only the table's body so a client can refresh the list on a
timer. The rows must be the page's rows — the same include — and the fragment must contain no table.

<details>
<summary>Show the answer</summary>

<!-- snippet: examples/learn_traditional/templates/_rows.html -->

<!-- snippet: examples/learn_traditional/traditional11_exercise.py -->

<!-- output: traditional11_exercise -->
```text
GET /pages/users/rows -> 200 text/html; charset=utf-8
the fragment is a row: True
and nothing around it: True True
the row is the page's row: True
after a write, the fragment has both rows: True
and the page agrees: True
```

The template is three lines because the work was already done: `_rows.html` loops over the same
`_row.html` the page includes, so the refreshed body and the initially rendered body are the same markup
by construction. Two details worth keeping:

- **The route is gated like every other page route.** A polling endpoint is an endpoint: it reads user
  data, so it verifies and it requires the role.
- **The fragment is re-read from the database on every poll.** That is the whole reason to poll rather
  than to patch the DOM: the list converges on what is stored, including changes another client made.
</details>

## Next

Lesson 12 takes it to a server: the deploy step, what to check before traffic arrives, and the
operational facts that make the application in this path runnable.

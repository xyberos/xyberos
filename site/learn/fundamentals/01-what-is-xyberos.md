---
title: What Xyberos is
path: fundamentals
lesson: 1
tier: built-in
status: verified
verify: output
example: examples/learn_fundamentals/fundamentals01_what_is_xyberos.py
prerequisites: []
---

# Lesson 1 — what Xyberos is

## What you will build

One application with one service in it. Small enough to read in a minute, and it already shows the
three things everything later builds on: you compose an application, the runtime owns the lifetime of
what you register, and code asks for what it needs instead of looking it up.

## What you need

- Python 3.10 or newer.
- Xyberos, from PyPI. This lesson needs no extras.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install xyberos
```

## The code

<!-- snippet: examples/learn_fundamentals/fundamentals01_what_is_xyberos.py -->

## How to run it

From a clone of this repository, this file is the one the test suite runs:

```powershell
python -m pip install -e .[http,database]
$env:PYTHONPATH = "src;examples"
python -m learn_fundamentals.fundamentals01_what_is_xyberos
```

In your own project, copy the file, then run it the same way — `python -m pip install xyberos` is the
only thing it needs.

## What it prints

<!-- output: fundamentals01_what_is_xyberos -->
```text
xyberos 2.2.0
scopes: app, request, transient
before start: new
running: ready
hello from Xyberos
providers: 1
registered by: application
after stop: stopped
```

The first line is the version this page was verified against, and the test suite compares the whole
block with the real output, so it cannot drift.

## The lines that matter

| Line | What it does |
| ---- | ------------ |
| `app = App()` | creates an application: a composition root, not a container you look things up in |
| `app.provide(Greeter, instance=Greeter("Xyberos"))` | registers a provider, keyed by its own class |
| `async with app.lifespan():` | starts the application, and stops it when the block ends |
| `await app.resolve(Greeter)` | asks the application for the provider |
| `app.state.value` | the lifecycle state: `new`, `ready`, and `stopped` here |
| `app.diagnostics()` | where every provider came from, and in which order plugins started |

Two of those are worth pausing on.

**A provider is keyed by a type, not a name.** `Greeter` is registered under `Greeter`, and nothing
resolves a service by writing a string. That is why a typo in a contract is a failure at composition
time rather than a surprise in production.

**`resolve` is asynchronous.** The `await` is not decoration: the runtime may have to construct the
provider, and construction can be asynchronous.

## Common mistakes

- **Forgetting `await`.** `app.resolve(Greeter)` without `await` returns a coroutine, and the next line
  fails with `'coroutine' object has no attribute 'greet'`.
- **Resolving outside the lifespan.** `app.resolve` before `async with app.lifespan():` raises
  `LifecycleStateError`, because the application has not started.
- **Reaching for a global.** There is no module-level container. A service that needs another service
  declares it in its constructor as `Annotated[Other, Inject()]`, which is lesson 8.

## Exercise

Change the greeting so it names the person instead of the framework, and make the provider a class
rather than a pre-built instance — `app.provide(Greeter)` with a `name` argument the runtime supplies
is lesson 7's subject, so for now try `Greeter("your name")`.

## Next

Install Xyberos properly, with the extras each capability needs, in **lesson 2 — install Xyberos**.
Until it is published, [the roadmap](../../roadmap.md) shows where each lesson stands.

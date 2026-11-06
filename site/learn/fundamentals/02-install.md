---
title: Install Xyberos
path: fundamentals
lesson: 2
tier: built-in
status: verified
verify: output
example: examples/learn_fundamentals/fundamentals02_install.py
prerequisites: ["/learn/fundamentals/01-what-is-xyberos"]
---

# Lesson 2 — install Xyberos

## What you will build

Nothing: this lesson is about what you get when you install the package, and what you deliberately do
not. That distinction decides how you read every later lesson, because an optional capability is an
*install*, not an import that fails mysteriously.

## The Python range

Xyberos supports **Python 3.10 through 3.13**, tested in continuous integration on each of them.

=== "PowerShell"

    ```powershell
    python -m venv .venv
    .venv\Scripts\python -m pip install xyberos
    ```

=== "POSIX"

    ```bash
    python -m venv .venv
    .venv/bin/python -m pip install xyberos
    ```

## The extras

The core package has one dependency, and it is not a web framework, a database driver, or an AI SDK.
Everything else is an extra you ask for by name:

| Extra | What it adds | Install |
| --- | --- | --- |
| — | composition, dependency injection, scopes, lifecycle, configuration, workflows, plugins, and the AI facade with a fake provider | `pip install xyberos` |
| `http` | the Starlette-backed HTTP adapter | `pip install "xyberos[http]"` |
| `database` | the SQLite provider, Alembic migrations, and the provider conformance suite | `pip install "xyberos[database]"` |
| `ollama` | the Ollama adapter | `pip install "xyberos[ollama]"` |
| `durable` | the experimental durable executor | `pip install "xyberos[durable]"` |

The AI facade being in core is the part that surprises people, so it is what the example proves.

## The code

<!-- snippet: examples/learn_fundamentals/fundamentals02_install.py -->

## How to run it

=== "PowerShell"

    ```powershell
    $env:PYTHONPATH = "src;examples"
    python -m learn_fundamentals.fundamentals02_install
    ```

=== "POSIX"

    ```bash
    PYTHONPATH=src:examples python -m learn_fundamentals.fundamentals02_install
    ```

In your own project, `python -m pip install xyberos` is the only prerequisite; this file needs no extra.

## What it prints

<!-- output: fundamentals02_install -->
```text
xyberos 2.2.0
importing the AI facade pulled in an SDK: False
an answer with no SDK installed: hello from the fake
```

Read the middle line carefully: the module records whether `httpx` was loaded *before* importing
`xyberos.ai`, then checks again. Importing the facade pulls in no vendor SDK, in any environment —
which is why the last line can ask a model for an answer with nothing installed but the core package.

## Common mistakes

- **Installing an extra you do not need.** The core package is the smallest thing that can run an
  application; adding `http` to a script that never answers a request is a dependency you now maintain.
- **Expecting a helpful error from a bare import.** A missing extra reports the extra to install, and
  the message is part of the contract — the command line repeats it verbatim. That is why
  `tests/test_optional_dependencies.py` exists.
- **Assuming the AI facade needs a model service.** It needs one when you point it at a real provider.
  The fake provider is not a mock of the facade; it is a provider, with declared capabilities, that
  answers instantly.

## Exercise

Run the same file with an extra installed and count the difference.

<details>
<summary>Show the answer</summary>

=== "PowerShell"

    ```powershell
    python -m pip install "xyberos[http]"
    $env:PYTHONPATH = "src;examples"
    python -m learn_fundamentals.fundamentals02_install
    ```

The output does not change. Installing an extra makes a capability *available*; it does not make the
core package import it, which is exactly the property the middle line of output tests.

Check it from the other direction: `python -c "import sys, xyberos; print([m for m in ('starlette',
'sqlalchemy') if m in sys.modules])"` prints `[]` with the extras installed.
</details>

## Next

Lesson 3 creates a project you can run, so that the rest of the path works on a real layout rather
than on a single file. Until it is published, [the roadmap](../../roadmap.md) shows where each lesson
stands.

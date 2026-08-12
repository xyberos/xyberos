# Contributing to Xyberos

First off — thank you for considering a contribution! Xyberos is built around
stable contracts and a zero-dependency core, and contributions of every size
(bug reports, docs, tests, features, RFCs) are welcome.

## Table of contents

- [Code of conduct](#code-of-conduct)
- [Development environment](#development-environment)
- [Project layout](#project-layout)
- [Running the tests](#running-the-tests)
- [Coding standards](#coding-standards)
- [Documentation](#documentation)
- [The RFC process](#the-rfc-process)
- [Reporting issues](#reporting-issues)
- [Submitting a pull request](#submitting-a-pull-request)

---

## Code of conduct

Be respectful and constructive. This project aims to be a welcoming place for
contributors of all experience levels. Harassment, discrimination, or abusive
behavior is not tolerated.

## Development environment

1. **Fork and clone** the repository:

   ```bash
   git clone https://github.com/xyberos/xyberos.git
   cd xyberos
   ```

2. **Create a virtual environment** (Python 3.10+):

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

3. **Install in editable mode with dev extras:**

   ```bash
   pip install -e ".[dev]"
   ```

   This installs `pytest` and `pytest-cov`. The package itself has **zero
   runtime dependencies** — only the standard library.

4. **Verify the setup:**

   ```bash
   python -c "import xyberos; print(xyberos.__version__)"
   pytest
   ```

## Project layout

```text
xyberos/
├── kernel/        # config, logging, registry, lifecycle, event bus
├── runtime/       # cognitive context and runtime execution (sync + async)
├── brain/         # automated cognitive pipeline
├── contracts/     # the stable extension interfaces
├── agents/        # multi-agent runtime, roles, messaging, handoffs
├── workflows/     # sequential workflows, state graphs, checkpoints
├── plugins/       # plugin loading and auto-discovery
├── llm/           # model providers, streaming/async, structured output
├── memory/        # in-memory, SQLite, vector, consolidating providers
├── knowledge/     # in-memory, SQLite, vector, ingesting providers
├── planner/       # fixed, LLM, adaptive, reflective planners
├── intent/        # heuristic, LLM, embedding, cascade engines
├── router/        # hybrid responder chain (RFC-0017)
├── vector/        # vector store contract and providers
├── experience/    # episode store (RFC-0016)
├── learning/      # promotion, demotion, example promotion
├── trainer/       # offline training/distillation
├── tools/         # registries, runners, typed function tools
├── events/        # event bus, tracing, exporters
├── security/      # kill switch, guardrails, audit log
└── utils/         # resilience helpers + evaluation metrics

test/              # the test suite (mirrors the package layout)
docs/              # the documentation site (mkdocs)
examples/          # runnable example applications
```

## Running the tests

```bash
# Run the full suite (coverage is configured in pytest.ini)
pytest

# Run a single file
pytest test/test_brain.py

# Run with coverage report
pytest --cov=xyberos
```

The test suite is the **authoritative reference for current behavior** — if you
change behavior, update the tests, and add a test for every new feature or
fix.

## Coding standards

- **Line length:** 100 characters (configured in `pyproject.toml`).
- **Target:** Python 3.10+.
- **Linting:** [Ruff](https://docs.astral.sh/ruff/) — select `E`, `F`, `I`,
  `W`, `UP`. Run it before committing:

  ```bash
  ruff check .
  ruff format --check .
  ```

- **Type hints:** use modern type hints (e.g. `list[str]`, `Mapping[str, Any] | None`).
- **Dependencies:** never add runtime dependencies to the core. Optional
  integrations go behind lazy imports and optional extras (`dev`, `train`,
  `vectors`, `rerank`, `embeddings`).
- **Contracts first:** new subsystems extend the core through a contract in
  `xyberos/contracts/`. Default implementations are separate, swappable
  providers.

## Documentation

The docs live in [`docs/`](index.md) and are built with
[MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

- **The tutorial** is a W3Schools-style learning path in
  [`docs/learn/`](learn/01-what-is-xyberos.md) — each chapter adds one
  capability (knowledge → memory → tools → workflows → brain → agents →
  security → testing → build your Jarvis). Keep that progressive structure
  when adding chapters.
- **API docs** follow the "what it owns / when to use it" format in
  [`docs/api-reference.md`](api-reference.md).
- **Architecture decisions** are recorded as RFCs in
  [`docs/RFCs/`](RFCs/RFC-Roadmap.md).

Build and preview locally:

```bash
pip install mkdocs mkdocs-material
mkdocs serve
```

## The RFC process

Substantial architectural changes (new subsystems, contract changes, new
core layers) should be proposed as an **RFC** before implementation:

1. Copy `docs/RFCs/RFC-0001-architecture.md` as a starting template.
2. Number the new RFC as the next number in `docs/RFCs/`.
3. Describe the **problem**, the **proposed design**, the **contracts**
   affected, and the **default implementation**.
4. Open a draft PR for discussion before implementing the code.

Small features, bug fixes, and docs changes do **not** need an RFC — just
submit the pull request.

## Reporting issues

Before opening an issue:

- Search existing issues for a duplicate.
- Include your **Python version**, **Xyberos version** (`import xyberos;
  print(xyberos.__version__)`), and OS.
- Include a **minimal reproduction** — ideally a short script using only
  `xyberos` and the standard library.

For bugs, run the environment check and include its output:

```python
from xyberos import doctor
print(doctor().as_dict())
```

## Submitting a pull request

1. **Create a branch** off `master` with a descriptive name
   (`fix/`, `feat/`, `docs/`, `refactor/`).
2. **Make your change** — small, focused, with tests and docs where relevant.
3. **Run the checks**:

   ```bash
   ruff check .
   ruff format --check .
   pytest
   ```

4. **Commit** with a clear message describing *what* and *why*.
5. **Push and open a pull request** against `master`.

### PR checklist

- [ ] Tests pass (`pytest`)
- [ ] Ruff passes (`ruff check .`)
- [ ] New behavior has a test
- [ ] Public API changes are reflected in `docs/api-reference.md`
- [ ] New capabilities are reflected in the tutorial (`docs/learn/`) or guides
- [ ] No new runtime dependencies added to the core

### After review

Address review feedback, push updates, and keep the branch rebased on
`master`. Once approved, a maintainer will merge.

---

<p align="center"><strong>Core done. Build anything. Contribute more.</strong></p>

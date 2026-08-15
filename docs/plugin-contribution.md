# Build & Contribute Plugins

> **Related:** this page is the *plugin* half of the [Contributing Guide](contributing.md).
> For what is available today and what's planned, see the
> [Integration Roadmap](RFCs/RFC-0019-integrations-roadmap.md); for a hands-on
> walkthrough, see [Learn 24 — Build & Contribute Plugins](learn/24-plugin-development.md).

Turning plugin contribution into an automated developer workflow where Xyberos
does most of the boring architectural work — **without touching the core
package**. The core (`xyberos/`) is stable at v1.0.x and is extended
**additively** by policy; plugins are the sanctioned way to ship capabilities.

Everything in this plan is external tooling layered on top of the stable public
API: `create_app`, `kernel.register(...)`, `app.load_plugin()` /
`load_entry_points()` / `load_plugins_from()`, the introspectable contracts
(`Plugin`, `Tool`, `Memory`, `Knowledge`, `LLM`, `Vector`, `Workflow`, …), and
`ToolRegistry` / `FunctionTool`.

## The goal

The developer only needs to know:

> What does my integration do?

Xyberos handles:

> How does a Xyberos plugin work?

The generator becomes the "teacher". Instead of documentation saying *"implement
ToolPlugin, define metadata, configure lifecycle hooks, add tests…"*, the
developer runs `xyberos plugin create`, answers a few questions, and gets a
validated, tested, packaged plugin that is ready to PR.

## Architecture (all external)

```text
                 Xyberos Core (unchanged)
                      │
              ┌───────┴────────┐
              │                │
        Plugin Contracts    Plugin Runtime
        (import only)     (public API only)
              │                │
              └───────┬────────┘
                      │
                xyberos-plugin-sdk
               (typed plugin base classes,
                declarative loader)
                      │
              ┌───────┴────────┐
              │                │
         Scaffolding       Validator
         (generator)      (introspection + live kernel)
              │                │
              └───────┬────────┘
                      │
                xyberos-cli
                      │
              ┌───────▼────────┐
              │  Ask Developer │
              │   Questions    │
              └───────┬────────┘
                      │
                      ▼
              Generate Plugin
                      │
                      ▼
              Generate Tests
                      │
                      ▼
             Generate README
                      │
                      ▼
             Validate Plugin
                      │
                      ▼
                Ready to PR
```

No new contract, no kernel change, no runtime change. The SDK, generator,
validator, and CLI are independent packages that import the stable core.

## The one rule: derive everything from the contracts

Don't create `contract.py` and `template.py` as two independently maintained
definitions. Otherwise six months from now:

```text
Xyberos contract  = v2
Plugin generator  = still generating v1
```

Instead, the generator and the validator both derive their definition from the
contracts **by introspection** — import the contract class, read
`__abstractmethods__`, and use `inspect.signature()` for method shapes. One
definition, two consumers — much harder to drift.

```text
             Contract (imported, introspected)
                │
        ┌───────┴────────┐
        ▼                ▼
    Generator         Validator
        │                │
        └───────┬────────┘
                ▼
          Same definition
```

## The approaches (each independent of the core)

### 1. Typed plugin layer in an external SDK
`xyberos-plugin-sdk` ships `ToolPlugin(Plugin)`, `MemoryPlugin(Plugin)`, … as
thin base classes **layered on top of** the core's generic `Plugin` contract
(`name` / `register(kernel)` / `unregister(kernel)`). Their `register()` calls
the existing public `kernel.register(...)` / `ToolRegistry` APIs. The core stays
untouched; "typed plugins" become an SDK concern, not a core one.

### 2. Introspection-driven generator + validator
No metadata is added to the contracts. Templates and validation rules are
derived at runtime from the imported contracts (`__abstractmethods__`,
`inspect.signature`, and the roadmap version markers already present in each
contract's docstring, e.g. `tool.py` = "v0.4", `plugin.py` = "v0.8").

### 3. Live-kernel validation in an isolated subprocess
`xyberos plugin validate` builds a real `create_app()`, `load_plugin()`s the
target, and runs the generated contract tests — inside a `subprocess` harness so
it never depends on or mutates the core. This catches failures that static
checks miss, e.g. "the signature is right but `register()` actually raises".

### 4. Contract tests generated from the ABCs
Enumerate `__abstractmethods__` of the imported contract and emit pytest cases:
the class is not abstract, method signatures match, and `register`/`unregister`
work against a real kernel. Same introspection source as the generator.

### 5. Declarative plugins via `[tool.xyberos]` in pyproject.toml
Support config-driven authoring:

```toml
[tool.xyberos.plugins.github]
type = "tool"
auth = "token"
capabilities = ["repositories", "issues", "pull_requests"]
```

The SDK ships a single module that reads this table and registers everything
through the public kernel API. The app's **existing** `xyberos.plugins`
entry-point group points at that module, so core discovery is reused as-is.

### 6. AST-based `--fix` / repair in the CLI
`xyberos plugin repair` and `validate --fix` mechanically fix authorable
problems (e.g. adding a missing `context` parameter) by rewriting the source
with Python's `ast`. A pure CLI concern.

### 7. CI/PR validation as a GitHub Action
A standalone `xyberos-plugin-validator` action runs on every PR against a plugin
repo, institutionalizing the contribution pipeline.

## The CLI experience

`xyberos plugin create` asks:

```text
What is your plugin name?            > github
What type of plugin is this?
  1. Tool  2. LLM Provider  3. Memory  4. Knowledge
  5. Vector Store  6. Workflow  7. Other                 > 1
What does this plugin integrate with?  > GitHub API
Does it require authentication?       > Yes
Authentication type?
  1. API Key  2. OAuth  3. Token  4. Custom               > 3
What capabilities will it provide?    > repositories, issues, pull requests
Do you want async support?            > Yes
Do you want streaming support?        > No
```

Then it generates: project structure, plugin contract, metadata, configuration,
authentication interface, capability declarations, async interface, test
scaffolding, example, README, and `pyproject.toml`.

`xyberos plugin validate` reports structure / contract / configuration /
testing / documentation / compatibility, then ends with `Result: PASS`. On
failure it shows what is wrong, the expected vs found shape, and suggests
`xyberos plugin repair` (or `validate --fix` for mechanically fixable
problems).

## Contribution pipeline

```text
CREATE → IMPLEMENT → TEST → VALIDATE → DOCUMENT → PACKAGE → PULL REQUEST
```

## Package layout (external, independent)

```text
xyberos-plugin-sdk         typed base classes + declarative loader
xyberos-plugin-validator   introspection + live-kernel validation
xyberos-cli                wizard, generate, validate, repair
```

Optionally dogfood: distribute the CLI itself as a plugin loaded through the
existing `xyberos.plugins` entry-point group.

## What the core does NOT change

- No new contracts; no contract edits (versions stay docstring prose).
- No kernel / registry / loader / runtime changes.
- No new entry-point groups (reuses `xyberos.plugins`).

## Trade-offs

- Contract version IDs remain docstring prose unless a future, deliberate,
  additive change adds a machine-readable field.
- Typed-plugin enforcement happens at SDK `register()` time, not in the core.

## Implementation status (all milestones implemented)

All six milestones are implemented in this repository as three external,
independent packages — the core (`xyberos/`) is untouched.

| # | Milestone | Where | Status |
| - | --------- | ----- | ------ |
| 1 | Introspection layer (contract → method set + signatures) | `xyberos_plugin_sdk/introspect.py` | ✅ |
| 2 | `xyberos-plugin-sdk`: typed base classes + declarative loader | `xyberos_plugin_sdk/{base,declarative}.py` | ✅ |
| 3 | Subprocess live-kernel validator | `xyberos_plugin_validator/{checks,live,_runner}.py` | ✅ |
| 4 | `xyberos-cli` wizard + generator | `xyberos_cli/{main,create}.py` | ✅ |
| 5 | AST-based repair / `--fix` | `xyberos_cli/{repair,validate}.py` | ✅ |
| 6 | GitHub Action for PR validation | `.github/actions/xyberos-plugin-validator/` + `.github/workflows/plugin-validation.yml` | ✅ |

### Quick start

```bash
pip install -e ./xyberos_plugin_sdk -e ./xyberos_plugin_validator -e ./xyberos_cli

xyberos plugin create --name github --type tool --description "GitHub integration" \
    --integrate-with "GitHub REST API" --auth token --non-interactive
cd github
pip install -e .
xyberos plugin validate .            # static + live-kernel PASS/FAIL
xyberos plugin repair . --check      # preview missing contract stubs
```

The shared introspection rule is enforced: the generator and the validator both
derive their definitions from `xyberos_plugin_sdk.introspect`, which reads the
contracts (`__abstractmethods__` / protocol bodies) at runtime — so they cannot
drift as the contracts evolve.
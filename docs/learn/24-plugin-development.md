# 24. Build & Contribute Plugins

[**← Previous**](23-customer-support-tutorial.md) · [**Next →**](../contributing.md)

## What You'll Learn

- The plugin toolkit: `xyberos-plugin-sdk`, `xyberos-plugin-validator`, `xyberos-cli`
- Scaffold a plugin in seconds with `xyberos plugin create`
- The generated project structure
- Typed plugin base classes (the SDK)
- Declarative plugins via `[tool.xyberos.plugins]`
- Validate a plugin — static checks + a live-kernel check in a subprocess
- Auto-repair missing contract members with `xyberos plugin repair`
- Enforce it all in CI with the GitHub Action

The whole toolkit is **external and additive** — it imports the stable Xyberos
public API and never modifies the core. See
[`plugin-contribution.md`](../plugin-contribution.md) for the
design and the [integration roadmap](../RFCs/RFC-0019-integrations-roadmap.md)
for where each plugin fits.

---

## 1. The toolkit at a glance

```text
Xyberos core (unchanged)
        │   (imports the stable public API only)
        ▼
xyberos-plugin-sdk        typed base classes + declarative loader + introspection
xyberos-plugin-validator  static checks + subprocess live-kernel validation
xyberos-cli                `xyberos plugin create | validate | repair`
```

One rule drives the whole design: **everything is derived from the contracts**
by introspection. The generator and the validator both read the contract ABCs
(`Tool`, `Memory`, `Knowledge`, `VectorStore`, `LLMProvider`, …) at runtime, so
a scaffolded plugin always matches the current contracts — they can't drift.

### Install

```bash
pip install xyberos-cli        # pulls in the sdk + validator
```

From this repository's source:

```bash
pip install -e ./xyberos_plugin_sdk -e ./xyberos_plugin_validator -e ./xyberos_cli
```

---

## 2. Scaffold a plugin

### Interactive wizard

```bash
xyberos plugin create
```

Answer a few questions — name, plugin type, description, what it integrates
with — and a complete, tested, entry-point-ready plugin is written to disk.

### Non-interactive (great for scripts/CI)

```bash
xyberos plugin create \
    --name github \
    --type tool \
    --description "GitHub API integration" \
    --integrate-with "GitHub REST API" \
    --auth token \
    --non-interactive
```

Plugin types map one-to-one to contracts:

| `--type` | Contract |
| -------- | -------- |
| `tool` | `Tool` |
| `llm` | `LLMProvider` |
| `memory` | `Memory` |
| `knowledge` | `Knowledge` |
| `vector` | `VectorStore` |
| `workflow` | `Workflow` |
| `planner` | `Planner` |
| `agent` | `Agent` |
| `service` | `Service` |
| `other` | `Plugin` |

### The generated project

```text
github/
├── pyproject.toml          # entry point: [project.entry-points."xyberos.plugins"]
├── README.md
├── github/
│   ├── __init__.py
│   ├── config.py           # Config dataclass + from_env()
│   ├── service.py          # the contract implementation (Tool, Memory, …)
│   └── plugin.py           # a typed Plugin + the `plugin` export
├── tests/test_plugin.py    # load + contract tests
└── examples/example.py
```

`pyproject.toml` declares the `xyberos.plugins` entry point, so once the package
is installed, `app.load_entry_points()` discovers it automatically:

```toml
[project.entry-points."xyberos.plugins"]
github = "github.plugin:plugin"
```

---

## 3. The SDK: typed plugins

The SDK ships thin typed base classes layered on the generic `Plugin` contract
(`name` / `register(kernel)` / `unregister(kernel)`). Their `register()` wires
the contribution through the public kernel API, so you never hand-write
registration boilerplate.

```python
# github/plugin.py
from xyberos.contracts import Tool
from xyberos_plugin_sdk.base import ToolPlugin

from .service import GithubTool


class GithubPlugin(ToolPlugin):
    @property
    def name(self) -> str:
        return "github"

    def tools(self) -> list[Tool]:
        return [GithubTool()]


plugin = GithubPlugin()   # entry-point target
```

The typed bases are: `ToolPlugin`, `LLMPlugin`, `MemoryPlugin`,
`KnowledgePlugin`, `VectorPlugin`, `WorkflowPlugin`, `PlannerPlugin`,
`AgentPlugin`, `ServicePlugin` — each with one abstract "contribute" method
(`tools()`, `llm()`, `memory()`, `knowledge()`, `vector_store()`, `workflow()`,
`planner()`, `agent()`, `service()`).

---

## 4. Implement the service

`service.py` is where the real work happens. The scaffold derives the stub
from the contract, so you only fill in the TODO:

```python
# github/service.py
from typing import Any

from xyberos.contracts import Tool


class GithubTool(Tool):
    @property
    def name(self) -> str:
        return "github"

    def execute(self, context: object, **arguments: Any) -> Any:
        # TODO: call the GitHub REST API and return a structured result.
        raise NotImplementedError
```

Load it locally to try it:

```python
from xyberos import create_app

from github.plugin import plugin

app = create_app()
app.load_plugin(plugin)
print(app.plugins.names)          # ('github',)
print(app.tools.names)            # ('github',)  — the tool is registered
```

---

## 5. Declarative plugins

Prefer configuration over code? Declare a plugin in `pyproject.toml` and bind
implementations in code:

```toml
[tool.xyberos.plugins.github]
type = "tool"
auth = "token"
capabilities = ["repositories", "issues", "pull_requests"]
```

```python
from xyberos_plugin_sdk.declarative import DeclarativePlugin, load_declarative

plugins = load_declarative("pyproject.toml")   # -> [DeclarativePlugin('github', {...})]
plugin = plugins[0].with_tool(GithubTool())

app.load_plugin(plugin)
```

The declarative plugin registers itself as `plugin.<name>` plus any attached
tools/services, all through the public kernel API.

---

## 6. Validate a plugin

```bash
cd github
pip install -e .
xyberos plugin validate .
```

The validator reports six checks, then a verdict:

```text
Xyberos plugin validation
----------------------------------------
✅ structure: PASS — found pyproject.toml and package github/
✅ configuration: PASS — entry point 'github' -> 'github.plugin:plugin' (group xyberos.plugins)
✅ documentation: PASS — README.md present
✅ testing: PASS — 1 test file(s) present (run with --run-tests)
✅ contract: PASS — GithubPlugin is a valid tool plugin
✅ compatibility: PASS — loaded + unloaded 'github' against a real create_app()
----------------------------------------
Result: PASS
```

The **compatibility** check is the important one: it builds a real
`create_app()`, loads the plugin, and unloads it — inside an **isolated
subprocess**, so it catches failures static analysis can't (e.g. "the signature
is right but `register()` actually raises"). It never touches your running
process.

Run the plugin's own tests too:

```bash
xyberos plugin validate . --run-tests
```

---

## 7. Auto-repair missing contract members

Missed an abstract method? `xyberos plugin repair` finds classes extending a
known contract and textually inserts implementable stubs — no reformatting of
the rest of the file:

```bash
xyberos plugin repair . --check     # preview what would change
xyberos plugin repair .             # apply
xyberos plugin validate . --fix     # repair, then validate
```

---

## 8. Enforce it in CI

A reusable GitHub Action runs the validator on every PR:

```yaml
# .github/workflows/plugin-validation.yml
on:
  pull_request:
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/xyberos-plugin-validator
        with:
          path: .
          run-tests: 'true'
```

---

## 9. The contribution pipeline

```text
CREATE → IMPLEMENT → TEST → VALIDATE → DOCUMENT → PACKAGE → PULL REQUEST
```

The wizard (CREATE), the generated tests (TEST), and the validator (VALIDATE)
do the boring architectural work; you supply the integration logic. From the
generator to the merged PR, the pipeline is the same every time — which is what
makes plugin contribution **standardized**.

## Further reading

- [`plugin-contribution.md`](../plugin-contribution.md) — the full toolkit design (introspection rule, declarative loader, repair, CI)
- [Integration Roadmap RFC](../RFCs/RFC-0019-integrations-roadmap.md) — status tracker + execution plan
- [Integration Roadmap RFC](../RFCs/RFC-0019-integrations-roadmap.md) — the execution plan (milestones, Definition of Done)

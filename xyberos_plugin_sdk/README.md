# xyberos-plugin-sdk

Typed plugin base classes, a declarative loader, and contract introspection
for building **Xyberos** plugins.

Everything in this package is **external and additive**: it imports only the
stable public API of `xyberos` (the contracts, `create_app`, `kernel.register`,
entry points) and never modifies the core.

## Install

```bash
pip install xyberos-plugin-sdk
```

## Typed plugins

```python
from xyberos.contracts import Tool
from xyberos_plugin_sdk.base import ToolPlugin


class GreetTool(Tool):
    @property
    def name(self) -> str:
        return "greet"

    def execute(self, context: object, **arguments) -> object:
        return f"hello, {arguments.get('who', 'world')}"


class GreetPlugin(ToolPlugin):
    @property
    def name(self) -> str:
        return "greet"

    def tools(self):
        return [GreetTool()]
```

## Declarative plugins

Define a plugin in `pyproject.toml` and load it with
`xyberos_plugin_sdk.declarative`:

```toml
[tool.xyberos.plugins.github]
type = "tool"
auth = "token"
capabilities = ["repositories", "issues", "pull_requests"]
```

See `xyberos_plugin_sdk.introspect` for the contract introspection used by
the generator and validator (the "one rule" — derive everything from the
contracts so nothing can drift).

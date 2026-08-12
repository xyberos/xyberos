# 7. Give It Skills — Tools

[**← Previous**](06-memory.md) · [**Next →**](08-workflows.md)

## What You'll Learn

- What a tool (skill) is
- Create your first tool
- Typed function tools and JSON schemas
- Register & execute tools
- Tool parameters and results
- Tool errors
- Tool permissions
- Plugin basics (where skills live long-term)

---

## What is a tool?

A **tool** is a named capability your assistant can act on — look up an order,
open a ticket, run a search, format data. Tools are how a talk-only assistant
becomes useful.

```text
Assistant
   ↓
Tool Registry
   ↓
Tool (named capability)
```

## Create your first tool

The easiest way is `FunctionTool`, which turns a plain typed function into a
tool and derives a JSON schema from the signature:

```python
from xyberos.tools import FunctionTool, ToolRegistry

def lookup_order(order_id: str = "unknown") -> str:
    """Look up the status of an order by id."""
    return f"Order {order_id} status: shipped"

tool = FunctionTool("lookup_order", lookup_order,
                    description="Look up an order's status")
print(tool.schema)    # typed JSON schema derived from the signature
```

## Register & execute tools

```python
from xyberos.runtime.context import CognitiveContext

registry = ToolRegistry([
    FunctionTool("lookup_order", lookup_order, description="Look up an order's status"),
    FunctionTool("open_ticket", open_ticket, description="Open a new support ticket"),
])

# Run a tool by name, passing its arguments:
print(registry.execute("lookup_order", CognitiveContext("order"), order_id="A-100"))
# -> Order A-100 status: shipped
```

The registry validates and coerces arguments from the JSON schema — pass
`limit="5"` for an `int` parameter and it becomes `5`.

## Let the assistant use them

Hand-executing tools is the simplest start. The `Brain` can also dispatch a
matching tool automatically through the `ToolRunner`:

```python
from xyberos import create_app
from xyberos.tools import ToolRegistry

app = create_app(tools=registry)
```

The default heuristic selects a tool whose name appears in the prompt. For
schema-driven LLM tool selection, use `SchemaToolCaller`:

```python
from xyberos.tools import SchemaToolCaller

caller = SchemaToolCaller(app.llm, registry)
data = caller.run("look up order A-100", app.run("x"))
```

## Tool parameters & results

- **Parameters** — derived from the function signature (types, defaults, docs).
- **Results** — whatever the function returns (str, dict, etc.).
- **Validation** — missing, unknown, or mistyped arguments raise
  `ToolArgumentError`.

```python
def search(query: str, limit: int = 10) -> str:
    return f"search({query}, limit={limit})"

tool = FunctionTool("search", search, description="Search the catalog")
print(tool.execute(None, query="books", limit="5"))   # limit coerced to 5
```

## Tool errors

Tools fail loudly with typed exceptions:

```python
from xyberos.exceptions import ToolArgumentError

try:
    registry.execute("search", CognitiveContext("s"), query="books", limit="many")
except ToolArgumentError:
    print("bad arguments")
```

## Tool permissions

Permissions are the security layer around tools — gate what the assistant is
*allowed* to do. Combine:

- **Guardrails** — block harmful prompts before a tool runs.
- **Kill switch** — halt everything in an emergency.
- **Audit log** — record every security event.

```python
from xyberos import Guardrail, create_app

app = create_app()
app.security.add_guardrail(
    Guardrail("no-destructive", lambda ctx: "rm -rf" not in ctx.prompt)
)
```

> Full coverage in [15. Security](15-security.md).

## Plugins: where skills live long-term

A plugin can register tools (and other services) automatically. See
[9. Skills & Plugins — the plugin system](09-plugins.md) for the full picture.
Quick preview:

```python
from xyberos.contracts import Plugin

class MySkillsPlugin(Plugin):
    @property
    def name(self):
        return "skills"

    def register(self, kernel):
        kernel.register("tools", ToolRegistry([my_tool]), replace=True)

app.load_plugin(MySkillsPlugin())
```

## Default behavior

- With no `tools=`, Xyberos uses an **empty** `ToolRegistry` — no tools.
- `ToolRunner` dispatches a tool when its name matches the prompt (or the
  intent target names it).

## Common mistakes

- **Tools without typed signatures** — `FunctionTool` needs type hints to build
  the schema and validate arguments.
- **Forgetting descriptions** — a good `description` is what makes tools
  discoverable.
- **Ignoring `ToolArgumentError`** — always handle invalid arguments at the
  boundary.

## Next Step

[**8. Give It Plans & Workflows**](08-workflows.md) — automate processes and
plan multi-step tasks.

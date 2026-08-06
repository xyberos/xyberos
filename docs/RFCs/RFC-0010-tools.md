RFC-0010 — Tools

Title: Tool Extension Contract

Status: Accepted

Summary

Defines the Tools subsystem — named, typed capabilities that an agent or the
Brain can invoke to perform actions beyond text generation (lookups, API calls,
calculations).

Motivation

LLMs are text-in/text-out. Tools give them arms and legs — the ability to query
a database, call an API, or run a computation. A stable contract lets tools be
authored independently and discovered at runtime.

Contract

```python
class Tool(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        """A stable, unique name used to register and select the tool."""

    @abstractmethod
    def execute(self, context: object, **arguments: Any) -> Any:
        """Execute the tool and return its provider-specific result."""
```

Implementations

### FunctionTool

Wraps any typed Python callable. Derives a JSON schema from the function
signature (parameter names, types, defaults) and validates/coerces arguments
before invocation:

```python
def lookup_order(order_id: str = "unknown") -> str: ...

tool = FunctionTool("lookup_order", lookup_order,
                    description="Look up an order's status")
```

``build_json_schema(func)`` produces a JSON-schema description of the
callable's signature. ``coerce_arguments(schema, kwargs)`` validates types
before calling.

### ToolRegistry

A namespace of named tools with lookup and auto-dispatch:

```python
registry = ToolRegistry([tool1, tool2])
registry.execute("lookup_order", context, order_id="A-100")
```

### ToolRunner

The Brain's tool dispatcher. When prompt text mentions a tool name,
``ToolRunner`` matches and invokes it, short-circuiting LLM generation.
Matching is name-based — the LLM can also signal tool invocations in its
output.

Pipeline Integration

```text
Planner → Tools (dispatch) → LLM (generate)
```

Tools run before the LLM. If a tool produces a response, the pipeline may
short-circuit and skip LLM generation entirely.

Exceptions

- ``ToolArgumentError`` — missing, unknown, or mistyped arguments
- Raised before the underlying callable executes

RFC-0009 — Planner

Title: Planning Extension Contract

Status: Accepted

Summary

Defines the Planner subsystem — produces an ordered plan of action from an
execution context before the LLM generates a final response.

Motivation

Complex requests benefit from explicit planning. A planner decomposes a prompt
into steps (e.g., "1. check order status, 2. verify refund policy, 3. respond")
before the LLM generates, improving structured reasoning without changing the
model itself.

Contract

```python
class Planner(ABC):

    @abstractmethod
    def plan(self, context: object) -> Any:
        """Build and return a plan for the supplied execution context."""
```

The returned plan shape is provider-defined. The Brain records it on
``context.plan`` for downstream consumers (tools, workflows, observability).

Pipeline Integration

```text
Knowledge → Planner (record plan) → Tools → LLM
```

The plan is recorded on the context. By default it is NOT injected into the
model prompt. Set ``config["brain.inject_plan"] = True`` to append it.

Providers

| Provider | Strategy |
|---|---|
| ``SequentialPlanner`` | Fixed-step "memory → knowledge → tools → llm" |
| ``LLMPlanner`` | Asks the LLM to decompose the prompt into ordered steps |

``LLMPlanner`` supports a custom ``parse`` callable for non-line-based formats
(e.g., JSON step lists).

Example

```python
app = create_app(planner=LLMPlanner(llm))
app.config["brain.inject_plan"] = True
```

Future Directions

- Plan execution/verification loop (execute step, re-plan on failure)
- Confidence scoring and reflection on plan quality
- Adaptive planning that changes based on intermediate results

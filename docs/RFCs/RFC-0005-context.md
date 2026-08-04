RFC-0005 — Cognitive Context

Defines the Context object.

Context represents the complete state of one execution.

Implemented fields:

prompt
response
metadata
error
plan

- `plan` holds the provider-defined plan produced by the Brain's planner step.
- The Brain stores completed contexts through the Memory contract after each
  request and retrieves them before the next, so conversation history is
  available to future executions via the configured memory provider.

Future versions may add:

history
thoughts
actions
tool_results
cost
timing

Runtime must treat Context as the canonical execution state.
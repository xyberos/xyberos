RFC-0005 — Cognitive Context

Defines the Context object.

Context represents the complete state of one execution.

Version 1 fields:

prompt
response

Future versions may add:

history
memory
knowledge
thoughts
actions
tool_results
metadata
cost
timing

Runtime must treat Context as the canonical execution state.
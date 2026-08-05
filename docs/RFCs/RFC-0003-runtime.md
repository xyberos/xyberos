RFC-0003 — Runtime

Defines the Runtime execution engine.

Runtime is responsible for executing one cognitive cycle.

Input:

Context

Output:

Context

Pipeline

Context

↓

Brain

↓

Updated Context

Runtime is intentionally unaware of specific LLM providers.

In addition to the synchronous ``run``, the Runtime provides an async ``arun``
that awaits the brain's async pipeline, and it emits request lifecycle events
on the kernel event bus (request started / completed / failed).
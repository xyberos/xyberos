RFC-0004 — Brain

Defines the Brain subsystem.

Brain is responsible for cognition.

Implemented pipeline (v0.9):

Prompt

↓

Workflow (optional) — configured steps run first; a step that sets the response
is honored and the pipeline short-circuits

↓

Memory (retrieve) — past conversation turns are injected into the prompt

↓

Knowledge (query) — matching facts are injected into the prompt

↓

Planner (plan) — the plan is computed and recorded on the context

↓

Tools (dispatch) — a matching tool may handle the request before the model

↓

LLM (generate)

↓

Memory (store) — the completed turn is persisted for future requests

↓

Response

Every subsystem is optional. A Brain without any of them behaves like a plain
LLM wrapper, and all changes remain internal to the Brain — the Runtime
interface is unchanged.

Future revisions may add, without changing the Runtime interface:

- LLM-driven / adaptive planning (replacing the fixed-step SequentialPlanner)
- reflection and self-critique loops
- streaming responses
- structured outputs and typed tool results
- event hooks and observability
- configurable policy for whether the plan is injected into the model prompt
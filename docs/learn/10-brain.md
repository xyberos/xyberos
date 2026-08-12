# 10. Give It a Brain

[**← Previous**](09-plugins.md) · [**Next →**](11-context.md)

## What You'll Learn

- What the cognitive engine (Brain) is
- The automated cognitive pipeline
- Intent classification
- Planning
- Tool selection
- The hybrid router (LLM-free answers)
- Context construction
- Observing the pipeline

---

## What is the Brain?

The **Brain** is the orchestrator that runs the automated cognitive pipeline
for each request. You add capabilities (facts, history, tools, plans, intents)
and the brain uses them in the right order. You rarely call subsystems
yourself — you configure them and `app.chat()` does the rest.

```text
Input
 ↓
Intent
 ↓
Context
 ↓
Reasoning (plan)
 ↓
Tools
 ↓
Observation
 ↓
Response
```

## The cognitive pipeline

A single `app.chat(prompt)` runs the automated pipeline:

```text
Workflow → Memory → Knowledge → Intent → Plan → Router/Tools → LLM → Memory
 (pre-steps) (history)  (facts)   (goal)   (steps)  (actions)    (reply) (remember)
```

For each request, `Brain.chat()` runs the configured subsystems in order:

1. **Workflow** — pre-steps run; a step that sets the response short-circuits.
2. **Cheap-first router** — when installed, its LLM-free tiers may answer
   before any LLM call (template → tool → knowledge → memory → cache).
3. **Memory** — past turns are retrieved and injected.
4. **Knowledge** — matching facts are queried and injected.
5. **Intent** — if enabled (`brain.intent`), the request is classified and
   recorded on `context.intent`.
6. **Planner** — the plan is computed and recorded on `context.plan`.
7. **Router** — a configured `Router` gets a chance to answer; a confident
   tier short-circuits.
8. **Tools** — a matching tool is dispatched via the `ToolRunner`.
9. **LLM** — the enriched prompt is sent to the model.
10. **Memory** — the completed turn is stored for future requests.

Every step is optional. A bare `Brain` behaves like a plain LLM wrapper.

## Intent classification

Intent engines classify a request before planning, so routing can be
intent-aware. Enable it and route to tools/agents/workflows:

```python
from xyberos import create_app
from xyberos.intent import HeuristicIntentEngine, IntentRule

app = create_app(
    intent=HeuristicIntentEngine(
        [IntentRule("refund", ("refund", "money back"), target="refund_tool")]
    ),
    config={"brain.intent": True},
)
```

When enabled, the brain classifies each request, records it on
`context.intent`, and emits `brain.intent_classified`. `ToolRunner.choose`
honors `context.intent.target` first.

Engines:

- `HeuristicIntentEngine` — deterministic rules, no LLM.
- `LLMIntentEngine` — open-ended classification via the model.
- `EmbeddingIntentEngine` — learns by accumulation (`learn(name, example)`).
- `CascadeIntentEngine` — cheap engines first, stronger engines on low
  confidence.

## Planning

The planner produces the step list (see [8. Plans & Workflows](08-workflows.md)):

```python
print(app.run("build a report").plan)   # -> ['research', 'draft', 'review']
```

## Tool selection

A matching tool is dispatched through the `ToolRunner` — by prompt-name
heuristic or `context.intent.target` first. For schema-driven selection, use
`SchemaToolCaller` (see [7. Tools](07-tools.md)).

## The hybrid router (LLM-free answers)

The **router** answers each request with the *cheapest confident tier* first:

```text
Template → Tool → Knowledge → Memory → Cache → LLM → Degrade
 (canned)  (actions)  (facts)  (history)  (learned)  (novel tail)  (fallback)
```

- Tiers 0–4 can answer **without any LLM call**.
- The LLM handles only the **novel tail**, and it **teaches** the cache — so
  the same question next time is served by the cache, not the model.

```python
from xyberos import create_semantic_app
from xyberos.llm import OllamaLLM, OllamaEmbeddingLLM

app = create_semantic_app(
    llm=OllamaLLM(model="llama3.2"),
    embedder=OllamaEmbeddingLLM(model="nomic-embed-text"),  # real semantics
    router="hybrid",
)
```

> Semantic matching needs a **real embedder**; the default `HashEmbedder` only
> matches near-identical text.

## Observing the pipeline

Every step publishes events to `app.events`:

```python
from xyberos.events import EventRecorder

recorder = EventRecorder(limit=10_000).subscribe_to(app.events)
app.chat("hello")
print(recorder.counts())
# {'brain.response_produced': 1, 'brain.memory_stored': 1, ...}
```

## Default behavior

- `create_app()` wires the in-memory defaults and a fully automated brain.
- The default `HeuristicIntentEngine` is empty (no rules) unless you pass
  rules; intent is off unless `brain.intent` is `True`.

## Common mistakes

- **Thinking you must call subsystems yourself** — you configure them; the
  brain orchestrates.
- **Replacing a provider after `create_app()`** — the brain captures providers
  at construction; build a fresh app (or use plugins).
- **Forgetting the embedder for semantic tiers** — knowledge/memory/cache
  tiers need a real embedder for paraphrase matching.

## Next Step

[**11. Context**](11-context.md) — the state object that ties everything
together.

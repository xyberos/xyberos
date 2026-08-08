# RFC-0016 — Trainable Cognitive Engines

| | |
|---|---|
| **Status** | Draft |
| **Version** | 1.x (stable line) — this RFC extends it additively |
| **Owner** | Core |
| **Scope** | Intent, Planning, Memory, Knowledge + a shared Learning/Experience layer |

---

## Summary

Xyberos already orchestrates memory, knowledge, planning, tools, and agents. What it
**does not** have is anything that *learns*. There are no embeddings, no vector store,
no experience/feedback capture, no intent classification, and no way to turn runtime
outcomes into better behavior.

This RFC makes the core **trainable** — not by baking model weights into it, but by
adding the four missing foundations, in priority order:

1. **Intent engine** — a first-class `IntentEngine` contract + Brain pipeline slot that
   routes a request to the right planner mode / tool / agent / workflow with a confidence
   score. Today the only routing is `ToolRunner.choose()`'s substring heuristic.
2. **Embeddings + vector retrieval** — the semantic foundation that makes Memory and
   Knowledge "learn by accumulation" and gives every engine an example-retrieval store.
   Shipped as duck-typed capabilities and **optional-dependency** providers, so the core
   keeps zero required runtime deps.
3. **Learning/Experience layer** — an `ExperienceStore` that records every episode
   (prompt, intent, plan, tool calls, response, outcome, feedback). This is the *training
   signal source*. Without it, nothing can be trained.
4. **Trainable engine providers** — intent, planner, memory, and knowledge providers that
   consume the experience layer (few-shot examples, semantic retrieval, outcome-based
   re-planning), plus an **optional offline trainer** for distillation/fine-tuning.

The guiding position (see *The Better Way* below): **runtime adaptation via retrieval,
few-shot examples, and outcome feedback is the default "training"; supervised fine-tuning
is an optional, opt-in plugin for high-volume, stable, domain-specific cases.** This keeps
the stable 1.x contracts intact, respects the additive-extension rule, and matches how
production agent frameworks actually get "smarter."

---

## Motivation

The current Brain pipeline is fixed and deterministic:

```text
Workflow (optional)
  ↓
Memory (retrieve)     — SqliteMemory: returns ALL turns, no ranking
  ↓
Knowledge (query)     — SqliteKnowledge: substring keyword match only
  ↓
Planner (plan)        — SequentialPlanner (fixed steps) or LLMPlanner (one-shot)
  ↓
Tools (dispatch)      — ToolRunner.choose: substring name match
  ↓
LLM (generate)
  ↓
Memory (store)
```

It is a *platform* — every subsystem is optional and swappable — but none of the
subsystems adapt. Observed gaps, all verified in the current source:

- **No intent.** `grep -ri intent` finds nothing in `xyberos/`. The support-assistant
  example hand-rolls a regex. Routing = `if name in prompt: return name`.
- **No semantic retrieval.** `SqliteMemory.retrieve` returns every row; `SqliteKnowledge`
  does `key in prompt`. No embeddings exist anywhere.
- **No learning signal.** Nothing records outcomes, tool success/failure, or user
  feedback, so there is no data to "train" on.
- **Planning is one-shot.** `LLMPlanner` produces a plan once; there is no execute →
  verify → re-plan loop, and no plan confidence/reflection (both are listed as open items
  in RFC-Roadmap §6).

The roadmap already defers "vector providers" (RFC-Roadmap §2) and asks for a
"plan execution/verification loop … re-plan on failure … confidence/reflection"
(RFC-Roadmap §6). This RFC is the coherent program that delivers all of those, plus the
missing intent and experience layers, under one design.

---

## The Better Way (Design Position)

The natural instinct is "add an intent engine, planner engine, memory engine … and make
them **trainable** (i.e. fine-tuned models)." That is usually the wrong first move. The
recommendation here is:

> **Do not put gradient-based training in the core. Build a runtime learning layer —
> experience capture → retrieval + few-shot examples + outcome-based adaptation — with
> embeddings as the substrate, and treat fine-tuning as an optional offline plugin for
> distilling proven behavior into a smaller/cheaper model.**

### What "trainable" means (be precise)

| Mechanism | When it trains | Cost | Where it lives |
|---|---|---|---|
| **Few-shot / in-context** | Per request (examples retrieved and injected) | Zero deps, zero weights | `ExampleStore` + any engine |
| **Embedding retrieval** | Continuously ("learns by accumulation" — add an example, retrieval improves) | Optional deps | `VectorStore` + `Embedder` |
| **Outcome-based adaptation** | Per episode (bandit-style: promote what worked, demote what failed) | Zero deps | `ExperienceStore` + planners/intent |
| **Offline supervised fine-tuning** | Offline, on a curated dataset | Optional extras (`sklearn`/`torch`/adapter SDKs) | `Trainer` plugin (Phase 3) |

The first three give ~90% of the "smartness" with **zero** new required dependencies and
**no** retraining/versioning burden. Fine-tuning is the last 10% and only pays off at
high volume on a stable domain. This RFC builds all four, in that order.

### Why this is better than "fine-tuned engines in core"

1. **No labeled data at scale → no training set to start.** You can start learning today
   with feedback/outcome signals; a fine-tune needs thousands of curated
   `(prompt → intent/plan/answer)` pairs you don't have yet.
2. **Drift is free.** Retrieval/few-shot adapt as examples accumulate; a fine-tuned
   checkpoint drifts and needs a re-train pipeline.
3. **Stable contracts + zero-deps stay intact.** The 1.x contract set is unchanged; we
   add three small `object`-typed contracts (`IntentEngine`, `VectorStore`,
   `ExperienceStore`) and an embeddings capability duck-typed on the LLM — exactly like
   `stream`/`agenerate` are duck-typed today. Heavy providers ship as optional extras.
4. **Observability and safety.** A learning layer is inspectable (episodes, examples,
   confidence) and reversible (delete examples, reset index). Model weights are a black
   box that is hard to audit.
5. **It matches how production agent frameworks operate** — strong backbone LLM +
   retrieval + tools + feedback loops, with fine-tuning reserved for distillation.

---

## Contract Additions (small, `object`-typed, backwards compatible)

New contracts follow the repo's invariant: **contracts depend on `object`, never on
`CognitiveContext`/`Runtime`**, so providers stay independent of core layers.

### 1. `xyberos/contracts/intent.py` — Intent Engine

```python
@dataclass(frozen=True)
class Intent:
    name: str                                   # e.g. "refund", "faq", "chat", "execute_task"
    confidence: float = 0.0                     # 0.0..1.0
    params: Mapping[str, Any] = field(default_factory=dict)   # extracted slots/args
    target: str | None = None                   # tool / agent / workflow name, optional

class IntentEngine(ABC):
    """Classify a request's intent. Providers stay decoupled from the Brain."""
    @abstractmethod
    def classify(self, context: object) -> Intent: ...

IntentEngineProvider = IntentEngine   # compatibility alias (repo convention)
```

### 2. `xyberos/contracts/vector.py` — Vector Store (semantic substrate)

```python
@dataclass(frozen=True)
class ScoredHit:
    id: str
    score: float
    payload: Mapping[str, Any] | None = None

class VectorStore(ABC):
    @abstractmethod
    def upsert(self, namespace: str, id: str, vector: Sequence[float],
               payload: Mapping[str, Any] | None = None) -> None: ...
    @abstractmethod
    def query(self, namespace: str, vector: Sequence[float],
              *, top_k: int = 5, threshold: float | None = None) -> list[ScoredHit]: ...
    @abstractmethod
    def delete(self, namespace: str, id: str) -> None: ...
    @abstractmethod
    def clear(self, namespace: str) -> None: ...
```

**Embeddings are a duck-typed LLM capability**, exactly like `stream`/`agenerate`:

```python
# optional method on LLMProvider (not in the Protocol)
def embed(self, text: str) -> Sequence[float]: ...
```

A helper `EmbeddingLLM(llm, embedder=None)` and an `OpenAIEmbeddingLLM` adapter are added
in `xyberos/llm/` / `xyberos/llm/adapters.py` (lazy import, `ProviderError` if the SDK is
missing — matching existing adapter policy).

### 3. `xyberos/contracts/experience.py` — Experience / Learning Layer

```python
@dataclass
class Episode:
    id: str
    prompt: str
    intent: Intent | None = None
    plan: Any = None
    tool_calls: list[Any] = field(default_factory=list)   # (tool, args, result, ok)
    response: str | None = None
    outcome: str | None = None        # "success" | "failure" | None
    feedback: float | None = None     # -1.0..1.0, from app.feedback()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

class ExperienceStore(ABC):
    @abstractmethod
    def record(self, episode: Episode) -> None: ...
    @abstractmethod
    def query(self, *, intent: str | None = None, outcome: str | None = None,
              limit: int = 20) -> list[Episode]: ...
    @abstractmethod
    def feedback(self, episode_id: str, rating: float, note: str | None = None) -> None: ...
    @abstractmethod
    def stats(self) -> Mapping[str, Any]: ...
```

### 4. Existing contracts — unchanged

`Planner.plan(context)`, `Memory.retrieve/store(context)`, `Knowledge.query(context)` are
**stable** — unchanged by this RFC. All new "engine" behavior is implemented as
**providers** of these existing contracts (plus the three new contracts above). No
existing interface changes.

---

## Engine Designs (providers)

### Intent engine

Providers in `xyberos/intent/` (new package):

- `HeuristicIntentEngine(rules: Sequence[Rule])` — regex/keyword cascade (promotes the
  support-assistant example into a first-class provider).
- `LLMIntentEngine(llm=None, *, schema=None, examples=None)` — structured-output
  classification via `StructuredLLM`/`extract_json`; returns `Intent` with confidence.
  Mirrors the `LLMPlanner(llm=None, *, parse=...)` shape.
- `EmbeddingIntentEngine(store, namespace="intents")` — nearest-neighbor over labeled
  examples in the vector store. **Trainable by accumulation**: call
  `learn(name, example_prompt)` to upsert.
- `CascadeIntentEngine(*engines, fallback=...)` — tries each in order, returns the first
  above a confidence threshold, else falls back to the heuristic/default. Produces the
  training signal "heuristic won → engine should learn this."

### Planner engine (upgrades existing `planner/`)

- `AdaptivePlanner(llm=None, *, store=None, top_k=3)` — injects the k most similar past
  `(prompt → plan)` episodes as few-shot demonstrations (via the vector/example store).
- `ReflectivePlanner(llm=None, *, reflect=...)` — after generation, a second LLM pass
  scores plan quality/confidence and can revise `context.plan` (config-gated).
- `ExecutingPlanner` / a new `PlanExecutor` (Phase 2) — runs each plan step as a tool
  call, verifies intermediate results, and **re-plans on failure** (the RFC-Roadmap §6
  open item). Reuses `ToolRunner`/`GraphWorkflow`; bounded by `max_steps`.

### Memory engine (providers of `Memory`)

- `VectorMemory(store, embedder, *, top_k=5, alpha=0.7)` — hybrid retrieval: embedding
  similarity × recency/importance decay. Preserves the `.prompt`/`.response` entry shape
  the Brain's history formatter expects.
- `ConsolidatingMemory(llm, *, interval=50)` — periodically summarizes/compacts old turns
  (LLM-written digest), applies importance scoring and forgetting. LLM-as-backbone, like
  `LLMPlanner`. Config-gated so default output is unchanged.

### Knowledge engine (providers of `Knowledge`)

- `VectorKnowledge(store, embedder, *, top_k=5)` — semantic retrieval over facts instead
  of `key in prompt`.
- `IngestingKnowledge(...)` — `add(document)` chunks → embeds → indexes; a tool result or
  LLM answer can be captured back into knowledge (implicit accumulation).

---

## Pipeline Integration

New Brain pipeline (additions marked **[NEW]**):

```text
Workflow (optional)
  ↓
Memory (retrieve)                       — SemanticMemory / ConsolidatingMemory
  ↓
Knowledge (query)                       — VectorKnowledge
  ↓
Intent (classify)        [NEW]          — context.intent set; emits brain.intent_classified
  ↓
Planner (plan)                          — AdaptivePlanner / ReflectivePlanner
  ↓
Tools (dispatch)                        — ToolRunner.choose honors context.intent.target
  ↓
LLM (generate)
  ↓
Memory (store)
  ↓
Experience (record)      [NEW]          — emit Episode; emits brain.episode_recorded
```

### Code touch-points (exact, minimal)

| File | Change |
|---|---|
| `xyberos/contracts/intent.py` | **new** — `Intent`, `IntentEngine` (+ alias) |
| `xyberos/contracts/vector.py` | **new** — `VectorStore`, `ScoredHit` |
| `xyberos/contracts/experience.py` | **new** — `Episode`, `ExperienceStore` (+ alias) |
| `xyberos/contracts/__init__.py` | export the three new contracts |
| `xyberos/brain/brain.py` | `__init__` gains `intent: IntentEngine | None` and `experience: ExperienceStore | None`; `_prepare`/`_enrich_prompt` adds the intent classify step; after `_remember`, record an `Episode`; new `feedback(episode_id, rating)` helper |
| `xyberos/tools/runner.py` | `choose()` checks `context.intent.target` first, then the existing heuristic as fallback |
| `xyberos/xyberos.py` | register `"intent"` / `"experience"` in `Xyberos.__init__`; add both to the `load_entry_points()` re-sync tuple (`("llm", "memory", "knowledge", "planner", "workflow", "tool_runner", "intent", "experience")`); `create_app(..., intent=..., experience=...)`; `app.feedback(...)` API |
| `xyberos/events/names.py` | add `brain.intent_classified`, `brain.episode_recorded`, `brain.feedback_recorded`, `engine.trained`, `engine.refreshed` |
| `xyberos/kernel/config.py` (docs) | document new `brain.*` / `intent.*` / `memory.*` / `knowledge.*` / `learning.*` keys |

### Config knobs (dotted keys, all default-off so current behavior is unchanged)

- `brain.intent` (bool) — enable the intent step
- `brain.inject_plan` (existing) — unchanged
- `intent.cascade` / `intent.fallback` / `intent.confidence_threshold`
- `planner.mode` (`"sequential" | "llm" | "adaptive" | "reflective"`)
- `memory.semantic` / `memory.consolidate` / `memory.consolidate_interval`
- `knowledge.vector`
- `experience.enabled` / `experience.store` (`"memory" | "sqlite"`)
- `learning.few_shot_top_k` / `learning.inject_examples`

---

## The Learning Loop (how it becomes "trainable")

```mermaid
flowchart LR
    A[Request] --> B[Brain pipeline]
    B --> C[ExperienceStore.record]
    C --> D{Feedback / outcome?}
    D -->|user feedback| E[mark Episode.feedback]
    D -->|tool success/failure| F[derive Episode.outcome]
    E --> G[ExampleStore / VectorStore]
    F --> G
    G --> H[Retrieval + few-shot injection]
    H --> A
    G -. offline .-> T[Trainer (Phase 3, plugin)]
    T -->|distill| M[(small model / artifact)]
    M -.-> A
```

1. **Record** — every turn writes an `Episode` (event `brain.episode_recorded`).
2. **Signal** — `app.feedback(episode_id, rating)` and implicit outcome derivation
   (tool success/failure, plan-verification result) update the episode.
3. **Learn (runtime)** — high-outcome episodes are promoted into the `ExampleStore` and
   upserted to the vector index; engines retrieve them as few-shot demonstrations.
4. **Distill (offline, optional)** — the `Trainer` plugin exports a dataset from the
   experience store and fine-tunes a small intent/planner model, or refreshes the
   embedding index / prompt. Artifacts land in an artifact directory and are loaded at
   startup via config (`learning.model`).

---

## Testing Plan (follows repo conventions)

One `_contract.py` + one `_provider.py` per new subsystem, plus integration:

- `test_intent_contract.py` — stub engine, `with pytest.raises(TypeError): IntentEngine()`,
  `isinstance(engine, IntentEngineProvider)`; `Intent` dataclass shape.
- `test_intent_provider.py` — heuristic/LLM/embedding/cascade providers; confidence
  thresholds; fallback; `learn()` accumulation.
- `test_vector_contract.py` / `test_vector_provider.py` — upsert/query/delete/clear;
  `CosineVectorStore` correctness (known vectors → expected ranking).
- `test_experience_contract.py` / `test_experience_provider.py` — record/query/feedback/
  stats; `SqliteExperience` persistence across restarts.
- `test_memory_provider.py` / `test_knowledge_provider.py` (extend) — semantic + 
  consolidating providers, preserving `.prompt`/`.response` entry shape.
- `test_planner_provider.py` (extend) — `AdaptivePlanner`/`ReflectivePlanner`; few-shot
  injection; re-plan loop bounds (`max_steps`, `HandoffLoopError`-style guard).
- `test_brain.py` (extend) — intent before tool dispatch, `context.intent` set, episode
  recorded, `brain.intent_classified`/`brain.episode_recorded` emitted, `app.feedback`.
- `test_learning.py` — promote/demote cycle: feedback → example promotion → retrieval
  improves → measurable metric (e.g., top-1 intent accuracy on a tiny fixture set).
- `test_public_api.py` / `test_package_structure.py` (extend) — new exports registered.

---

## Documentation Plan

- `docs/RFCs/RFC-0016-trainable-cognitive-engines.md` (this file) — the plan.
- `docs/extensions.md` — add an "Intent Engines", "Vector Stores", and "Experience &
  Learning" extension surface (following the existing per-contract guide pattern).
- `docs/api-reference.md` — new contracts/providers/events.
- `docs/configuring-services.md` — wiring examples: `create_app(intent=CascadeIntentEngine(...),
  experience=SqliteExperience("exp.db"))`, `app.feedback(...)`, optional extras install.
- `mkdocs.yml` — add RFC-0016 to the Architecture RFCs nav.

---

## Phased Implementation Roadmap

### Phase 0 — Foundations (the "make it trainable" groundwork) ✅
- [x] Add `VectorStore` contract + `CosineVectorStore` (pure-Python, no deps) + optional
      extras: `xyberos[vectors]` → chromadb / pgvector adapters.
- [x] Add duck-typed `embed()` LLM capability + `EmbeddingLLM` helper + `OpenAIEmbeddingLLM`
      adapter (lazy import).
- [x] Add `IntentEngine` contract + `HeuristicIntentEngine` + Brain slot + event
      (`brain.intent_classified`) + `Xyberos` wiring + `load_entry_points` sync tuple.
- [x] Add `ExperienceStore` contract + `InMemoryExperience` + `SqliteExperience`
      (+ episode recording in the Brain + `brain.episode_recorded`).
- [x] Events, config keys, contract/provider tests, docs.

### Phase 1 — Runtime-adaptive providers (the "trainable" engines) ✅
- [x] `LLMIntentEngine` + `EmbeddingIntentEngine` + `CascadeIntentEngine` (+ `learn()`).
- [x] `VectorMemory` (hybrid retrieval) + `ConsolidatingMemory` (LLM summarization).
- [x] `VectorKnowledge` + `IngestingKnowledge`.
- [x] `AdaptivePlanner` (few-shot) + `ReflectivePlanner` (confidence/reflection).
- [x] `ToolRunner.choose` intent-aware; `app.feedback()` API; promote/demote loop;
      integration + learning tests.

### Phase 2 — Closed-loop planning & evaluation ✅
- [x] `PlanExecutor` — execute plan steps via tools, verify, **re-plan on failure**
      (RFC-Roadmap §6); bounded loop with events.
- [x] Outcome-driven example promotion into `ExamplePromoter`; automatic consolidation
      scheduling for memory (`ConsolidatingMemory.consolidate_now`).
- [x] Evaluation harness: `xyberos/utils/eval.py` with datasets,
      metrics (intent top-1 accuracy, plan success rate, retrieval recall@k) and
      regression tests.

### Phase 3 — Optional offline fine-tuning (distillation, plugin)
- [ ] `Trainer` plugin: export dataset from `ExperienceStore` → optional `sklearn`/`torch`
      backend (`xyberos[train]` extras) → produce artifact (small intent/planner model or
      refreshed embedding index / optimized prompt).
- [ ] Artifact registry + `learning.model` config load; keep fine-tuned engines behind the
      same `IntentEngine`/`Planner`/`Memory` contracts so nothing in core changes.

Each phase is independently shippable and default-off, so current behavior and the 98%
coverage suite remain green at every step.

---

## Non-Goals & Risks

**Non-goals:** no changes to the `Runtime` request/response interface; no new required
runtime dependencies; no in-core fine-tuning; no breaking change to any stable 1.x
contract.

**Risks & mitigations:**

| Risk | Mitigation |
|---|---|
| New Brain slots are captured at construction (plugin replacements won't propagate) | Add `"intent"`/`"experience"` to the `load_entry_points()` re-sync tuple; document that hot-swap requires `load_entry_points()` or a fresh app |
| Semantic retrieval regresses "just works" defaults | All semantic/adaptive behavior is config-gated off by default; heuristic + substring fallbacks remain the default |
| Vector store unbounded growth | `clear(namespace)`, TTL/retention policy in `VectorMemory`, consolidation/forgetting |
| "Training" becomes a black box | Episodes, examples, and confidence are inspectable and reversible; evaluation harness gates regressions |
| Optional extras not installed | Providers raise a clear `ProviderError` (existing adapter pattern) when an optional dep is missing |

---

## Future Directions

- Schema-driven LLM function calling from `FunctionTool.schema` (RFC-Roadmap §7) — natural
  complement to intent→tool routing.
- Supervised multi-agent re-planning loops (RFC-Roadmap §5) driven by `ExperienceStore`.
- Cross-tenant privacy: episode/exemplar redaction before promotion to the example store.
- Embedding providers for local models (Ollama embeddings) as first-class adapters.

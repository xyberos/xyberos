# RFC-0017 — Hybrid Self-Routing: LLM as Fallback, Teacher & Quality Escalator

| | |
|---|---|
| **Status** | Draft (revised) |
| **Version** | 2.x — incorporates gap analysis & hybrid-stack recommendations |
| **Supersedes** | RFC-0017 v1.x |
| **Owner** | Core |
| **Scope** | A confidence-gated responder chain with template matching, knowledge retrieval, memory recall, distilled caching, local-model fallback, cloud-LLM escalation, and graceful degradation — plus CascadeIntentEngine integration and a "warm-up then detach" lifecycle |

---

## Summary

RFC-0016 made the core *trainable* (capture → promote → learn → evaluate →
distill). This RFC turns that into a **hybrid self-routing system**: a request
is answered by the **cheapest tier that is confident enough**, escalating only
when necessary. The key insight is that LLM-independence is a **spectrum**, not
a binary switch — the system earns independence over time through a warm-up
phase where the LLM acts as teacher, then progressively detaches.

```text
Template ──▶ Rules/Policies ──▶ Knowledge ──▶ Memory ──▶ Distilled Cache ──▶ Local Model ──▶ Cloud LLM ──▶ Degrade
  (variants)   (deterministic)  (facts/RAG)  (past Q→A)  (learned pairs)   (Ollama, etc.)  (last resort) (smart fallback)
```

The **LLM becomes a fallback and a teacher**, not the primary generator: it
handles the tail (novel/ambiguous requests) and distills its answers into the
cheaper tiers. Tiers 0–4 can serve requests with zero cloud dependency.

The revised design addresses three critical gaps identified in the v1.x analysis:

1. **Template brittleness** — templates without variation feel robotic. Fixed
   with multi-variant templates + context injection from memory/knowledge.
2. **Intent classification fragility** — heuristic-only intent fails on
   paraphrasing. Fixed with the `CascadeIntentEngine` (Heuristic → Embedding →
   LLM) integrated into the routing pipeline.
3. **Cold-start emptiness** — LLM-free tiers are empty until the LLM fills them.
   Fixed with a "warm-up then detach" lifecycle and pre-seeding support.

All seams are additive and **off by default**, so existing behavior is unchanged
until a router is installed.

**Implementation status:** the full milestone plan (M0–M14) is implemented — the
`xyberos/router` package ships `ResponderChain`, every responder tier
(Template → Tool → Knowledge → Memory → Cache → LLM → Degrade), the
`build_router` factory, warm-up `CacheTeacher`, confidence `CalibratedResponder`,
grounding, and the escalation `EscalationTuner`/`TierMonitor`. The semantic tiers
pair with a real embedder for paraphrase matching — e.g. `OllamaEmbeddingLLM`
(local Ollama `/api/embed`, stdlib HTTP) or `SentenceTransformerEmbedder`.

---

## Motivation

The RFC-0016 review identified six gaps between "trainable" and "self-routing":

1. **The LLM is the primary generator** — `Brain._prepare` only short-circuits on
   a workflow or tool result; there is no "answer from knowledge/memory/cache
   without the LLM" path, so every request pays full LLM cost.
2. **The intent cascade's terminal fallback is a static label**, not escalation.
3. **No unified fallback/router policy** spanning intent → tools → responder →
   LLM → offline.
4. **Escalation thresholds are static**, not learned from outcomes.
5. **Distillation covers intent only** — no response cache, no distilled planner.
6. **No model-level fallback chain or offline mode** — a provider outage means an
   outage; there is no `FallbackLLM` (cloud → local) and no LLM-less degraded
   answering.

Additional gaps identified in v2 analysis:

7. **Templates feel robotic** — a single static template per intent produces
   identical responses on repeat requests, making the system feel "dumb."
8. **Heuristic-only intent is brittle** — keyword matching fails on paraphrasing
   (e.g., "my stuff ain't showing up" ≠ "order status"), forcing over-reliance
   on the LLM.
9. **No warm-up lifecycle** — the LLM-free tiers are empty at startup; without
   a teacher phase, the router escalates everything to the LLM anyway.
10. **Degraded responses are dead ends** — a bare "I don't understand" offers no
    path forward for the user.

The goal: cheaper, faster, more resilient, **natural-feeling**, and — through
escalation learning — measurably smarter over time.

---

## Core Design Principle: The Spectrum, Not a Switch

LLM-independence is not all-or-nothing. The system operates on a continuum
controlled by two primary knobs:

| Knob | Effect |
|---|---|
| `router.confidence_threshold` | Higher = more escalation to LLM, more natural, more costly |
| `router.warmup_mode` | Whether the LLM "teaches" the cheaper tiers (on by default) |

```text
  Purely Deterministic ◀──────────────────────────────────────▶ Fully LLM-Driven
  (templates only)         (templates + cache)    (cache + local)   (cloud LLM tail)
  │                       │                      │                 │
  threshold=0.99          threshold=0.7          threshold=0.5     threshold=0.0
  warmup=off              warmup=on              warmup=on         warmup=off
```

The recommended production configuration sits at **threshold=0.7 with warmup**:
80-90% of requests are served by tiers 0-4, with the cloud LLM handling only
the genuinely novel or ambiguous tail.

---

## The Tiered Design

### Design refinements (v2 additions in **bold**)

1. **Split "gate" from "respond".** Every tier answers two questions: *can I
   handle this?* (a confidence/eligibility gate) and *what is the answer?*. A
   tier that can't respond returns `None` and the router escalates.
2. **Add a template tier** at position 0 — the cheapest, fastest responder for
   common patterns like greetings, FAQs, and well-known intents. **Templates
   support multiple variants and context injection** to avoid robotic repetition.
3. **Add a distilled cache tier** between memory and the local model. The LLM
   (or any successful responder) teaches; the cache serves identical/near
   requests without any model call.
4. **The model tier is itself a cascade** — local model first, falling back to
   cloud LLM on `ProviderError`/timeout, then to the degraded tier. **The local
   model is the preferred model tier** for cost and offline resilience.
5. **Bounded, evented escalation.** Every tier hit and every escalation is
   emitted as an event, so hit-rates are measurable and thresholds can be tuned.
6. **Graceful degradation with actionable fallbacks.** When nothing is confident,
   the degraded responder offers **context-aware suggestions** (try rephrasing,
   connect to human, list available capabilities) rather than a dead-end
   "I don't understand."
7. **Learn the gates.** Escalation thresholds are tuned from the
   `ExperienceStore` outcomes and feedback (bandit-style), not hard-coded.
8. **CascadeIntentEngine integration** — the intent classification itself uses a
   cascade (Heuristic → Embedding → LLM) so the routing decision is also
   progressively enhanced.

### The tier table (v2)

| Tier | Responder | Cost | Model needed | Natural? | Escalation when |
|---|---|---|---|---|---|
| 0 | **Template** (multi-variant + context injection) | ~0 | no | Yes (varied) | no pattern match |
| 1 | **Rules / policies / workflows** | ~0 | no | Partial | no deterministic match |
| 2 | **Knowledge** (`VectorKnowledge`, facts) | ~0 | no (embedding) | Yes (factual) | low retrieval score |
| 3 | **Memory** (episodic Q→A, few-shot) | ~0 | no (embedding) | Yes (prior answer) | no good past match |
| 4 | **Distilled cache** (learned Q→A) | ~0 | no | Yes (LLM-authored) | cache miss |
| 5 | **Local model** (Ollama / phi3 / llama3.2) | low | yes, local | Yes | low confidence / failure |
| 6 | **Cloud LLM** | high | yes, cloud | Yes | last resort |
| 7 | **Degrade** (smart fallback) | ~0 | no | Actionable | nothing else could |

Tiers 0–4 can serve requests with zero cloud dependency and zero model
generation cost. Tier 5 adds natural language generation at zero cloud cost.

### Why TemplateResponder is Tier 0 (not merged with Rules)

The original RFC-0017 merged templates into "Rules / policies / workflows."
This revision separates them because:

- **Templates produce natural-language responses** with variation and context
  injection — they replace the LLM for the response layer.
- **Rules produce actions** — tool dispatches, workflow triggers, policy
  enforcement — they replace the LLM for the decision layer.
- A template match at tier 0 means "I know what to say" without even checking
  rules, making it the absolute cheapest path.
- Templates decay to tier 1 (rules) when no pattern matches, keeping the
  separation clean.

---

## Intent Classification: The Cascade Within the Cascade

Intent classification itself follows the same progressive-enhancement pattern
as response routing. The already-existing `CascadeIntentEngine` is the vehicle:

```python
CascadeIntentEngine(
    HeuristicIntentEngine(rules=[
        IntentRule("greeting", ("hello", "hi", "hey", "good morning")),
        IntentRule("order_status", ("order", "track", "shipment", "where is my")),
        IntentRule("billing", ("bill", "invoice", "payment", "charge", "refund")),
        IntentRule("account", ("account", "password", "login", "profile")),
        IntentRule("support", ("help", "support", "issue", "problem", "broken")),
    ]),
    EmbeddingIntentEngine(store, embedder=..., threshold=0.6),
    LLMIntentEngine(llm=...),                       # only fires for truly novel phrasing
    confidence_threshold=0.7,                        # escalate below 0.7
)
```

| Engine | When it fires | Handles |
|---|---|---|
| Heuristic (tier 0) | Keyword match | "track my order", "reset password" |
| Embedding (tier 1) | Semantic similarity > 0.6 | "my stuff ain't showing up" → order_status |
| LLM (tier 2) | Nothing else confident | "I was wondering if perhaps you could..." |

The `confidence_threshold` is the dial: set it to 0.9 and the LLM only fires
for 5% of intents; set it to 0.5 and the LLM fires for 30%. The system learns
the right threshold from outcomes (RFC-0018 M13 → M14).

---

## The "Warm-Up Then Detach" Lifecycle

This is the most important operational pattern. LLM-free tiers are empty at
startup. The system must **earn** its independence:

```text
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1: WARM-UP (warmup_mode=enabled, default)            │
│                                                             │
│  Every request flows through ALL tiers, but the LLM always  │
│  generates. The LLM's answer is the "ground truth" that     │
│  teaches the cheaper tiers:                                 │
│                                                             │
│  Template match? → record "this pattern → this intent"      │
│  Cache miss?     → LLM generates → cache.teach(Q, A)        │
│  EmbeddingIntent → learn(intent, example) from LLM label    │
│  VectorKnowledge → auto-ingest rated LLM answers            │
│  Memory          → store every Q→A pair                     │
│                                                             │
│  Duration: configurable (N requests, time, or confidence)   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 2: DETACH (warmup_mode=disabled or auto-transition)  │
│                                                             │
│  Tiers 0-4 are now populated. The router short-circuits on │
│  the first confident tier. The LLM only fires for:          │
│  - Truly novel requests (cache miss + low knowledge score)  │
│  - Ambiguous intents (CascadeIntentEngine escalates)        │
│  - Complex reasoning beyond template/knowledge scope        │
│                                                             │
│  The LLM continues to teach in the background for any       │
│  requests that DO reach it, continuously shrinking its      │
│  share of traffic.                                          │
└─────────────────────────────────────────────────────────────┘
```

### Pre-seeding (shortcut for known domains)

For domains with existing FAQ/knowledge bases, the system supports **pre-seeding**
at startup to skip the warm-up phase entirely:

```python
# Pre-seed templates
app.router.template_responder.load([
    Template(pattern="greeting", variants=["Hello!", "Hi there!", "Welcome!"]),
    Template(pattern="order_status", variants=[
        "Let me look up your order. What's your order number?",
        "I can track that for you. Do you have the order ID?",
    ]),
])

# Pre-seed knowledge
app.knowledge.ingest([
    ("return policy", "Returns accepted within 30 days with receipt."),
    ("shipping times", "Standard shipping: 5-7 business days. Express: 2-3 days."),
])

# Pre-seed cache
app.router.cache_responder.teach_batch([
    ("how do I reset my password", "Go to Settings → Account → Reset Password..."),
    ("what are your hours", "We're open Mon-Fri 9AM-6PM EST."),
])
```

---

## TemplateResponder: Natural Responses Without an LLM

The `TemplateResponder` is the cornerstone of LLM-free natural language. A bare
template is robotic; the v2 design addresses this with three mechanisms:

### 1. Multi-variant selection

```python
class Template:
    """One response template with multiple variants."""
    pattern: str                    # regex or intent name to match
    variants: tuple[str, ...]       # randomly selected to avoid repetition
    confidence: float = 1.0         # how confident this match is (0-1)
    requires_context: tuple[str, ...] = ()  # memory/knowledge keys to inject

class TemplateResponder(Responder):
    def respond(self, context: CognitiveContext) -> str | None:
        match = self._match(context.prompt, context.intent)
        if match is None:
            return None
        if match.confidence < self._threshold:
            return None  # escalate — not confident enough
        variant = self._pick_variant(match)
        return self._inject_context(variant, context)
```

### 2. Context injection

Templates can pull data from memory and knowledge to feel personalized:

```python
# Template: "Your last {billing.amount} payment was on {billing.date}."
# Memory provides: billing.amount = "$49.99", billing.date = "Aug 1"
# Output: "Your last $49.99 payment was on Aug 1."
```

### 3. Confidence scoring

Not all template matches are equal. A regex match on "help" with no further
context might have confidence 0.3 ("probably a support request but could be
anything"). An exact intent match with high heuristic confidence gets 0.95.
Templates below the router threshold escalate instead of giving a wrong answer.

---

## Smart Degradation: Actionable Fallbacks

The `DegradedResponder` (tier 7) must not be a dead end. The v2 design specifies
**actionable degradation**:

```python
class DegradedResponder(Responder):
    POLICIES = {
        "offline": (
            "I'm currently unable to connect to my language model. "
            "Here's what I can still help with:\n"
            "{available_capabilities}\n\n"
            "You can also try rephrasing your request, or type 'agent' "
            "to connect with a human."
        ),
        "refusal": (
            "I wasn't able to find a good answer for that. "
            "Could you try asking in a different way? "
            "I can help with: {available_capabilities}."
        ),
        "human": (
            "Let me connect you with someone who can help. "
            "In the meantime, you can also check {knowledge_links}."
        ),
    }
```

The degraded responder dynamically lists available capabilities (derived from
registered tools, intents, and knowledge topics) and offers concrete next
steps — rephrase, connect to human, browse known topics.

---

## Contract Additions (additive, `object`-typed)

### `xyberos/contracts/responder.py` — Responder (NEW)

```python
class Responder(ABC):
    """Answers a request if it can; returns None to escalate."""

    @abstractmethod
    def respond(self, context: object) -> Any | None: ...

    def confidence(self, context: object) -> float:
        """Optional gate: 0.0 = cannot handle, 1.0 = certain."""
        return 1.0
```

### `xyberos/contracts/router.py` — Router (NEW)

```python
class Router(ABC):
    """Runs responders in priority order; escalates on None or low confidence."""

    @abstractmethod
    def respond(self, context: object) -> Any: ...
```

### Template support (NEW — in `xyberos/contracts/responder.py`)

```python
@dataclass(frozen=True)
class Template:
    pattern: str
    variants: tuple[str, ...]
    confidence: float = 1.0
    requires_context: tuple[str, ...] = ()

class TemplateResponder(Responder):
    def load(self, templates: Iterable[Template]) -> None: ...
    def respond(self, context: object) -> str | None: ...
```

### `xyberos/llm/fallback.py` — FallbackLLM (EXISTS, enhanced)

```python
class FallbackLLM:
    """Try a primary LLM, then fall back to local/other providers on failure."""

    def __init__(self, primary, *fallbacks) -> None: ...
    def generate(self, prompt: str) -> str: ...
    # Enhanced: stream/agenerate variants; cost-tracking; per-model metrics
```

---

## Providers (each is a `Responder`)

- **`TemplateResponder(templates, *, threshold=0.5)`** — multi-variant templates
  with context injection; tier 0.
- **`RuleResponder(rules)`** — deterministic rules/policies/workflows; tier 1.
- **`ToolResponder(tool_runner)`** — wraps `ToolRunner.dispatch()` as a responder.
  Returns the tool result when a tool matches the intent; returns `None` when
  no tool matches. Inserted between rules and knowledge in the default chain.
  **(NEW in v2)**
- **`KnowledgeResponder(knowledge, *, threshold=0.0)`** — answers from
  `VectorKnowledge`/fact retrieval; tier 2.
- **`MemoryResponder(memory, *, top_k=1, min_similarity=...)`** — answers from the
  most similar past `Q→A` in `VectorMemory`; tier 3.
- **`CacheResponder(store, *, embedder=None)`** — exact/near cache of learned
  `prompt → answer` pairs; `teach(prompt, answer)` records LLM answers so the
  next identical request skips the model entirely. Supports `teach_batch()` for
  pre-seeding; tier 4.
- **`DistilledResponder(engine)`** — a `Trainer`-distilled model (embedding
  index or sklearn) answering directly. Optional upgrade of tier 4.
- **`LLMResponder(llm)`** — wraps any `LLMProvider` (including `FallbackLLM`) as
  a responder tier. Tiers 5-6 depending on model.
- **`DegradedResponder(policy)`** — offline/canned/human-escalation with
  actionable suggestions; tier 7.

---

## Pipeline Integration

The Brain gains an optional `router` slot. The full pipeline becomes:

```text
Workflow
  → Memory(retrieve) → Knowledge(query) → Intent(classify) → Planner
  → Router:  Template → Rules → Tools → Knowledge → Memory → Cache → Local → Cloud
  → Degrade (last resort)
  → Memory(store) → Experience(record)
```

The router runs after enrichment (so context has memory, knowledge, intent, and
plan populated) and replaces the current `_generate` / `_agenerate` call when a
tier answers confidently. When the router is `None` (default), the Brain behaves
identically to today.

### Code touch-points

| File | Change |
|---|---|
| `xyberos/contracts/responder.py` | **new** — `Responder`, `Template`, `TemplateResponder` |
| `xyberos/contracts/router.py` | **new** — `Router`; `ResponderChain` in `xyberos/router/` |
| `xyberos/router/` | **new** package — all responders + chain |
| `xyberos/llm/fallback.py` | **enhance** — `stream`/`agenerate` variants, cost tracking |
| `xyberos/brain/brain.py` | optional `router` param; run in `_prepare`; emit hit/escalation events |
| `xyberos/xyberos.py` | `create_app(..., router=...)` + `create_semantic_app(..., router="hybrid")` |
| `xyberos/events/names.py` | `brain.responder_hit`, `brain.escalated`, `brain.degraded`, `brain.cache_hit`, `brain.template_hit`, `brain.warmup_phase`, `brain.detach_phase` |

### Config knobs (all default-off)

| Key | Values | Description |
|---|---|---|
| `brain.router` | `bool` | Enable the router slot |
| `router.mode` | `"off"` `"warmup"` `"hybrid"` `"detached"` | Operating mode |
| `router.responders` | ordered names | Which tiers, in priority order |
| `router.threshold` | `0.0–1.0` | Global confidence gate |
| `router.per_tier_threshold` | `{name: float}` | Per-tier confidence override |
| `router.degrade` | `"offline"` `"refusal"` `"human"` | Degradation policy |
| `router.warmup_requests` | `int` | Auto-transition after N requests |
| `llm.fallback_chain` | ordered model names | For `FallbackLLM` |
| `cache.path` | `str` | Persistent cache store path |
| `cache.pre_seed` | `dict[str, str]` | Pre-seeded Q→A pairs |
| `templates.path` | `str` | Template definitions file |

---

## The Recommended Hybrid Stack (Production Default)

This is the target configuration after full implementation:

```text
┌──────────────────────────────────────────────────────────────┐
│                  CascadeIntentEngine                         │
│   HeuristicIntentEngine → EmbeddingIntentEngine → LLMIntent  │
│   (keyword patterns)    (learned examples)      (novel only) │
└───────────────────────────┬──────────────────────────────────┘
                            │ intent + confidence
┌───────────────────────────▼──────────────────────────────────┐
│                    ResponderChain                             │
│                                                              │
│  Tier 0: TemplateResponder     ← multi-variant, context-rich │
│  Tier 1: RuleResponder          ← deterministic policies     │
│  Tier 2: ToolResponder          ← tool dispatch (NEW)        │
│  Tier 3: KnowledgeResponder     ← VectorKnowledge lookup     │
│  Tier 4: MemoryResponder        ← past Q→A similarity        │
│  Tier 5: CacheResponder         ← distilled LLM answers      │
│  Tier 6: LLMResponder(local)    ← Ollama phi3/llama3.2       │
│  Tier 7: LLMResponder(cloud)    ← FallbackLLM wrapper        │
│  Tier 8: DegradedResponder      ← actionable suggestions     │
└──────────────────────────────────────────────────────────────┘
```

**Expected traffic distribution after warm-up (threshold=0.7):**

| Tier | % of traffic | Cost/request | Quality |
|---|---|---|---|
| Template | 15-20% | ~$0 | Good (varied, contextual) |
| Rules/Tools | 10-15% | ~$0 | Deterministic |
| Knowledge | 15-20% | ~$0 (+ embedding) | Factual, verifiable |
| Memory | 10-15% | ~$0 (+ embedding) | Prior answer quality |
| Cache | 10-15% | ~$0 | LLM-authored (highest) |
| Local model | 15-20% | ~$0 (hardware) | Good for common cases |
| Cloud LLM | 5-10% | API cost | Best for complex/novel |
| Degrade | <1% | ~$0 | Actionable fallback |

**~85-90% of requests served with zero cloud LLM cost.**

---

## Learning the Escalation (Closes G4)

`ExperienceStore` already records every turn's outcome and feedback. The router
adds the tier that answered to the episode. With that signal:

- **Per-tier hit-rate** = how often each tier answered and was rated ≥ 0.
- **Per-tier quality score** = average feedback rating per tier.
- **Escalation tuning** — if a low tier answers but feedback is negative, its
  gate is raised (escalate sooner); if a high tier keeps being skipped or
  over-used, its gate is relaxed. This is the bandit-style loop the eval harness
  (`intent_accuracy`, `plan_success_rate`) already measures.
- **Warm-up completion** — auto-transition from warmup to detach when per-tier
  hit-rates stabilize above a configurable threshold.

---

## Risks & Mitigations (v2 — expanded)

| Risk | v1 Mitigation | v2 Enhancement |
|---|---|---|
| Cheap tiers degrade quality | Confidence gates + eval harness | **Warm-up phase ensures stores are populated before activation; template variants prevent robotic repetition** |
| Router changes default behavior | Entirely off by default | **`router.mode="off"` is the default; mode transitions are evented** |
| Cache returns stale answers | Similarity threshold + positive-rating filter | **TTL per cache entry; invalidation on knowledge update** |
| Provider outage still fails | `FallbackLLM` → Degraded | **Local model (tier 6) is the primary model; cloud is the fallback** |
| Escalation loops | Bounded chain | **Per-tier hit events + circuit breaker after N consecutive escalations** |
| Templates feel robotic | — | **Multi-variant selection + context injection + confidence gating** |
| Intent classification brittle | — | **CascadeIntentEngine (Heuristic → Embedding → LLM) with learned thresholds** |
| Cold-start: tiers empty at launch | — | **Warm-up phase + pre-seeding support; auto-transition when populated** |
| Degraded responses are dead ends | — | **Actionable suggestions: rephrase, list capabilities, connect to human** |

---

## The Canonical Build Sequence (v2 — re-ordered)

Shared with RFC-0018. **Follow M0 → M14 in order.**

```text
M0  [DONE]   FallbackLLM — cloud → local cascade                       RFC-0017
M1  Auto-outcome attribution — real Episode.outcome signals            RFC-0018
M2  Evaluation workflow + CI regression gate                           RFC-0018
M3  Immediate reinforcement — eager learn on positive feedback         RFC-0018
M4  Routing skeleton — contracts + all responder stubs +
    ResponderChain + Brain slot + events (INACTIVE until M11)          RFC-0017
M5  TemplateResponder — multi-variant + context injection              RFC-0017 · NEW
M6  Self-expanding knowledge — auto-ingest rated answers/results       RFC-0018
M7  Memory stratification — working facts vs episodic transcripts      RFC-0018
M8  CascadeIntentEngine integration — Heuristic→Embedding→LLM          RFC-0017 · NEW
M9  Schema-driven tool calling — from FunctionTool.schema              RFC-0018
M10 ToolResponder — tools as formal router tier                        RFC-0017 · NEW
M11 Router activation + warm-up mode (cache, distilled, config)         RFC-0017
M12 Response reflection & grounding check                              RFC-0018
M13 Reranking + confidence calibration (sharpens gates)                RFC-0018
M14 Escalation threshold tuning + auto-detach + DegradedResponder      RFC-0017
```

**Key ordering rules (v2 additions in bold):**

1. **Signals before learning** — M1 before M3, M14.
2. **Measure before you change** — M2 before M4, M11.
3. **Skeleton early, activation late** — M4 early but inactive until M11.
4. **Templates before cache** — M5 before M11 so template responses populate the
   quality baseline independently of LLM teaching.
5. **Intent cascade before router activation** — M8 before M11 so the
   router has a calibrated intent signal to gate on.
6. **Calibration before escalation** — M13 before M14.

---

## Testing Plan (v2 — expanded)

- `test_responder_contract.py` / `test_router_contract.py` — stubs, `TypeError`
  on abstract instantiation, no core coupling.
- `test_responder_provider.py` — each tier returns an answer or `None`.
- `test_template_responder.py` — multi-variant selection, context injection,
  confidence gating, pattern matching, pre-seeding.
- `test_router.py` — priority order, escalation on `None`/low confidence,
  bounded, fallback honored, hit/escalation events emitted.
- `test_fallback_llm.py` — primary failure → local fallback → degraded.
- `test_brain_router.py` — integration: router short-circuits before LLM;
  `brain.responder_hit`/`brain.escalated`; default unchanged.
- `test_warmup_lifecycle.py` — warm-up phase captures LLM outputs into all
  stores; auto-transition to detach when thresholds met.
- `test_cascade_intent_router.py` — Heuristic→Embedding→LLM cascade integrated
  with router; intent confidence feeds template/rule tier gating.
- `test_degraded_responder.py` — actionable fallback messages; capability
  listing; policy selection.
- `test_escalation_learning.py` — feedback raises/lowers a tier's gate.
- `test_pre_seeding.py` — pre-seeded templates, cache, and knowledge produce
  correct tier-0–4 responses without warm-up.

---

## Non-goals

- No change to the `Runtime` request/response interface.
- No new required runtime dependencies (Ollama and embeddings are optional extras).
- No change to the frozen RFC-0016 contracts.
- No in-core fine-tuning (stays the optional `Trainer` path).
- No real-time model switching mid-response (streaming across models is deferred).

---

## Future Directions

- **Teacher loop automation** — the cloud LLM's positively-rated answers
  automatically feed `CacheResponder.teach()` and the `Trainer`, continuously
  shrinking the LLM's share of traffic.
- **Per-tenant routing** — different tier orders/thresholds per user/domain,
  stored in the experience layer.
- **Async/streaming tiers** — async `Router`/`FallbackLLM` variants and
  streaming from the local/cloud tiers.
- **Cost/latency dashboards** — `EventRecorder` + exporters for per-tier
  hit-rates, cost, and p95 latency.
- **Model-aware template generation** — use the LLM during warm-up to
  automatically generate template variants from observed Q→A pairs.
- **Adaptive threshold scheduling** — time-of-day or load-based threshold
  adjustment (e.g., tighter gates during peak hours to reduce cloud cost).

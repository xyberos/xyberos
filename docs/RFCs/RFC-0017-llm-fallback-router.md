# RFC-0017 — LLM-as-Fallback & Self-Routing (Tiered Responders)

| | |
|---|---|
| **Status** | Draft |
| **Version** | 1.x (stable line) — additive seams, default-off |
| **Owner** | Core |
| **Scope** | A confidence-gated responder chain where the LLM is the last resort, plus routing, caching, model fallback, and escalation learning |

---

## Summary

RFC-0016 made the core *trainable* (capture → promote → learn → evaluate →
distill). RFC-0017 turns that into *self-routing*: a request is answered by the
**cheapest tier that is confident enough**, escalating only when necessary:

```text
Rules / policies ──▶ Knowledge ──▶ Memory ──▶ Distilled cache ──▶ Local model ──▶ Cloud LLM ──▶ Degrade
   (no model)      (facts/RAG)   (past turns)  (learned Q→A)   (if available)   (last resort)  (offline/human)
```

The **LLM becomes a fallback and a teacher**, not the primary generator: it
handles the tail and distills its answers into the cheaper tiers. Today the LLM
is called for every final response; this RFC makes that the *exception*.

All seams are additive and **off by default**, so existing behavior — and the
whole RFC-0016 work — is unchanged until a router is installed.

**Implemented so far:** `FallbackLLM` (M0 — cloud → local model cascade) ships in
`xyberos/llm/fallback.py`. Everything else is planned; see *The canonical build
sequence* below (M0 → M12) for the exact order of work across RFC-0017 + RFC-0018.

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

The goal: cheaper, faster, more resilient, and — through escalation learning —
measurably smarter over time.

---

## The tiered design (the "better way")

The desired priority — **rule/policy first, then knowledge, then memory, then a
local model if available, then the cloud LLM** — is the correct cost/latency
cascade. Six refinements make it robust:

1. **Split "gate" from "respond".** Every tier answers two questions:
   *can I handle this?* (a confidence/eligibility gate) and *what is the
   answer?*. A tier that can't respond returns `None` and the router escalates.
2. **Add a distilled cache tier** between memory and the local model. The LLM
   (or any successful responder) teaches; the cache serves identical/near
   requests without any model call.
3. **The model tier is itself a cascade** — cloud LLM first, falling back to a
   local model on `ProviderError`/timeout, then to the degraded tier.
4. **Bounded, evented escalation.** Every tier hit and every escalation is
   emitted as an event, so hit-rates are measurable and thresholds can be tuned.
5. **Graceful degradation.** When nothing is confident, a policy-controlled
   fallback applies (canned response, refusal, or human escalation) instead of a
   hang or a hard failure.
6. **Learn the gates.** Escalation thresholds are tuned from the
   `ExperienceStore` outcomes and feedback (bandit-style), not hard-coded.

### The tier table

| Tier | Responder | Cost | Model needed | Escalation when |
|---|---|---|---|---|
| 0 | **Rules / policies / workflows** | ~0 | no | no deterministic match |
| 1 | **Knowledge** (`VectorKnowledge`, facts) | ~0 | no (embedding maybe) | low retrieval score |
| 2 | **Memory** (episodic Q→A, few-shot) | ~0 | no | no good past match |
| 3 | **Distilled cache** (learned Q→A) | ~0 | no | cache miss |
| 4 | **Local model** (Ollama / distilled `Trainer` artifact) | low | yes, optional | low confidence / failure |
| 5 | **Cloud LLM** | high | yes | last resort |
| 6 | **Degrade** (offline policy / human) | ~0 | no | nothing else could |

Tiers 0–3 can be served entirely without a network model — the "LLM-less" path.

---

## Contract additions (additive, `object`-typed)

### `xyberos/contracts/responder.py` — Responder

```python
class Responder(ABC):
    """Answers a request if it can; returns None to escalate."""

    @abstractmethod
    def respond(self, context: object) -> Any | None: ...
```

A responder that returns a non-`None` value "handles" the request. Providers may
also expose an optional `confidence(context) -> float` used by the router's gate.

### `xyberos/contracts/router.py` — Router / FallbackPolicy

```python
class Router(ABC):
    """Runs responders in priority order; escalates on None or low confidence."""

    @abstractmethod
    def respond(self, context: object) -> Any: ...
```

The concrete `ResponderChain(responders, fallback=...)` iterates responders,
stops at the first confident hit, records which tier answered (for telemetry and
learning), and ends at the configured `fallback` (a `LLMResponder`, a degraded
responder, or a raise policy).

### `xyberos/llm/fallback.py` — FallbackLLM

```python
class FallbackLLM:
    """Try a primary LLM, then fall back to local/other providers on failure."""

    def __init__(self, primary, *fallbacks) -> None: ...
    def generate(self, prompt: str) -> str: ...   # duck-typed LLMProvider
```

Catches `ProviderError` (configurable via `retry_on`) on the primary and
delegates to the next model — so the "cloud LLM" tier is itself a cascade
(cloud → local → degraded).

**Status:** implemented — `xyberos/llm/fallback.py`, exported from `xyberos.llm`
as `FallbackLLM` (sync `generate`; `stream`/async variants are future work).

---

## Providers (each is a `Responder`)

- `RuleResponder(rules)` — deterministic rules/policies/workflows; the cheapest
  tier, often a `GraphWorkflow` or intent-triggered action.
- `KnowledgeResponder(knowledge, *, threshold=0.0)` — answers from
  `VectorKnowledge`/fact retrieval when the top fact clears a similarity gate.
- `MemoryResponder(memory, *, top_k=1, min_similarity=...)` — answers from the
  most similar past `Q→A` in `VectorMemory`.
- `CacheResponder(store, *, embedder=None)` — exact/near cache of learned
  `prompt → answer` pairs; `teach(prompt, answer)` records LLM answers so the
  next identical request skips the model entirely.
- `DistilledResponder(engine)` — a `Trainer`-distilled model (embedding index or
  sklearn) answering directly.
- `LLMResponder(llm)` — wraps any `LLMProvider` (including `FallbackLLM`) as the
  final answering tier.
- `DegradedResponder(policy)` — offline/canned/human-escalation fallback.

---

## Pipeline integration

The Brain gains an optional `router` slot. In `_prepare`, the router runs after
enrichment and **before** tool dispatch and the LLM:

```text
Workflow → Memory(retrieve) → Knowledge(query) → Intent → Planner
   → Router:  Rule → Knowledge → Memory → Cache → Local → Cloud   [NEW]
   → Tools (if router declined) → LLM (last resort) → Memory(store) → Experience
```

A router hit short-circuits exactly like a tool response today. When the router
is `None` (default), the Brain behaves identically to today.

### Code touch-points

| File | Change |
|---|---|
| `xyberos/contracts/responder.py` | **new** — `Responder` (+ alias) |
| `xyberos/contracts/router.py` | **new** — `Router`; `ResponderChain` in `xyberos/router/` |
| `xyberos/llm/fallback.py` | **new** — `FallbackLLM` (+ tests) |
| `xyberos/router/` | **new** package — responders + chain |
| `xyberos/brain/brain.py` | optional `router` param; run in `_prepare`; emit hit/escalation events |
| `xyberos/xyberos.py` | `create_app(..., router=...)` + `create_semantic_app(..., router=True)` opt-in |
| `xyberos/events/names.py` | `brain.responder_hit`, `brain.escalated`, `brain.degraded`, `brain.cache_hit` |

### Config knobs (all default-off)

- `brain.router` (bool) — enable the router slot
- `router.responders` (ordered names) — which tiers, in priority order
- `router.threshold` — per-tier confidence gate
- `router.degrade` — `"offline"` | `"refusal"` | `"raise"`
- `llm.fallback_chain` — ordered model names for `FallbackLLM`
- `cache.path` — persistent `SqliteVectorStore` path for `CacheResponder`

---

## Learning the escalation (closes G4)

`ExperienceStore` already records every turn's outcome and feedback. The router
adds the tier that answered to the episode. With that signal:

- **Per-tier hit-rate** = how often each tier answered and was rated ≥ 0.
- **Escalation tuning** — if a low tier answers but feedback is negative, its
  gate is raised (escalate sooner); if a high tier keeps being skipped or
  over-used, its gate is relaxed. This is the bandit-style loop the eval harness
  (`intent_accuracy`, `plan_success_rate`) already measures.

---

## Testing plan (repo conventions)

- `test_responder_contract.py` / `test_router_contract.py` — stubs, `TypeError`
  on abstract instantiation, no core coupling.
- `test_responder_provider.py` — each tier (rule/knowledge/memory/cache/local/
  cloud/degrade) returns an answer or `None`.
- `test_router.py` — priority order, escalation on `None`/low confidence,
  bounded, fallback honored, hit/escalation events emitted.
- `test_fallback_llm.py` — primary failure → local fallback → degraded.
- `test_brain_router.py` — integration: router short-circuits before LLM;
  `brain.responder_hit`/`brain.escalated`; default (no router) unchanged.
- `test_escalation_learning.py` — feedback raises/lowers a tier's gate.

---

## The canonical build sequence

The single execution plan shared with RFC-0018. **Follow M0 → M12 in order**;
RFC-0017's own milestones are **M0, M4, M8, M11, M12** (see
`RFC-0018-smarter-learning.md` for the RFC-0018 milestones M1–M3, M5–M7, M9–M10).

```text
M0  [DONE]  FallbackLLM — cloud → local cascade                      RFC-0017 · B
M1  Auto-outcome attribution — real Episode.outcome signals          RFC-0018 · E1.1
M2  Evaluation workflow + CI regression gate                          RFC-0018 · E1.2
M3  Immediate reinforcement — eager learn on positive feedback        RFC-0018 · E1.3
M4  Routing skeleton — contracts + rule/knowledge/memory responders
    + ResponderChain + Brain slot + events (INACTIVE until M8)        RFC-0017 · A
M5  Self-expanding knowledge — auto-ingest rated answers/results      RFC-0018 · E2.2
M6  Memory stratification — working facts vs episodic transcripts     RFC-0018 · E2.3
M7  Schema-driven tool calling — from FunctionTool.schema             RFC-0018 · E2.1
M8  Router completion + ACTIVATE (cache, distilled, config)           RFC-0017 · B
M9  Response reflection & grounding check                             RFC-0018 · E3.1
M10 Reranking + confidence calibration (sharpens gates)               RFC-0018 · E3.2
M11 Escalation threshold tuning (consumes M1+M2+M10)                  RFC-0017 · C
M12 DegradedResponder + per-tier hit-rate events                      RFC-0017 · C
```

**Why this order (the rules that prevent missteps):**

1. **Signals before learning** — real outcome signals (M1) before anything that
   learns from outcomes (M3, M11).
2. **Measure before you change** — the eval workflow (M2) exists before the
   routing skeleton (M4) or activation (M8), so every change is measurable.
3. **Skeleton early, activation late** — build the router (M4) early but keep it
   *inactive* so per-tier hit-rates are observable (via M2) as stores fill; only
   activate (M8) once stores are populated (M5–M6) and measured.
4. **Calibration before escalation** — confidence calibration (M10) precedes
   escalation tuning (M11), so thresholds are meaningful.

Every milestone is additive and off by default, so the suite stays green
throughout.

---

## Non-goals & Risks

**Non-goals:** no change to the `Runtime` request/response interface; no new
required runtime dependencies; no change to the frozen RFC-0016 contracts.

| Risk | Mitigation |
|---|---|
| Cheap tiers degrade quality | Confidence gates + eval harness + feedback-gated thresholds |
| Router changes default behavior | Entirely off by default; `brain.router` must be set |
| Cache returns stale answers | `CacheResponder` keyed by embedded similarity with a threshold; `teach()` only from positively-rated responses |
| Provider outage still fails | `FallbackLLM` (cloud → local) then `DegradedResponder` |
| Escalation loops / unbounded cost | Bounded chain (each tier once), `router.threshold`, and per-tier hit-rate events |

---

## Future directions

- **Teacher loop** — the cloud LLM's positively-rated answers automatically feed
  `CacheResponder.teach()` and the `Trainer` (intent + cache), shrinking the
  LLM's share of traffic over time.
- **Per-tenant routing** — different tier orders/thresholds per user/domain,
  stored in the experience layer.
- **Async/streaming tiers** — async `Router`/`FallbackLLM` variants and
  streaming from the local/cloud tiers.
- **Cost/latency dashboards** — `EventRecorder` + exporters for per-tier
  hit-rates, cost, and p95 latency.

# RFC-0018 — Smarter Learning: Outcome-Driven, Self-Measuring, Self-Expanding

| | |
|---|---|
| **Status** | Draft (revised) |
| **Version** | 2.x — incorporates the "dumbness problem" analysis & mitigation strategies |
| **Supersedes** | RFC-0018 v1.x |
| **Owner** | Core |
| **Scope** | Automatic outcome signals, a first-class evaluation workflow, self-expanding knowledge, schema-driven tool calling, memory stratification, grounding/reflection, reranking/confidence calibration, and natural-language quality mitigations for LLM-free tiers |

---

## Summary

- **RFC-0016** made the core *trainable* (capture → promote → learn → evaluate →
  distill).
- **RFC-0017** (v2) makes it *hybrid self-routing* (cheap tiers first, LLM as
  fallback, warm-up-then-detach lifecycle).
- **RFC-0018** fills the gap between them and **directly addresses the
  "dumbness" problem** — the risk that LLM-free tiers (templates, heuristics,
  rules) produce brittle intent classification, robotic responses, and dead-end
  fallbacks. This RFC makes outcomes **automatic**, makes "is it smarter?"
  **continuously measurable**, makes the knowledge stores **self-expanding**,
  and adds the capability/quality upgrades that make the hybrid stack feel
  natural even when the LLM is not the primary responder.

### The "Dumbness" Problem & How This RFC Solves It

When moving toward LLM independence, three quality risks emerge:

| Problem | Root Cause | RFC-0018 Mitigation |
|---|---|---|
| **Intent brittleness** | Heuristic-only intent fails on paraphrasing ("my stuff ain't showing up" ≠ "order status") | CascadeIntentEngine (Heuristic→Embedding→LLM) with learned thresholds via M13 |
| **Robotic responses** | Single static template per intent = identical text on repeat requests | M5 (self-expanding knowledge fuels varied responses), M7 (stratified memory injects context), M9 (schema-driven tools produce dynamic results) |
| **Dead-end fallbacks** | "I don't understand" with no path forward | M14 (DegradedResponder with actionable suggestions — rephrase, list capabilities, connect to human) |

The key insight: **quality is not binary (LLM vs. no-LLM) but graduated**.
Each milestone adds a quality layer that makes LLM-free responses more natural,
more context-aware, and more resilient to novel phrasing.

All changes are additive and **off by default**; nothing in RFC-0016 or the
stable 1.x contracts changes.

---

## The Quality Spectrum: How Each Milestone Makes the System "Smarter"

Rather than treating LLM-independence as a switch that "dumbs down" the system,
this RFC views each milestone as a **quality increment** on a continuum:

```text
  "Dumb" Robot                          Conversational                    Fully Natural
  (bare templates)                      (context-aware)                   (LLM-authored)
  │                                     │                                 │
  M5: template variants ───────────────▶ varied phrasing, less robotic
  M6: self-expanding knowledge ────────▶ factual answers from live data
  M7: stratified memory ───────────────▶ personalized context injection
  M9: schema-driven tools ─────────────▶ dynamic, data-driven responses
  M8: CascadeIntentEngine ─────────────▶ handles paraphrasing, novel phrasing
  M12: response grounding ─────────────▶ verified claims, fewer hallucinations
  M13: confidence calibration ─────────▶ knows when it doesn't know (escalates)
  M14: smart degradation ──────────────▶ actionable fallbacks, not dead ends
```

Each milestone is independently valuable — you don't need all of them to see
a quality improvement. M5 alone (template variants) eliminates robotic
repetition. M5+M7 (variants + memory) makes responses feel personalized. M5+M7+M8
(variants + memory + cascade intent) handles 80%+ of requests naturally without
an LLM.

---

## The Canonical Build Sequence

The single execution plan shared with RFC-0017. **Follow M0 → M14 in order.**

```text
M0  [DONE]   FallbackLLM — cloud → local cascade                       RFC-0017
M1  Auto-outcome attribution — real Episode.outcome signals            RFC-0018
M2  Evaluation workflow + CI regression gate                           RFC-0018
M3  Immediate reinforcement — eager learn on positive feedback         RFC-0018
M4  Routing skeleton — contracts + all responder stubs +
    ResponderChain + Brain slot + events (INACTIVE until M11)          RFC-0017
M5  TemplateResponder — multi-variant + context injection              RFC-0017
M6  Self-expanding knowledge — auto-ingest rated answers/results       RFC-0018
M7  Memory stratification — working facts vs episodic transcripts      RFC-0018
M8  CascadeIntentEngine integration — Heuristic→Embedding→LLM          RFC-0017
M9  Schema-driven tool calling — from FunctionTool.schema              RFC-0018
M10 ToolResponder — tools as formal router tier                        RFC-0017
M11 Router activation + warm-up mode (cache, distilled, config)         RFC-0017
M12 Response reflection & grounding check                              RFC-0018
M13 Reranking + confidence calibration (sharpens gates)                RFC-0018
M14 Escalation threshold tuning + auto-detach + DegradedResponder      RFC-0017
```

**Why this order (the rules that prevent missteps):**

1. **Signals before learning** — real outcome signals (M1) before anything that
   learns from outcomes (M3, M14).
2. **Measure before you change** — the eval workflow (M2) exists before the
   routing skeleton (M4) or activation (M11), so every change is measurable.
3. **Skeleton early, activation late** — build the router (M4) early but keep it
   *inactive* so per-tier hit-rates are observable (via M2) as stores fill; only
   activate (M11) once stores are populated (M6–M7) and measured.
4. **Templates before cache** — M5 before M11 so template responses populate the
   quality baseline independently of LLM teaching.
5. **Intent cascade before router activation** — M8 before M11 so the router
   has a calibrated intent signal to gate on.
6. **Calibration before escalation** — confidence calibration (M13) precedes
   escalation tuning (M14), so thresholds are meaningful.

---

## Enhancement Backlog

### Phase 1 — Signals & measurement (foundation) → **M1, M2, M3**

#### M1 · Auto-outcome attribution — *small, highest leverage* (E1.1)

**What.** Derive `Episode.outcome` automatically instead of leaving it `None`:
tool success/failure, `PlanExecutor` verification results, guardrail blocks, and
LLM/responder errors all become real outcome signals. **New in v2:** also
captures which responder tier answered (template, knowledge, cache, LLM, etc.)
for per-tier quality scoring.

**Why.** Today `promote_successful` / `demote_failed` and RFC-0017's escalation
learning only work off *manual* `app.feedback()`. Auto-outcomes make the whole
learning loop data-driven without human ratings. The per-tier signal is critical
for answering "are my LLM-free tiers actually good enough?"

**Feeds.** `ExamplePromoter`, RFC-0017 escalation learning, `Trainer` dataset
quality, per-tier quality dashboards.

#### M2 · Evaluation as a first-class workflow — *small–medium* (E1.2)

**What.** A runnable `xyberos eval` path (script/example + `test_eval`-style
regression gate in CI) over datasets using `intent_accuracy`, `recall@k`,
`plan_success_rate`, **and `tier_hit_rate` with per-tier quality scoring**,
plus a summary report.

**Why.** The metrics exist but only as a library. A repeatable eval is the
prerequisite for trusting every other enhancement — especially answering
"did making tier 0 LLM-free hurt quality?" with data, not opinion.

**Feeds.** CI gate; before/after numbers for all other RFCs; warm-up completion
decision.

#### M3 · Immediate reinforcement — *small* (E1.3)

**What.** Learn *eagerly*: on positive `app.feedback`, immediately
`intent_engine.learn(...)` / feed the cache, instead of only batched
`promote()`. **New in v2:** also feeds `TemplateResponder` — when a template
matches and gets positive feedback, boost its confidence; when negative,
lower it so the router escalates sooner next time.

**Why.** Reduces the lag between a good answer and the system improving; pairs
with E1.1 (outcome-driven) to close the loop in real time. Template confidence
tuning is the mechanism that prevents wrong template matches from recurring.

**Feeds.** `EmbeddingIntentEngine`, `CacheResponder`, `TemplateResponder`
confidence calibration.

### Phase 2 — Capability & self-expanding stores → **M6, M7, M9**

#### M6 · Self-expanding knowledge — *medium* (E2.2)

**What.** Auto-ingest high-rated LLM answers and successful tool results into
`VectorKnowledge` / `IngestingKnowledge` (the "teacher loop" as a standalone
step). **New in v2:** also ingest positively-rated template matches to build
a feedback loop where template responses improve knowledge coverage.

**Why.** The knowledge base grows from usage — which is precisely what fills the
stores RFC-0017 will route over. Without this, `KnowledgeResponder` returns
`None` for most requests. **This is the single most important milestone for
making tier 3 (Knowledge) actually useful.**

**Feeds.** `VectorKnowledge`, RFC-0017 knowledge tier + cache.

#### M7 · Working memory vs. episodic memory — *medium* (E2.3)

**What.** Use the LLM to extract durable facts (preferences, decisions) into a
facts store while keeping raw transcripts as episodic history; upgrade
`ConsolidatingMemory` from naive truncation to importance-aware extraction.
**New in v2:** extracted facts feed `TemplateResponder` context injection
(e.g., `{user.name}`, `{last_order.status}`), making template responses feel
personalized.

**Why.** The difference between "remembering text" and "knowing the user."
Context injection is what makes a template say "Your last payment of $49.99
was on Aug 1" instead of "Tell me your payment details."

**Feeds.** `VectorMemory` / `ConsolidatingMemory`, RFC-0017 memory tier,
`TemplateResponder` context injection.

#### M9 · Schema-driven tool calling — *medium, biggest capability jump* (E2.1)

**What.** Auto-generate tool calls from `FunctionTool.schema` via structured LLM
output (the RFC-Roadmap §7 item), replacing the `ToolRunner.choose()` name
heuristic (+ `intent.target`).

**Why.** Reliable, typed tool use; composes with `LLMIntentEngine` /
`StructuredLLM` machinery that already exists. When tools produce dynamic,
data-rich responses, the system feels "smart" even when the response layer is
a template — because the *data* is live and personalized.

**Feeds.** Tool tier of RFC-0017 (`ToolResponder`); agent quality.

### Phase 3 — Quality & trust → **M12, M13**

#### M12 · Response-level reflection & grounding check — *medium* (E3.1)

**What.** Extend the `ReflectivePlanner` pattern to final *responses*: self-critique
and verify claims against retrieved knowledge before committing. **New in v2:**
applies to ALL responder tiers, not just LLM — template responses are checked
against knowledge for factual consistency before being returned.

**Why.** Directly attacks hallucination and pairs with the guardrail system.
Grounding template/knowledge responses is critical because LLM-free responses
have no "self-correction" mechanism — they must be verified externally.

**Feeds.** Brain response path; security; template/knowledge quality.

#### M13 · Reranking & confidence calibration — *medium* (E3.2)

**What.** A second-stage reranker (optional dependency) for retrieval, and
calibration of raw cosine/probability into meaningful confidence. **New in v2:**
confidence calibration directly feeds the `TemplateResponder` and
`KnowledgeResponder` confidence scores, making their escalation decisions
data-driven rather than hand-tuned.

**Why.** Improves precision; calibrated confidence makes cascade/router
thresholds meaningful instead of arbitrary. **This is the milestone that
answers "should I trust this template match or escalate to the LLM?"**

**Feeds.** RFC-0017 gates directly; `TemplateResponder` confidence; warm-up
completion auto-detection.

### Future (deferred)

- **Async + thread-safety** for the new engines, stores, and responders
- **OpenTelemetry / Prometheus exporters** for hit-rates, cost, p95 latency
- **Task-aware model routing** — pick a cheap model for easy intents before the cascade
- **Cost/budget guards per tier** — escalate only within budget
- **Active learning** — surface which examples to collect next (uncertainty sampling)
- **Multi-agent verification** for high-stakes intents
- **Template variant auto-generation** — use the LLM during warm-up to generate
  natural-sounding variants for each matched pattern

---

## How It Composes (v2 — expanded)

```text
  M1  auto-outcome ──▶ promote/demote + escalation learning + per-tier scoring
  M3  immediate reinforcement ──▶ intent/cache/template learn on feedback
  M6  self-expanding knowledge ──▶ VectorKnowledge fills from usage
  M7  memory stratification ──▶ facts injected into template responses
  M9  schema-driven tool calling ──▶ dynamic, data-rich tool responses
  M12 grounding / reflection ──▶ verifies ALL tiers, not just LLM
  M13 rerank + calibration ──▶ data-driven confidence for all tiers
        │
        ▼
   RFC-0017 hybrid router:
   Template → Rules → Tools → Knowledge → Memory → Cache → Local → Cloud → Degrade
```

**Quality layering across tiers:**

```text
  Tier 0 (Template)   + M5 (variants) + M7 (context) + M13 (calibrated confidence)
                      = natural, personalized, knows when to escalate

  Tier 3 (Knowledge)  + M6 (auto-ingest) + M13 (calibrated retrieval score)
                      = growing, factual, self-improving

  Tier 4 (Memory)     + M7 (stratification) + M1 (auto-outcome tagging)
                      = knows user, recalls what worked before

  Tier 7 (Degrade)    + M14 (actionable suggestions)
                      = helpful even when everything fails
```

---

## Addressing the "Dumbness" Problem: Concrete Mitigation Patterns

### Pattern A: Intent Classification Without an LLM

```python
# BEFORE (brittle):
intent = HeuristicIntentEngine(rules=[...])  # "my stuff ain't showing up" → general

# AFTER (resilient):
intent = CascadeIntentEngine(
    HeuristicIntentEngine(rules=[...]),          # catches obvious keywords
    EmbeddingIntentEngine(store, embedder=...),  # handles paraphrasing via similarity
    LLMIntentEngine(llm=...),                    # last resort for truly novel phrasing
    confidence_threshold=0.7,                    # escalate below 0.7
)
# "my stuff ain't showing up" → embedding match → order_status (confidence 0.82)
```

### Pattern B: Natural-Feeling Template Responses

```python
# BEFORE (robotic):
template = "I understand your billing concern."  # same text every time

# AFTER (natural):
templates = TemplateResponder([
    Template(
        pattern="billing",
        variants=[
            "Got it — let me pull up your billing details.",
            "I can help with that. Let me check your account.",
            "Sure thing, looking into your billing now.",
        ],
        requires_context=("user.name", "billing.last_amount"),
        confidence=0.85,
    ),
])
# With context: "Got it, Sarah — let me pull up your billing details."
```

### Pattern C: Smart Degradation

```python
# BEFORE (dead end):
fallback = "I don't understand."

# AFTER (actionable):
fallback = DegradedResponder(policy="refusal")
# Output: "I wasn't able to find a good answer for that.
#          Could you try asking in a different way?
#          I can help with: billing, orders, account settings, technical support."
```

---

## Testing Plan (v2 — expanded)

- `test_outcome_attribution.py` — tool failure/success, plan-verification,
  guardrail results, **and per-tier attribution** set `Episode.outcome`.
- `test_eval_workflow.py` — `xyberos eval` runs datasets and reports metrics;
  regression gate fails on regression; **per-tier hit-rate and quality scoring**.
- `test_immediate_reinforcement.py` — positive feedback triggers eager `learn()`;
  **template confidence boosted on positive match, lowered on negative**.
- `test_tool_calling.py` — schema-driven call generation + argument coercion.
- `test_knowledge_ingestion.py` — auto-ingest of rated answers/tool results;
  **template match results also ingested**.
- `test_memory_stratification.py` — facts vs transcripts; consolidation extracts
  durable facts; **extracted facts feed template context injection**.
- `test_grounding.py` — response verified against retrieved knowledge;
  **applies to template and knowledge tiers, not just LLM**.
- `test_rerank_calibration.py` — reranker ordering; calibrated confidence;
  **template and knowledge confidence calibration**.

---

## Non-goals & Risks (v2 — expanded)

**Non-goals:** no change to the `Runtime` request/response interface; no new
required runtime dependencies; no change to the frozen RFC-0016 contracts; no
in-core fine-tuning (that stays the optional `Trainer` path).

| Risk | Mitigation |
|---|---|
| Auto-outcome is noisy (tool errors ≠ bad answer) | Explicit outcome taxonomy + config; outcomes feed promotion, never punish without cause |
| Eval gates block legit change | Tunable thresholds; eval is advisory in dev, enforced in CI |
| Self-expanding knowledge ingests garbage | Only high-rated answers/tool results; dedupe by embedding similarity |
| Rerank/calibration add deps | Optional extras (`xyberos[rerank]`), lazy import, default-off |
| Scope creep across three RFCs | Each phase independently shippable; RFC-0018 items are additive and default-off |
| **Template variants diverge in quality** | **Eval harness scores per-variant; low-performing variants auto-demoted** |
| **Memory context injection leaks PII** | **Configurable allowlist for injectable context keys; default-off** |
| **Degraded responder lists wrong capabilities** | **Capability list derived from registered intents/tools, not static** |

---

## Future Directions

- Fold calibrated confidence into RFC-0017's escalation learning (M13 → M14).
- Make the eval workflow emit per-tier hit-rates once RFC-0017 lands, so
  "is routing helping?" is answered by the same harness.
- Datasets-as-code: versioned eval datasets stored alongside the codebase.
- **Auto-generate template variants from LLM during warm-up** — observe which
  patterns produce consistent LLM responses, generate 3-5 natural variants.
- **A/B test tier configurations** — run two router configs side-by-side and
  compare quality/cost via the eval harness.

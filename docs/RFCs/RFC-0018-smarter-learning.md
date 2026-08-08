# RFC-0018 — Smarter Learning: Outcome-Driven, Self-Measuring, Self-Expanding

| | |
|---|---|
| **Status** | Draft |
| **Version** | 1.x (stable line) — additive, default-off |
| **Owner** | Core |
| **Scope** | Automatic outcome signals, a first-class evaluation workflow, self-expanding knowledge, schema-driven tool calling, memory stratification, grounding/reflection, and reranking/confidence calibration |

---

## Summary

- **RFC-0016** made the core *trainable* (capture → promote → learn → evaluate →
  distill).
- **RFC-0017** will make it *self-routing* (cheap tiers first, LLM as fallback).
- **RFC-0018** fills the gap between them: the learning loop currently runs on
  **manual signals**. This RFC makes outcomes **automatic**, makes "is it
  smarter?" **continuously measurable**, makes the knowledge stores
  **self-expanding**, and adds the capability/quality upgrades that benefit both
  the current LLM-first era and the future routed era.

All changes are additive and **off by default**; nothing in RFC-0016 or the
stable 1.x contracts changes.

---

## The canonical build sequence

The single execution plan shared with RFC-0017. **Follow M0 → M12 in order**;
RFC-0018's own milestones are **M1–M3, M5–M7, M9–M10** (see
`RFC-0017-llm-fallback-router.md` for the RFC-0017 milestones M0, M4, M8, M11, M12).

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

---

## Enhancement backlog

### Phase 1 — Signals & measurement (foundation) → **M1, M2, M3**

#### M1 · Auto-outcome attribution — *small, highest leverage* (E1.1)

**What.** Derive `Episode.outcome` automatically instead of leaving it `None`:
tool success/failure, `PlanExecutor` verification results, guardrail blocks, and
LLM/responder errors all become real outcome signals.

**Why.** Today `promote_successful` / `demote_failed` and (later) RFC-0017's
escalation learning only work off *manual* `app.feedback()`. Auto-outcomes make
the whole learning loop data-driven without human ratings.

**Feeds.** `ExamplePromoter`, RFC-0017 escalation learning, `Trainer` dataset
quality.

#### M2 · Evaluation as a first-class workflow — *small–medium* (E1.2)

**What.** A runnable `xyberos eval` path (script/example + `test_eval`-style
regression gate in CI) over datasets using `intent_accuracy`, `recall@k`, and
`plan_success_rate`, plus a summary report.

**Why.** The metrics exist but only as a library. A repeatable eval is the
prerequisite for trusting every other enhancement — including RFC-0017's
hit-rate targets.

**Feeds.** CI gate; before/after numbers for all other RFCs.

#### M3 · Immediate reinforcement — *small* (E1.3)

**What.** Learn *eagerly*: on positive `app.feedback`, immediately
`intent_engine.learn(...)` / feed the cache, instead of only batched
`promote()`.

**Why.** Reduces the lag between a good answer and the system improving; pairs
with E1.1 (outcome-driven) to close the loop in real time.

**Feeds.** `EmbeddingIntentEngine`, (later) `CacheResponder`.

### Phase 2 — Capability & self-expanding stores → **M5, M6, M7**

#### M5 · Self-expanding knowledge — *medium* (E2.2)

**What.** Auto-ingest high-rated LLM answers and successful tool results into
`VectorKnowledge` / `IngestingKnowledge` (the "teacher loop" as a standalone
step).

**Why.** The knowledge base grows from usage — which is precisely what fills the
stores RFC-0017 will route over. High-ROI and independently valuable.

**Feeds.** `VectorKnowledge`, RFC-0017 knowledge tier + cache.

#### M6 · Working memory vs. episodic memory — *medium* (E2.3)

**What.** Use the LLM to extract durable facts (preferences, decisions) into a
facts store while keeping raw transcripts as episodic history; upgrade
`ConsolidatingMemory` from naive truncation to importance-aware extraction.

**Why.** The difference between "remembering text" and "knowing the user."

**Feeds.** `VectorMemory` / `ConsolidatingMemory`, RFC-0017 memory tier.

#### M7 · Schema-driven tool calling — *medium, biggest capability jump* (E2.1)

**What.** Auto-generate tool calls from `FunctionTool.schema` via structured LLM
output (the RFC-Roadmap §7 item), replacing the `ToolRunner.choose()` name
heuristic (+ `intent.target`).

**Why.** Reliable, typed tool use; composes with `LLMIntentEngine` /
`StructuredLLM` machinery that already exists.

**Feeds.** Tool tier of RFC-0017; agent quality.

### Phase 3 — Quality & trust → **M9, M10**

#### M9 · Response-level reflection & grounding check — *medium* (E3.1)

**What.** Extend the `ReflectivePlanner` pattern to final *responses*: self-critique
and verify claims against retrieved knowledge before committing.

**Why.** Directly attacks hallucination and pairs with the guardrail system.

**Feeds.** Brain response path; security.

#### M10 · Reranking & confidence calibration — *medium* (E3.2)

**What.** A second-stage reranker (optional dependency) for retrieval, and
calibration of raw cosine/probability into meaningful confidence.

**Why.** Improves precision; calibrated confidence makes cascade/router
thresholds meaningful instead of arbitrary.

**Feeds.** RFC-0017 gates directly.

### Future (deferred)

- **Async + thread-safety** for the new engines, stores, and responders
- **OpenTelemetry / Prometheus exporters** for hit-rates, cost, p95 latency
- **Task-aware model routing** — pick a cheap model for easy intents before the cascade
- **Cost/budget guards per tier** — escalate only within budget
- **Active learning** — surface which examples to collect next (uncertainty sampling)
- **Multi-agent verification** for high-stakes intents

---

## How it composes

```text
  E1.1 auto-outcome ──▶ promote/demote + escalation learning
  E1.3 immediate reinforcement ──▶ intent/cache learn on feedback
  E2.2 self-expanding knowledge ──▶ VectorKnowledge fills from usage
  E2.3 memory stratification ──▶ facts vs transcripts
  E2.1 schema-driven tool calling ──▶ reliable tools
  E3.1 grounding / reflection ──▶ fewer hallucinations
  E3.2 rerank + calibration ──▶ better gates (RFC-0017)
        │
        ▼
   RFC-0017 router: Rule → Knowledge → Memory → Cache → Local → Cloud → Degrade
```

---

## Testing plan (repo conventions)

- `test_outcome_attribution.py` — tool failure/success, plan-verification, and
  guardrail results set `Episode.outcome`.
- `test_eval_workflow.py` — `xyberos eval` runs datasets and reports metrics;
  regression gate fails on regression.
- `test_immediate_reinforcement.py` — positive feedback triggers eager `learn()`.
- `test_tool_calling.py` — schema-driven call generation + argument coercion.
- `test_knowledge_ingestion.py` — auto-ingest of rated answers/tool results.
- `test_memory_stratification.py` — facts vs transcripts; consolidation extracts
  durable facts.
- `test_grounding.py` — response verified against retrieved knowledge.
- `test_rerank_calibration.py` — reranker ordering; calibrated confidence.

---

## Non-goals & Risks

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

---

## Future directions

- Fold calibrated confidence into RFC-0017's escalation learning (E3.2 → Phase C).
- Make the eval workflow emit per-tier hit-rates once RFC-0017 lands, so
  "is routing helping?" is answered by the same harness.
- Datasets-as-code: versioned eval datasets stored alongside the codebase.

# RFC-0019 — Plugin & Integration Ecosystem (Execution Plan)

| | |
|---|---|
| **Status** | Draft |
| **Version** | 1.0 |
| **Applies to** | Plugin ecosystem (integrations); core remains additive-only |
| **Companion docs** | [`INTEGRATION.md`](https://github.com/xyberos/xyberos/blob/main/INTEGRATION.md) (the roadmap / status source of truth) · [`EXTRA.md`](https://github.com/xyberos/xyberos/blob/main/EXTRA.md) (plugin SDK, generator, validator, CLI) · [`RFC-Roadmap.md`](RFC-Roadmap.md) (implementation status + community backlog) |

## 1. Purpose

Codify the Xyberos integration roadmap into an ordered, executable plan. This
RFC turns the strategic framing in `INTEGRATION.md` into milestones with
deliverables, dependencies, effort, and a Definition of Done, so contributors
and maintainers can execute rather than brainstorm.

## 2. Goals

1. Ship the two **multiplier** integrations first: an MCP client and a generic
   HTTP/API connector.
2. Make knowledge ingestion production-usable with structured loaders
   (filesystem, PDF, DOCX, HTML, CSV/XLSX).
3. Round out RAG: Qdrant, Redis (cache + state + vector), FAISS.
4. Operationalize community contribution: status taxonomy (in
   `INTEGRATION.md`), the plugin generator/validator (in `EXTRA.md`), and a CI
   validation gate.
5. Keep the **zero-dependency core** sacred; push every third-party dependency
   to an extra or a plugin.

## 3. Non-goals

- Building 100 native integrations (community plugins own the long tail).
- Changing the `Runtime` request/response interface.
- Core changes outside additive RFCs (core stays on the 1.x line).

## 4. Guiding principles

1. **Multipliers first** — MCP and HTTP/API each unlock an entire ecosystem.
2. **Contract-first** — every integration implements a stable contract
   (`LLMProvider`, `VectorStore`, `Memory`, `Knowledge`, `Tool`, `Exporter`,
   `Plugin`).
3. **Ship-location ladder** — Core (stdlib) → Extra (`xyberos[extra]`) →
   Plugin (entry point). Pick the cheapest rung that satisfies the dependency
   constraint.
4. **Status on everything** — every integration row in `INTEGRATION.md` has a
   🟢/🟡/🔵/⚪ status that changes as work lands.
5. **Observability is first-class** — exporters plug into `EventBus`/`Exporter`;
   they are thin, and front-loaded, not an afterthought.

---

## 5. Milestones

Each milestone: goal → deliverables → dependencies → effort (S/M/L) → DoD.

### M0 — Contribution operationalization *(foundation, small)*

**Goal:** a contributor can pick a 🔵 row and ship a plugin end-to-end without
asking questions.

- [x] Status-aware roadmap + Definition of Done written (`INTEGRATION.md`, this
      RFC).
- [ ] Publish a short "contribute an integration" guide (extend
      `CONTRIBUTING.md`).
- [ ] CI gate: `xyberos plugin validate` as a GitHub Action on plugin PRs
      (from `EXTRA.md` §7).
- [ ] First external plugin PR merged using the generator.

**Effort:** S · **Deps:** none · **DoD:** the guide + CI action exist and the
first generated plugin merges.

---

### M1 — Filesystem + document loaders *(high value, medium)*

**Goal:** turn plain-text-only ingestion into real document ingestion.

- [ ] `FileLoader` — walk directories, filter by extension, yield chunks.
- [ ] `PdfLoader` (lazy `pypdf`/`pymupdf` import, `ProviderError` if missing).
- [ ] `DocxLoader` (lazy `python-docx`).
- [ ] `HtmlLoader` (strip tags to text) and `CsvLoader`/`XlsxLoader`.
- [ ] All loaders return text chunks consumed by `IngestingKnowledge.ingest`.
- [ ] Update `docs/learn/21-knowledge-ingestion.md` with the loaders section.
- [ ] Example: `examples/ingest_documents.py` ingests a real PDF + DOCX.

**Effort:** M · **Deps:** M0 · **Ship:** Core (`FileLoader`, `HtmlLoader`) +
Extra (`[documents]` for PDF/DOCX/XLSX) · **DoD:** loaders tested, documented,
example runs; statuses flipped 🟡→🟢.

---

### M2 — Generic HTTP/API connector *(multiplier, medium)*

**Goal:** "point at any REST API, get typed tools."

- [ ] Declarative config: `base_url`, auth (api-key / bearer / oauth), headers,
      rate limiting (reuse `xyberos.utils.resilience.RateLimiter`).
- [ ] One `Tool` per declared operation, generated from an OpenAPI-ish spec or
      a simple YAML/JSON declaration.
- [ ] Async + streaming variants where the endpoint supports it.
- [ ] Examples: `examples/http_api_weather.py`, `examples/http_api_github.py`.

**Effort:** M · **Deps:** M0 · **Ship:** Plugin (uses only `Tool`/`FunctionTool`
public API) · **DoD:** a declared spec yields working, typed tools; two examples
run.

---

### M3 — MCP client *(multiplier, the big one, large)*

**Goal:** Xyberos → MCP → enormous ecosystem.

- [ ] `McpClient` speaking the MCP protocol: stdio transport (local servers)
      and streamable HTTP (remote servers).
- [ ] Server discovery via the MCP registry; `tools/list` → one `Tool` per
      server tool.
- [ ] Tool-call round-trip: arguments coerced through `FunctionTool` /
      `coerce_arguments`.
- [ ] Lifecycle: connect/disconnect, reconnection, timeouts
      (reuse `utils.resilience`).
- [ ] Security: no shell interpolation, subprocess isolation for stdio servers,
      allowlist of servers to connect.
- [ ] Docs + example: `examples/mcp_client.py` connects to a real server, lists
      tools, calls one.

**Effort:** L · **Deps:** M2 (pattern reuse) · **Ship:** Plugin + optional Extra
(`[mcp]`) · **DoD:** connect to ≥1 real MCP server, list and call a tool;
security review done.

---

### M4 — RAG completeness *(medium)*

**Goal:** first-class vector/state coverage for the common local + hosted
backends.

- [ ] `QdrantVectorStore` (lazy `qdrant-client`; add to `[vectors]`).
- [ ] `FaissVectorStore` (lazy `faiss-cpu`; add to `[vectors]`).
- [ ] Redis: `RedisVectorStore` + `RedisMemory` + cache backing for
      `CacheResponder` (lazy `redis`; add `[state]` extra).
- [ ] Parity smoke tests against `SqliteVectorStore` for each adapter (same
      contract, same behavior).

**Effort:** M · **Deps:** M0 · **Ship:** `[vectors]` / `[state]` · **DoD:** all
three adapters pass parity tests; statuses 🟡→🟢 (Qdrant), 🔵→🟢.

---

### M5 — Web search abstraction *(small-medium)*

**Goal:** one `WebSearch` contract, many providers behind it.

- [ ] `WebSearch` contract (`search(query, top_k) -> list[Result]`).
- [ ] Adapters: Tavily, Serper, Brave, Exa, Firecrawl (each a thin plugin).
- [ ] Browser-automation adapter optional (Playwright-backed) 🔵.
- [ ] Example: `examples/web_search.py`.

**Effort:** M · **Deps:** M2 (HTTP patterns) · **Ship:** Plugin (contract could
land in Core additively) · **DoD:** ≥2 adapters interchangeable behind the
contract.

---

### M6 — Remaining LLM providers *(small — thin configs, no new architecture)*

**Goal:** cover the long tail of providers with presets, not new code.

- [ ] OpenAI-compatible presets: Mistral, Groq, DeepSeek, Cohere, Together,
      xAI, Azure OpenAI (custom `base_url`).
- [ ] `LLMProvider` plugins for Bedrock and Vertex AI.
- [ ] Provider preset registry (e.g. `xyberos.llm.presets` dict in a plugin) so
      users configure by name.

**Effort:** S–M · **Deps:** none (contract exists) · **Ship:** Plugin /
`[llm-providers]` · **DoD:** presets documented + smoke-tested against stubs.

---

### M7 — Community wave *(ongoing, 🔵-driven)*

**Goal:** the generator, not the core team, ships the long tail.

- [ ] Publish the 🔵 backlog (Track G + Track E/F items) from `INTEGRATION.md`.
- [ ] Community plugins via generator: Slack, Discord, GitHub, GitLab, Notion,
      Gmail, Google Calendar, Jira, Linear, S3, GCS…
- [ ] Each lands through the M0 contribution pipeline.

**Effort:** ongoing · **Deps:** M0 · **Ship:** Plugins · **DoD:** 5+ community
plugins merged with 🟢 status.

---

### M8 — Voice + vision / multimodal *(medium-large)*

**Goal:** multimodal capability as plugins.

- [ ] STT: Whisper (local), Deepgram, AssemblyAI, Google/Azure Speech.
- [ ] TTS: ElevenLabs, OpenAI TTS, Piper/Coqui (local), Polly.
- [ ] Vision: OpenAI/Gemini/Claude vision; OCR (Tesseract); image gen.
- [ ] Voice transport (WebRTC/WebSocket streaming) ⚪ — deferred.
- [ ] Example: `examples/voice_assistant.py`.

**Effort:** L · **Deps:** M5 · **Ship:** Plugins · **DoD:** one local + one
cloud STT/TTS pair works; vision example runs.

---

### M9 — Enterprise + infrastructure *(large, late)*

**Goal:** serious-deployment readiness.

- [ ] Auth/identity plugins: OAuth 2.0, OIDC, JWT, SSO; Auth0/Okta/Entra.
- [ ] Enterprise storage/DB plugins: SharePoint, OneDrive, S3, Azure Blob, GCS;
      MSSQL, Oracle, SAP, Snowflake, Databricks.
- [ ] **Database Plugin Contract** RFC (connect → inspect schema → query →
      transform → structured result) as a Core additive RFC.
- [ ] Infra: Docker/Kubernetes, queues (Kafka/NATS/RabbitMQ/Redis Streams),
      serverless platforms.

**Effort:** L · **Deps:** M4, M7 · **Ship:** Plugins + one Core RFC · **DoD:**
enterprise reference deployment documented; DB contract RFC approved.

---

### M10 — Observability exporters *(threaded from the start)*

**Goal:** production observability with the events interface as the hub.

- [ ] `OpenTelemetryExporter`, `PrometheusExporter`, `Grafana`/`Jaeger` wiring.
- [ ] `LangfuseExporter`, `SentryExporter`, Arize Phoenix, W&B.
- [ ] End-to-end trace of one request through the pipeline into a backend.

**Effort:** M · **Deps:** none (uses `Exporter`) · **Ship:** Extra / Plugin ·
**DoD:** a trace lands in OTel or Langfuse from `app.chat(...)`.

---

## 6. Cross-cutting Definition of Done

For **every** integration (shared with `INTEGRATION.md` §5):

1. Implements its contract; no core changes outside additive RFCs.
2. Optional deps lazily imported with a clear `ProviderError`.
3. Contract tests + integration smoke test; optional-dep tests skip cleanly.
4. Example under `examples/`.
5. Docs page + status updated in `INTEGRATION.md`.
6. `xyberos plugin validate` passes (plugins).
7. Async/streaming variants where the contract supports them.

## 7. Testing strategy

- Reuse the existing provider test patterns (`test/test_sentence_embedder.py`
  is the model for optional-dep tests that skip when the dependency is absent).
- Parity tests: every `VectorStore`/`Memory`/`Knowledge` adapter must pass the
  same contract tests as the stdlib implementations (`SqliteVectorStore`,
  `SqliteMemory`, `SqliteKnowledge`).
- Live-kernel validation: plugins validated in a subprocess harness
  (`xyberos plugin validate`, from `EXTRA.md`).

## 8. Success metrics

- Number of 🟢 integrations in `INTEGRATION.md` over time.
- Number of community PRs merged via the generator.
- Time-to-first-plugin for a new contributor (**target: < 15 minutes**).
- Full test suite stays green (currently 536 passed / 3 skipped).

## 9. Open questions

- **Qdrant/FAISS ship location:** extend `[vectors]` vs. a new `[vector-dbs]`
  extra? (Lean: extend `[vectors]`.)
- **Redis scope:** vector store + memory + cache in one `[state]` extra, or
  separate extras?
- **MCP transports:** ship stdio + streamable HTTP in the first cut, or stdio
  only (remote servers need a security review)?
- **DB contract:** one Core RFC for all databases, or per-family contracts
  (SQL vs. document vs. graph)?
- **Provider presets:** ship as a Core registry (`xyberos.llm.presets`) or as a
  plugin?

---

## 10. Change history

| Rev | Date | Change |
| --- | ---- | ------ |
| 1.0 | 2026-08-15 | Initial draft — derived from `INTEGRATION.md` rewrite. |

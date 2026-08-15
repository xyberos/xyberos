# RFC-0019 — Plugin & Integration Roadmap

> The canonical integration roadmap for Xyberos: **what is available, what is
> planned, where each integration ships, and what "done" means** — plus the
> ordered execution plan (milestones M0–M10). This document merged the former
> `INTEGRATION.md` status tracker into a single source of truth.

| | |
|---|---|
| **Status** | Active |
| **Version** | 2.1 |
| **Applies to** | Plugin ecosystem (integrations); core remains additive-only |
| **Companion docs** | [`integrations.md`](../integrations.md) (available integrations + usage) · [`plugin-contribution.md`](../plugin-contribution.md) (plugin SDK, generator, validator, CLI) · [`RFC-Roadmap.md`](RFC-Roadmap.md) (platform implementation status + community backlog) |

## Status legend

| Status | Meaning |
| ------ | ------- |
| 🟢 **Available** | Shipped in core or an official extra. Do not rebuild. |
| 🟡 **In Development** | Actively being built — next in line. |
| 🔵 **Community Wanted** | Fully specified, generator-ready, looking for a contributor. |
| ⚪ **Planned** | Idea only, not yet specified. |

## Ship location legend

| Ship | Meaning |
| ---- | ------- |
| **Core** | Stdlib-only adapter in `xyberos/` (zero runtime deps). |
| **Extra** | Optional dependency, lazily imported — `pip install xyberos[extra]`. |
| **Plugin** | External package that registers an `xyberos.plugins` entry point. |

---

## 1. Purpose

Codify the Xyberos integration roadmap into a single, executable document:
the status tracker (what's available and planned, with a contract and ship
location for every integration) plus the ordered plan (milestones with
deliverables, dependencies, effort, and a Definition of Done) — so contributors
and maintainers can execute rather than brainstorm.

## 2. Goals

1. Ship the two **multiplier** integrations first: an MCP client and a generic
   HTTP/API connector.
2. Make knowledge ingestion production-usable with structured loaders
   (filesystem, PDF, DOCX, HTML, CSV/XLSX).
3. Round out RAG: Qdrant, Redis (cache + state + vector), FAISS.
4. Operationalize community contribution: the status taxonomy (below), the
   plugin generator/validator (in [`plugin-contribution.md`](../plugin-contribution.md)),
   and a CI validation gate.
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
4. **Status on everything** — every integration row below has a 🟢/🟡/🔵/⚪
   status that changes as work lands.
5. **Observability is first-class** — exporters plug into `EventBus`/`Exporter`;
   they are thin, and front-loaded, not an afterthought.

## 5. The strategy

1. **Multipliers before individual integrations.** A generic MCP client and a
   generic HTTP/API connector each unlock an *entire ecosystem* (every MCP
   server, every REST API) for the cost of one integration. They are the
   foundation of the roadmap.
2. **Native integrations only where Xyberos adds real value.** Everything else
   ships as community plugins through the generator described in
   [`plugin-contribution.md`](../plugin-contribution.md)
   (`xyberos plugin create` → `validate`).
3. **Every integration implements a stable contract** — see §4.
4. **Zero-dependency core stays sacred.** Anything needing a third-party SDK
   goes in an extra or a plugin with a lazy import and a clear `ProviderError`.
5. **Status on everything.** Every row below carries a status so contributors
   can pick work without asking.

---

## 6. Already shipped — do not rebuild

This is the ground truth for the current `v1.0.x` core. Anything listed here is
already available; treat it as done.

| Category | Integration | Implementation | Contract | Ship |
| -------- | ----------- | -------------- | -------- | ---- |
| LLM / AI | OpenAI | `OpenAILLM` | `LLMProvider` | Core (lazy SDK) |
| LLM / AI | Anthropic | `AnthropicLLM` | `LLMProvider` | Core (lazy SDK) |
| LLM / AI | Google Gemini | `GeminiLLM` | `LLMProvider` | Core (lazy SDK) |
| LLM / AI | Ollama — chat **and** embeddings | `OllamaLLM`, `OllamaEmbeddingLLM` | `LLMProvider` + embedder | Core (stdlib HTTP) |
| LLM / AI | OpenAI-compatible endpoints | `OpenAICompatibleLLM`, `OpenAIEmbeddingLLM` | `LLMProvider` + embedder | Core (stdlib HTTP) |
| LLM / AI | Local embeddings | `HashEmbedder`, `SentenceTransformerEmbedder` | embedder | Core / `[embeddings]` |
| LLM / AI | Structured outputs, fallback, streaming/async | `StructuredLLM`, `FallbackLLM`, `StreamingLLM`, `AsyncLLM` | `LLMProvider` | Core |
| Vector | SQLite (persistent, stdlib) | `SqliteVectorStore` | `VectorStore` | Core |
| Vector | Chroma | `ChromaVectorStore` | `VectorStore` | `[vectors]` |
| Vector | PostgreSQL / pgvector | `PgVectorStore` | `VectorStore` | `[vectors]` |
| Vector | Reranking | `ScoreReranker`, `LexicalReranker` | `Reranker` | Core / `[rerank]` |
| Memory | In-memory, SQLite, vector, consolidating, stratified | `InMemoryMemory`, `SqliteMemory`, `VectorMemory`, `ConsolidatingMemory`, `StratifiedMemory` | `Memory` | Core |
| Knowledge | Dict, SQLite, vector, chunked ingestion | `InMemoryKnowledge`, `SqliteKnowledge`, `VectorKnowledge`, `IngestingKnowledge` | `Knowledge` | Core |
| Plugins | Plugin contract + loader (entry points + package scan) | `Plugin`, `PluginLoader` | `Plugin` | Core (RFC-0013) |
| Observability | Event bus + exporter surface | `EventBus`, `EventRecorder`, `LoggingExporter`, `Exporter` | `EventBus` | Core |

> **Note:** plain-text ingestion (Markdown / TXT / JSON read as text) already
> works through `IngestingKnowledge` — see
> [`learn/21-knowledge-ingestion.md`](../learn/21-knowledge-ingestion.md).
> Structured loaders for PDF, DOCX, HTML, CSV/XLSX and directory walking now
> ship as the `xyberos-documents` plugin (M1); web fetches are still
> DIY (Track A 🔵).

---

## 7. The delivery model

For any new integration, pick **one** of these three, in order of preference:

1. **Core adapter** — only if it can be stdlib-only
   (e.g. `SqliteVectorStore`, `OllamaLLM`). No new runtime dependency.
2. **Official extra** — a small, curated set of third-party deps exposed as
   `pip install xyberos[extra]` (existing: `[vectors]`, `[embeddings]`,
   `[rerank]`, `[train]`, `[documents]`, `[state]`, `[mcp]`). Lazy import +
   `ProviderError` when missing.
3. **Community plugin** — everything else. Generated by `xyberos plugin create`,
   validated by `xyberos plugin validate`, distributed via the `xyberos.plugins`
   entry-point group (see [`plugin-contribution.md`](../plugin-contribution.md)).

---

## 8. The roadmap by track

### Track A — Foundation & multipliers *(do first)*

| Integration | Status | Contract | Ship | Notes |
| ----------- | ------ | -------- | ---- | ----- |
| MCP client | � | `Plugin` + `Tool` | Plugin (`xyberos-mcp`) | stdio + streamable HTTP; one `Tool` per server tool (M3) |
| Generic HTTP/API connector | 🟢 | `Tool` | Plugin (`xyberos-http-api`) | Declarative `base_url`/auth/operations → one `Tool` per operation (M2) |
| Filesystem loader | 🟢 | `Knowledge` | Plugin (`xyberos-documents`) | `ingest_document` / `ingest_directory` → `IngestingKnowledge` (M1) |
| Document loaders (PDF, DOCX, HTML, CSV/XLSX) | 🟢 | `Knowledge` | Extra / Plugin (`xyberos-documents`) | `PdfLoader`/`DocxLoader`/`HtmlLoader`/`CsvLoader`/`XlsxLoader` (M1) |
| Web loader (fetch + strip HTML) | 🔵 | `Knowledge` | Plugin | Tutorial already fetches plain text; formalize it |
| Web search abstraction | 🟢 | `Tool` | Plugin (`xyberos-web-search`) | `web_search` tool; Tavily/Serper/Brave/Exa/Firecrawl behind one contract (M5) |
| Browser automation | 🔵 | `Tool` | Plugin | Playwright-backed, headless mode |
| Markdown / TXT / JSON loaders | 🟢 | `Knowledge` | Core | Already works via `IngestingKnowledge` + `Path.read_text` |

### Track B — LLM & AI providers

OpenAI, Anthropic, Gemini, Ollama and OpenAI-compatible are **already shipped**
(§6 table). Remaining providers:

| Integration | Status | Contract | Ship | Notes |
| ----------- | ------ | -------- | ---- | ----- |
| Mistral / Groq / DeepSeek / Cohere / Together / xAI | 🔵 | `LLMProvider` | Plugin | Most are OpenAI-compatible → thin config, **no new adapter** |
| Hugging Face | 🔵 | `LLMProvider` | Plugin | |
| Azure OpenAI | 🔵 | `LLMProvider` | Plugin | OpenAI-compatible with a custom `base_url` |
| AWS Bedrock | 🔵 | `LLMProvider` | Plugin | |
| Google Vertex AI | 🔵 | `LLMProvider` | Plugin | |

> **Rule:** never create a different architecture per LLM. One `LLMProvider`
> contract; providers are implementations of it. The provider contract is the
> ecosystem's shared spine.

### Track C — Knowledge / RAG (vector stores)

SQLite, Chroma and pgvector are **shipped**. Remaining:

| Integration | Status | Contract | Ship | Notes |
| ----------- | ------ | -------- | ---- | ----- |
| Qdrant | � | `VectorStore` | Plugin (`xyberos-qdrant`) + `[vectors]` | Hosted or local in-memory mode; parity tests pass (M4) |
| FAISS | 🟢 | `VectorStore` | Plugin (`xyberos-faiss`) + `[vectors]` | Local, no server; parity tests pass (M4) |
| Pinecone / Weaviate / Milvus | 🔵 | `VectorStore` | Plugin | Hosted/larger-scale |
| Elasticsearch / OpenSearch | 🔵 | `VectorStore` | Plugin | Also serve Track D |

### Track D — Databases & state

SQLite (core) and PostgreSQL via pgvector (`[vectors]`) are **shipped**.

| Integration | Status | Contract | Ship | Notes |
| ----------- | ------ | -------- | ---- | ----- |
| Redis — cache + state + vector | � | `Memory` / `VectorStore` / `Service` | Plugin (`xyberos-redis`) + `[state]` | `RedisVectorStore`/`RedisMemory`/`RedisStringCache`; backs `CacheResponder` (M4) |
| MySQL / MariaDB / MongoDB / DuckDB | 🔵 | `Knowledge` / `Memory` | Plugin | |
| MSSQL / Oracle | 🔵 | `Knowledge` | Plugin | Enterprise |
| Snowflake / Databricks | 🔵 | `Knowledge` | Plugin | Analytics |
| **Database Plugin Contract** | 🟡 | new contract | Core (RFC) | `connect → inspect schema → query → transform → structured result`, DB-agnostic |

### Track E — Document & knowledge sources

| Integration | Status | Contract | Ship | Notes |
| ----------- | ------ | -------- | ---- | ----- |
| Cloud storage: S3, GCS, Azure Blob | 🔵 | `Knowledge` / `Tool` | Plugin | |
| Cloud drive: Google Drive, OneDrive, Dropbox | 🔵 | `Knowledge` / `Tool` | Plugin | |
| Knowledge platforms: Notion, Confluence, SharePoint | 🔵 | `Knowledge` / `Tool` | Plugin | |

### Track F — Web / search

| Integration | Status | Contract | Ship | Notes |
| ----------- | ------ | -------- | ---- | ----- |
| Tavily, Serper, Brave, Exa, Firecrawl | 🟢 | `Tool` | Plugin (`xyberos-web-search`) | `web_search` tool, one `WebSearch` contract (M5) |
| Bing, Google | 🔵 | `Tool` | Plugin | Implement the Track A web-search abstraction |

### Track G — Productivity / business *(community wave)*

| Integration | Status | Contract | Ship | Notes |
| ----------- | ------ | -------- | ---- | ----- |
| Communication: Slack, Discord, Teams, Telegram, WhatsApp | 🔵 | `Tool` / `Agent` | Plugin | |
| Project mgmt: Jira, Linear, Trello, Asana, GitHub, GitLab | 🔵 | `Tool` | Plugin | |
| CRM / support: Salesforce, HubSpot, Zendesk, Intercom | 🔵 | `Tool` | Plugin | |
| Email: Gmail, Outlook, IMAP/SMTP | 🔵 | `Tool` | Plugin | |
| Calendar: Google, Microsoft | 🔵 | `Tool` | Plugin | |

### Track H — Voice

| Integration | Status | Contract | Ship | Notes |
| ----------- | ------ | -------- | ---- | ----- |
| STT: Whisper, Deepgram, AssemblyAI, Google/Azure Speech | 🔵 | `Tool` / `Service` | Plugin | |
| TTS: ElevenLabs, OpenAI TTS, Google/Azure, Polly, Piper, Coqui | 🔵 | `Tool` / `Service` | Plugin | Piper/Coqui = local |
| Transport: WebRTC, WebSocket, streaming audio | ⚪ | `Service` | Plugin | |

### Track I — Vision / multimodal

| Integration | Status | Contract | Ship | Notes |
| ----------- | ------ | -------- | ---- | ----- |
| Vision: OpenAI / Gemini / Claude vision | 🔵 | `LLMProvider` / `Tool` | Plugin | |
| OCR: Tesseract, document vision | 🔵 | `Tool` / `Knowledge` | Plugin | |
| Image generation / understanding | 🔵 | `Tool` | Plugin | |
| Multimodal knowledge documents | ⚪ | `Knowledge` | Core | Depends on knowledge system support |

### Track J — Enterprise

| Integration | Status | Contract | Ship | Notes |
| ----------- | ------ | -------- | ---- | ----- |
| Auth: OAuth 2.0, OIDC, JWT, SSO, API keys | 🔵 | `Security` / `Plugin` | Plugin | |
| Identity: Auth0, Okta, Microsoft Entra, Google | 🔵 | `Plugin` | Plugin | |
| Storage: SharePoint, OneDrive, S3, Azure Blob, GCS | 🔵 | `Knowledge` / `Tool` | Plugin | |
| DBs: MSSQL, Oracle, SAP, Snowflake, Databricks | 🔵 | `Knowledge` | Plugin | |

### Track K — Infrastructure

| Integration | Status | Contract | Ship | Notes |
| ----------- | ------ | -------- | ---- | ----- |
| Docker, Kubernetes | ⚪ | `Plugin` | Plugin | Deployment-time |
| Queues: Celery, RabbitMQ, Kafka, NATS, Redis Streams, Postgres queues | ⚪ | `Service` / `Plugin` | Plugin | Async workload glue |
| Serverless: AWS, Azure, GCP | ⚪ | `Plugin` | Plugin | |

### Track L — Observability

> The platform already exposes a first-class events interface
> (`EventBus` + `Exporter`). These adapters are **thin exporters** that plug
> into it — the observability hub stays inside Xyberos.

| Integration | Status | Contract | Ship | Notes |
| ----------- | ------ | -------- | ---- | ----- |
| OpenTelemetry, Prometheus, Grafana, Jaeger | 🔵 | `Exporter` | Extra / Plugin | |
| LLM observability: Langfuse, Arize Phoenix, W&B | 🔵 | `Exporter` | Plugin | |
| Errors: Sentry | 🔵 | `Exporter` | Plugin | |

```text
Xyberos Application
       │
       ├── LLM call · Tool call · Plugin · Memory · Retrieval · Workflow
       │
       ↓
   Xyberos Events
       │
  ┌────┼─────────┐
  ↓    ↓         ↓
Console OTel   Langfuse
```

---

## 9. Status taxonomy — decision rule

- 🟢 = merged, tested, documented, and its status row in this file is updated.
- 🟡 = actively being built (someone is assigned).
- 🔵 = fully specified and generator-ready — waiting for a contributor.
- ⚪ = idea only, not yet specified.

The 🔵 list is the *call to action*: a contributor picks a row, runs the
generator, and ships.

---

## 10. Milestones

Each milestone: goal → deliverables → dependencies → effort (S/M/L) → DoD.

### M0 — Contribution operationalization *(foundation, small)*

**Goal:** a contributor can pick a 🔵 row and ship a plugin end-to-end without
asking questions.

- [x] Status-aware roadmap + Definition of Done written (this document).
- [x] Publish a short "contribute an integration" guide — the
      [Contributing Guide](../contributing.md) plugin callout and
      [Learn 24 — Build & Contribute Plugins](../learn/24-plugin-development.md).
- [x] CI gate: `xyberos plugin validate` as a GitHub Action on plugin PRs
      (`.github/workflows/plugin-validation.yml` + the `xyberos-plugin-validator`
      composite action; validates `examples/texttools`).
- [x] Publish the plugin tooling to PyPI — `xyberos-cli`, `xyberos-plugin-sdk`,
      `xyberos-plugin-validator` (`pip install xyberos-cli` pulls in SDK +
      validator). Registered 2026-08-15.
- [ ] First external plugin PR merged using the generator.

**Effort:** S · **Deps:** none · **DoD:** the guide + CI action exist and the
first generated plugin merges.

---

### M1 — Filesystem + document loaders *(high value, medium)*

**Goal:** turn plain-text-only ingestion into real document ingestion.

- [x] `FileLoader` — walk directories, filter by extension, yield chunks.
- [x] `PdfLoader` (lazy `pypdf`/`pymupdf` import, `ProviderError` if missing).
- [x] `DocxLoader` (lazy `python-docx`).
- [x] `HtmlLoader` (strip tags to text) and `CsvLoader`/`XlsxLoader`.
- [x] All loaders return text chunks consumed by `IngestingKnowledge.ingest`.
- [x] Update `docs/learn/21-knowledge-ingestion.md` with the loaders section.
- [x] Example: `examples/ingest_documents.py` ingests a real PDF + DOCX.

**Effort:** M · **Deps:** M0 · **Ship:** Core (`FileLoader`, `HtmlLoader`) +
Extra (`[documents]` for PDF/DOCX/XLSX) · **Shipped:** `xyberos/xyberos-plugins`
(`documents/` plugin, `xyberos-documents`) · **DoD:** loaders tested, documented,
example runs; statuses flipped 🟡→🟢.

---

### M2 — Generic HTTP/API connector *(multiplier, medium)*

**Goal:** "point at any REST API, get typed tools."

- [x] Declarative config: `base_url`, auth (api-key / bearer / oauth), headers,
      rate limiting (reuse `xyberos.utils.resilience.RateLimiter`).
- [x] One `Tool` per declared operation, generated from an OpenAPI-ish spec or
      a simple YAML/JSON declaration.
- [ ] Async + streaming variants where the endpoint supports it.
- [x] Examples: `examples/http_api_weather.py`, `examples/http_api_github.py`.

**Effort:** M · **Deps:** M0 · **Ship:** Plugin (uses only `Tool`/`FunctionTool`
public API) · **Shipped:** `xyberos/xyberos-plugins` (`http-api/` plugin,
`xyberos-http-api`) · **DoD:** a declared spec yields working, typed tools; two
examples run.

---

### M3 — MCP client *(multiplier, the big one, large)*

**Goal:** Xyberos → MCP → enormous ecosystem.

- [x] `McpClient` speaking the MCP protocol: stdio transport (local servers)
      and streamable HTTP (remote servers).
- [x] Server discovery via the MCP registry; `tools/list` → one `Tool` per
      server tool.
- [x] Tool-call round-trip: arguments coerced through `FunctionTool` /
      `coerce_arguments`.
- [x] Lifecycle: connect/disconnect, reconnection, timeouts
      (reuse `utils.resilience`).
- [x] Security: no shell interpolation, subprocess isolation for stdio servers,
      allowlist of servers to connect.
- [x] Docs + example: `examples/mcp_client.py` connects to a real server, lists
      tools, calls one.

**Effort:** L · **Deps:** M2 (pattern reuse) · **Ship:** Plugin + optional Extra
(`[mcp]`) · **Shipped:** `xyberos/xyberos-plugins` (`mcp/` plugin,
`xyberos-mcp`) · **DoD:** connect to ≥1 real MCP server, list and call a tool;
security review done.

---

### M4 — RAG completeness *(medium)*

**Goal:** first-class vector/state coverage for the common local + hosted
backends.

- [x] `QdrantVectorStore` (lazy `qdrant-client`; add to `[vectors]`).
- [x] `FaissVectorStore` (lazy `faiss-cpu`; add to `[vectors]`).
- [x] Redis: `RedisVectorStore` + `RedisMemory` + cache backing for
      `CacheResponder` (lazy `redis`; add `[state]` extra).
- [x] Parity smoke tests against `SqliteVectorStore` for each adapter (same
      contract, same behavior).

**Effort:** M · **Deps:** M0 · **Ship:** `[vectors]` / `[state]` · **Shipped:**
`xyberos/xyberos-plugins` (`vector-qdrant/`, `vector-faiss/`, `vector-redis/`
plugins) · **DoD:** all three adapters pass parity tests; statuses 🟡→🟢
(Qdrant), 🔵→🟢.

---

### M5 — Web search abstraction *(small-medium)*

**Goal:** one `WebSearch` contract, many providers behind it.

- [x] `WebSearch` contract (`search(query, top_k) -> list[Result]`).
- [x] Adapters: Tavily, Serper, Brave, Exa, Firecrawl (each a thin plugin).
- [ ] Browser-automation adapter optional (Playwright-backed) 🔵.
- [x] Example: `examples/web_search.py`.

**Effort:** M · **Deps:** M2 (HTTP patterns) · **Ship:** Plugin (contract could
land in Core additively) · **Shipped:** `xyberos/xyberos-plugins`
(`web-search/` plugin, `xyberos-web-search`) · **DoD:** ≥2 adapters
interchangeable behind the contract.

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

- [ ] Publish the 🔵 backlog (Track G + Track E/F items) from §8.
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

## 11. Phased build order

| Phase | Focus | Tracks |
| ----- | ----- | ------ |
| 1 | Foundation & multipliers — MCP, HTTP/API, filesystem + document loaders | A |
| 2 | RAG completeness — Qdrant, Redis, FAISS + web search abstraction | C, D, F |
| 3 | Remaining LLM providers (thin configs, no new architecture) | B |
| 4 | Community wave — comm / PM / CRM / email / calendar via the generator | G |
| 5 | Voice + vision / multimodal | H, I |
| 6 | Enterprise + infrastructure | J, K |
| 7 | Observability exporters (threaded through every phase, front-loaded) | L |

> **Status (2026-08-15):** Phases 1–2 are **complete** — M1–M5 shipped in
> `xyberos/xyberos-plugins`. Phase 3 (M6) is the next in-line core-team work.

---

## 12. Cross-cutting Definition of Done

For **every** integration:

1. Implements its contract; no core changes outside additive RFCs.
2. Optional deps lazily imported with a clear `ProviderError`.
3. Contract tests + integration smoke test; optional-dep tests skip cleanly.
4. Example under `examples/`.
5. Docs page + status updated in this document.
6. `xyberos plugin validate` passes (plugins).
7. Async/streaming variants where the contract supports them.

## 13. Testing strategy

- Reuse the existing provider test patterns (`test/test_sentence_embedder.py`
  is the model for optional-dep tests that skip when the dependency is absent).
- Parity tests: every `VectorStore`/`Memory`/`Knowledge` adapter must pass the
  same contract tests as the stdlib implementations (`SqliteVectorStore`,
  `SqliteMemory`, `SqliteKnowledge`).
- Live-kernel validation: plugins validated in a subprocess harness
  (`xyberos plugin validate`, from `plugin-contribution.md`).

## 14. Success metrics

- Number of 🟢 integrations in this roadmap over time.
- Number of community PRs merged via the generator.
- Time-to-first-plugin for a new contributor (**target: < 15 minutes**).
- Full test suite: 533 passed / 3 skipped (optional deps) — the 3 remaining
  failures are pre-existing async-security tests requiring `pytest-asyncio`.

## 15. Open questions

- ~~**Qdrant/FAISS ship location:** extend `[vectors]` vs. a new `[vector-dbs]`
  extra?~~ **Resolved (M4):** extended `[vectors]`.
- ~~**Redis scope:** vector store + memory + cache in one `[state]` extra, or
  separate extras?~~ **Resolved (M4):** one `[state]` extra.
- ~~**MCP transports:** ship stdio + streamable HTTP in the first cut, or stdio
  only (remote servers need a security review)?~~ **Resolved (M3):** stdio +
  streamable HTTP, with an allowlist security review.
- **DB contract:** one Core RFC for all databases, or per-family contracts
  (SQL vs. document vs. graph)?
- **Provider presets:** ship as a Core registry (`xyberos.llm.presets`) or as a
  plugin?

---

## 16. Strategic framing (why this shape)

The goal is **not to collect every integration** — it is to make Xyberos capable
of *attracting* capabilities from wherever they already exist:

```text
Xyberos → MCP       → enormous ecosystem
Xyberos → HTTP/API  → virtually any API
```

while native Xyberos plugins focus on the integrations where the platform can
provide a substantially better experience. That turns the "AI ecosystem magnet"
idea into an architectural strategy. 🧲

---

## 17. References

1. [Model Context Protocol — Blog](https://modelcontextprotocol.io/blog) — protocol evolution, remote servers, extensions.
2. [MCP Servers (official registry/reference)](https://github.com/modelcontextprotocol/servers) — discoverable server catalog.

---

## 18. Change history

| Rev | Date | Change |
| --- | ---- | ------ |
| 2.3 | 2026-08-15 | M1–M5 shipped in `xyberos/xyberos-plugins` (documents, http-api, mcp, vector-qdrant/faiss/redis, web-search); Track A/C/D/F + milestone statuses flipped to 🟢; `[documents]`/`[state]`/`[mcp]` extras added; open questions resolved. |
| 2.2 | 2026-08-15 | M0 tooling published to PyPI (`xyberos-cli`, `xyberos-plugin-sdk`, `xyberos-plugin-validator`); noted `[documents]` extra for M1. |
| 2.1 | 2026-08-15 | M0 status updated (contribution guide + CI gate implemented); corrected test counts. |
| 2.0 | 2026-08-15 | Merged the `INTEGRATION.md` status tracker into this roadmap (single source of truth). |
| 1.0 | 2026-08-15 | Initial draft — execution plan (milestones M0–M10). |


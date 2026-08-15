# Integrations & Ecosystem

Xyberos is **open to integrations** — every subsystem is an extension point. A
provider, store, tool, or plugin implements a stable contract and ships through
one of three channels:

| Channel | Meaning | Install |
| --- | --- | --- |
| 🟢 **Core** | Ships inside `xyberos` (stdlib only, zero runtime deps) | `pip install xyberos` |
| 🟡 **Extra** | Optional third-party adapter, lazily imported | `pip install xyberos[extra]` |
| 🔵 **Plugin** | External package via the `xyberos.plugins` entry point | `pip install <plugin>` |

This page lists what is **available today**. For the full picture — what's in
development, what's wanted from the community, and what's planned — see the
[Integration Roadmap](RFCs/RFC-0019-integrations-roadmap.md) (status + plan).

---

## LLM providers

| Provider | Implementation | Contract | Ship |
| --- | --- | --- | --- |
| OpenAI | `OpenAILLM` | `LLMProvider` | Core (lazy SDK) |
| Anthropic | `AnthropicLLM` | `LLMProvider` | Core (lazy SDK) |
| Google Gemini | `GeminiLLM` | `LLMProvider` | Core (lazy SDK) |
| Ollama — chat **and** embeddings | `OllamaLLM`, `OllamaEmbeddingLLM` | `LLMProvider` | Core (stdlib HTTP) |
| OpenAI-compatible endpoints | `OpenAICompatibleLLM`, `OpenAIEmbeddingLLM` | `LLMProvider` | Core (stdlib HTTP) |
| Local embeddings | `HashEmbedder`, `SentenceTransformerEmbedder` | embedder | Core / `[embeddings]` |
| Structured / fallback / streaming / async | `StructuredLLM`, `FallbackLLM`, `StreamingLLM`, `AsyncLLM` | `LLMProvider` | Core |

```python
from xyberos import create_app
from xyberos.llm import OpenAILLM, AnthropicLLM, GeminiLLM, OllamaLLM

app = create_app(llm=OpenAILLM(api_key="..."))            # cloud
app = create_app(llm=OllamaLLM(model="qwen2.5:1.5b"))     # fully local, no SDK
```

> **Learn more:** [Learn 2 — Getting Started](learn/02-getting-started.md) ·
> [How-To: Change the LLM](howto.md#change-the-llm)

---

## Vector stores

| Store | Implementation | Contract | Ship |
| --- | --- | --- | --- |
| In-memory | `CosineVectorStore` | `VectorStore` | Core |
| SQLite (persistent, stdlib) | `SqliteVectorStore` | `VectorStore` | Core |
| Chroma | `ChromaVectorStore` | `VectorStore` | `[vectors]` |
| PostgreSQL / pgvector | `PgVectorStore` | `VectorStore` | `[vectors]` |
| Qdrant (hosted or local) | `QdrantVectorStore` | `VectorStore` | Plugin `xyberos-qdrant` + `[vectors]` |
| FAISS (local, no server) | `FaissVectorStore` | `VectorStore` | Plugin `xyberos-faiss` + `[vectors]` |
| Redis (vector + memory + cache) | `RedisVectorStore`, `RedisMemory`, `RedisStringCache` | `VectorStore` / `Memory` | Plugin `xyberos-redis` + `[state]` |
| Reranking | `ScoreReranker`, `LexicalReranker` | `Reranker` | Core / `[rerank]` |

> **Learn more:** [Learn 5 — Give It Knowledge](learn/05-knowledge.md) ·
> [How-To: Replace the vector database](howto.md#replace-the-vector-database)

---

## Memory

| Provider | Implementation | Contract | Ship |
| --- | --- | --- | --- |
| In-memory | `InMemoryMemory` | `Memory` | Core |
| SQLite (durable) | `SqliteMemory` | `Memory` | Core |
| Vector (semantic) | `VectorMemory` | `Memory` | Core |
| Consolidating | `ConsolidatingMemory` | `Memory` | Core |
| Stratified (facts extraction) | `StratifiedMemory` | `Memory` | Core |

> **Learn more:** [Learn 6 — Give It Memory](learn/06-memory.md) ·
> [How-To: Add memory](howto.md#add-memory)

---

## Knowledge

| Provider | Implementation | Contract | Ship |
| --- | --- | --- | --- |
| In-memory | `InMemoryKnowledge` | `Knowledge` | Core |
| SQLite (durable) | `SqliteKnowledge` | `Knowledge` | Core |
| Vector (semantic) | `VectorKnowledge` | `Knowledge` | Core |
| Chunked ingestion (files, URLs) | `IngestingKnowledge` | `Knowledge` | Core |

> **Learn more:** [Learn 5 — Give It Knowledge](learn/05-knowledge.md) ·
> [Learn 21 — Knowledge Ingestion](learn/21-knowledge-ingestion.md)

---

## Tools, planning & workflows

| Capability | Implementation | Contract | Ship |
| --- | --- | --- | --- |
| Typed function tools | `FunctionTool`, `ToolRegistry`, `ToolRunner` | `Tool` | Core |
| Schema-driven tool calling | `SchemaToolCaller` | `Tool` | Core |
| Planners | `SequentialPlanner`, `LLMPlanner`, `AdaptivePlanner`, `ReflectivePlanner` | `Planner` | Core |
| Workflows | `SequentialWorkflow`, `GraphWorkflow`, `WorkflowCheckpoint` | `Workflow` | Core |
| Hybrid router (confidence-gated) | `build_router`, `ResponderChain`, responders | `Router` | Core |

> **Learn more:** [Learn 7 — Tools](learn/07-tools.md) ·
> [Learn 8 — Plans & Workflows](learn/08-workflows.md) ·
> [Learn 10 — Give It a Brain](learn/10-brain.md)

---

## Plugins & tooling

| Capability | Implementation | Contract | Ship |
| --- | --- | --- | --- |
| Plugin discovery + lifecycle | `PluginLoader` (entry points + package scan) | `Plugin` | Core |
| Plugin SDK (typed bases, declarative) | `xyberos-plugin-sdk` | `Plugin` | Plugin |
| Plugin validation (static + live) | `xyberos-plugin-validator` | — | Plugin |
| Plugin CLI | `xyberos-cli` (`create` / `validate` / `repair`) | — | Plugin |
| CI validation | `xyberos-plugin-validator` GitHub Action | — | Plugin |

> **Learn more:** [Learn 9 — Skills & Plugins](learn/09-plugins.md) ·
> [Learn 24 — Build & Contribute Plugins](learn/24-plugin-development.md)

---

## Multiplier plugins

A curated set of official plugins lives in the
[`xyberos/xyberos-plugins`](https://github.com/xyberos/xyberos-plugins) repo.
Each is a standalone package with an `xyberos.plugins` entry point, lazy
optional deps, tests, and examples — installed with `pip install -e
./<folder>` from that repo, then auto-discovered by `app.load_entry_points()`.

| Plugin | Package / folder | What it unlocks |
| --- | --- | --- |
| Document loaders | `xyberos-documents` (`documents/`) | `ingest_document` / `ingest_directory` tools + `FileLoader`/`HtmlLoader`/`CsvLoader` (stdlib) and `PdfLoader`/`DocxLoader`/`XlsxLoader` (`[documents]`) → feed `IngestingKnowledge` |
| Generic HTTP/API connector | `xyberos-http-api` (`http-api/`) | Declarative `base_url`/auth/operations spec → one typed `Tool` per operation |
| MCP client | `xyberos-mcp` (`mcp/`) | stdio + streamable HTTP `McpClient` → one `Tool` per server tool (allowlist-guarded) |
| Web search | `xyberos-web-search` (`web-search/`) | one `WebSearch` contract; Tavily / Serper / Brave / Exa / Firecrawl behind a `web_search` tool |

> **Learn more:** [Learn 21 — Knowledge Ingestion](learn/21-knowledge-ingestion.md) ·
> [Integration Roadmap RFC](RFCs/RFC-0019-integrations-roadmap.md) — milestone
> status (M1–M5 shipped here).

---

## Observability & security

| Capability | Implementation | Contract | Ship |
| --- | --- | --- | --- |
| Event bus (32 canonical events) | `EventBus` | `EventBus` | Core |
| Tracing / log exporters | `EventRecorder`, `LoggingExporter`, `Exporter` | `Exporter` | Core |
| Kill switch, guardrails, audit log | `Security`, `KillSwitch`, `Guardrail` | — | Core |

> **Learn more:** [Learn 14 — Observability](learn/14-observability.md) ·
> [Learn 15 — Security](learn/15-security.md)

---

## In development & planned

The roadmap tracks everything that is **not yet available** — from 🟡 in
development to 🔵 community-wanted and ⚪ planned. After the M1–M5 wave shipped
(MCP, HTTP/API, document loaders, Qdrant/FAISS/Redis, web search), the next
in-line work is the remaining LLM provider presets (M6) and the community
wave (M7):

- [Integration Roadmap RFC](RFCs/RFC-0019-integrations-roadmap.md) — status tracker + execution plan

## Contribute an integration

Plugins are the sanctioned way to ship new capabilities — the toolkit makes it
one command:

```bash
pip install xyberos-cli
xyberos plugin create --name github --type tool --non-interactive
xyberos plugin validate .
```

See [Learn 24 — Build & Contribute Plugins](learn/24-plugin-development.md) and
[`plugin-contribution.md`](plugin-contribution.md) for the full
`CREATE → IMPLEMENT → TEST → VALIDATE → DOCUMENT → PACKAGE → PR` pipeline.

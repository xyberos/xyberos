# Features & Plugins

This page is the at-a-glance inventory of what **Xyberos** ships out of the
box (built-in features) and what is available as an installable plugin from the
[`xyberos/xyberos-plugins`](https://github.com/xyberos/xyberos-plugins) GitHub
repository.

- [Built-in features](#built-in-features)
- [Available plugins](#available-plugins)

---

## Built-in features

The core ships in `xyberos` with **zero runtime dependencies** — the standard
library is all it needs (Python 3.10+). 15 stable contracts, 32 canonical
events, ~533 tests at ~90% coverage.

Features ship through three channels:

- 🟢 **Core** — stdlib-only, `pip install xyberos`
- 🟡 **Extra** — lazy optional dependencies, `pip install xyberos[extra]`
- 🔵 **Plugin** — external package via the `xyberos.plugins` entry point

Optional extras: `[embeddings]`, `[vectors]`, `[rerank]`, `[documents]`,
`[state]`, `[mcp]`, `[train]`, and `[llm-providers]`.

### Platform at a glance

| Subsystem | What it does |
| --- | --- |
| **Kernel** | Config, logging, DI, lifecycle, event bus, plugin loader, security |
| **Runtime** | Executes cognitive requests — sync and async |
| **Brain** | Automated pipeline: workflow → cheap-first router → memory → knowledge → intent → plan → router → tools → LLM |
| **LLM** | OpenAI, Anthropic, Gemini, Ollama, any OpenAI-compatible endpoint + embeddings (incl. local `OllamaEmbeddingLLM`) |
| **Memory** | In-memory, SQLite, and vector providers; semantic + consolidating memory |
| **Knowledge** | Fact injection from dicts, SQLite, or vector retrieval |
| **Planner** | Sequential, LLM, adaptive (few-shot), reflective, and plan execution |
| **Intent** | Heuristic, LLM, embedding, and cascade engines with confidence routing |
| **Router** | Confidence-gated responder tiers — template → tool → knowledge → memory → cache → LLM |
| **Learning** | Experience store, feedback, example promotion, offline training (Trainer) |
| **Tools** | Typed function tools with JSON-schema signatures |
| **Workflows** | Sequential + graph-based with branches, loops, pause/resume |
| **Agents** | Multi-agent runtime with messaging, handoffs, roles |
| **Plugins** | Auto-discovery via entry points or package scanning |
| **Events** | Pub/sub bus with 32 canonical events, tracing, and exporters |
| **Security** | Kill switch, content guardrails, audit logging |

### LLM providers

| Provider | Notes |
| --- | --- |
| `EchoLLM` (default) | Zero-dependency echo model — no API keys, no setup |
| `CallableLLM`, `StreamingLLM`, `AsyncLLM` | Sync / streaming / async wrappers |
| `OpenAILLM`, `AnthropicLLM`, `GeminiLLM` | Cloud providers (lazy SDKs) |
| `OllamaLLM`, `OllamaEmbeddingLLM` | Fully local — stdlib HTTP, no SDK |
| `OpenAICompatibleLLM`, `OpenAIEmbeddingLLM` | Any OpenAI-compatible endpoint (stdlib HTTP) |
| `StructuredLLM`, `FallbackLLM` | Structured output; cloud→local fallback chain |
| Embedders | `HashEmbedder` (dev), `SentenceTransformerEmbedder` (`[embeddings]`) |

### Memory, knowledge & vectors

| Subsystem | Built-in providers |
| --- | --- |
| Memory | `InMemoryMemory`, `SqliteMemory`, `VectorMemory`, `ConsolidatingMemory`, `StratifiedMemory` |
| Knowledge | `InMemoryKnowledge`, `SqliteKnowledge`, `VectorKnowledge`, `IngestingKnowledge` |
| Vector stores | `CosineVectorStore`, `SqliteVectorStore` (persistent, stdlib); `ChromaVectorStore`, `PgVectorStore` (lazy `[vectors]`) |
| Experience | `InMemoryExperience`, `SqliteExperience` |

### Planning, intent & learning

| Subsystem | Built-in providers |
| --- | --- |
| Planners | `SequentialPlanner`, `LLMPlanner`, `AdaptivePlanner`, `ReflectivePlanner`, `PlanExecutor` |
| Intent engines | `HeuristicIntentEngine`, `LLMIntentEngine`, `EmbeddingIntentEngine`, `CascadeIntentEngine` |
| Learning | Experience store, `app.feedback(...)`, `ExamplePromoter`, `promote_successful` / `demote_failed` |
| Offline training | `Trainer` (embedding distillation / sklearn), `export_dataset`, artifact registry |

### Routing, tools, workflows & agents

| Subsystem | Built-in capabilities |
| --- | --- |
| Router | `build_router`, `ResponderChain`, responders (template/tool/knowledge/memory/cache/LLM), `CacheTeacher`, `CalibratedResponder`, `GroundingResponder`, `EscalationTuner` |
| Tools | `FunctionTool`, `ToolRegistry`, `ToolRunner`, `SchemaToolCaller` (JSON-schema signatures) |
| Workflows | `SequentialWorkflow`, `GraphWorkflow` (branches, loops), `WorkflowCheckpoint` (SQLite pause/resume) |
| Agents | `RoleAgent`, `MultiAgentRuntime`, handoffs, messaging |

### Observability, security & hardening

| Capability | Built-in |
| --- | --- |
| Events | `EventBus`, `EventRecorder`, `LoggingExporter`, `Exporter` — 32 canonical events |
| Security | Kill switch, `Guardrail`, content guardrails, audit log (`InMemoryAuditStore` / `SqliteAuditStore`) |
| Production hardening | Retries + exponential backoff, rate limiting (token bucket), timeouts, config-driven, all off by default |
| Resilience utils | `utils.resilience` — retry, rate limiter, timeouts |
| Evaluation | `utils.eval` — `intent_accuracy`, `retrieval_recall_at_k`, `plan_success_rate` |

### Facade & plugin tooling

| Capability | Built-in |
| --- | --- |
| Facade | `Xyberos`, `create_app(...)`, `create_semantic_app(...)`, `chat` / `achat`, `app.load_plugin(...)`, `app.load_entry_points()` |
| Plugin discovery | `PluginLoader` — `xyberos.plugins` entry-point group + package scan |
| Plugin SDK | `xyberos-plugin-sdk` — typed/declarative plugin bases |
| Plugin validator | `xyberos-plugin-validator` — static + live validation, CI action |
| Plugin CLI | `xyberos-cli` — `create` / `validate` / `repair` |

---

## Available plugins

The official plugin set lives in the
[`xyberos/xyberos-plugins`](https://github.com/xyberos/xyberos-plugins) GitHub
repository. Each folder is an independently installable package that plugs into
the public `xyberos` API via the `xyberos.plugins` entry-point group. All
milestones (M1–M10) are shipped 🟢. Plugin folder names are prefixed
`vector-*` to avoid shadowing the real `faiss`/`redis` top-level modules.

| Milestone | Plugin (package) | Folder | Plugin class | What it unlocks |
| --- | --- | --- | --- | --- |
| M1 | `xyberos-documents` | [`documents/`](https://github.com/xyberos/xyberos-plugins/tree/master/documents) | `DocumentsPlugin` | `ingest_document` / `ingest_directory` tools + `FileLoader`/`HtmlLoader`/`CsvLoader` (stdlib) and `PdfLoader`/`DocxLoader`/`XlsxLoader` (`[documents]`) → feed `IngestingKnowledge` |
| M2 | `xyberos-http-api` | [`http-api/`](https://github.com/xyberos/xyberos-plugins/tree/master/http-api) | `HttpApiPlugin` | Declarative `base_url`/auth/operations spec → one typed `Tool` per operation |
| M3 | `xyberos-mcp` | [`mcp/`](https://github.com/xyberos/xyberos-plugins/tree/master/mcp) | `McpPlugin` | stdio + streamable HTTP `McpClient` → one `Tool` per MCP server tool (allowlist-guarded) |
| M4 | `xyberos-qdrant` | [`vector-qdrant/`](https://github.com/xyberos/xyberos-plugins/tree/master/vector-qdrant) | `QdrantPlugin` | `QdrantVectorStore` (hosted or local) |
| M4 | `xyberos-faiss` | [`vector-faiss/`](https://github.com/xyberos/xyberos-plugins/tree/master/vector-faiss) | `FaissPlugin` | `FaissVectorStore` (local, no server) |
| M4 | `xyberos-redis` | [`vector-redis/`](https://github.com/xyberos/xyberos-plugins/tree/master/vector-redis) | `RedisPlugin` | `RedisVectorStore`, `RedisMemory`, `RedisStringCache` |
| M5 | `xyberos-web-search` | [`web-search/`](https://github.com/xyberos/xyberos-plugins/tree/master/web-search) | `WebSearchPlugin` | one `WebSearch` contract; Tavily / Serper / Brave / Exa / Firecrawl behind a `web_search` tool |
| M6 | `xyberos-llm-providers` | [`llm-providers/`](https://github.com/xyberos/xyberos-plugins/tree/master/llm-providers) | `LlmProvidersPlugin` | OpenAI-compatible presets (Mistral/Groq/DeepSeek/Cohere/Together/xAI/OpenAI/OpenRouter) + dedicated `AzureOpenAILLM`, `BedrockLLM`, `VertexAILlm` |
| M7 | `xyberos-github` | [`github/`](https://github.com/xyberos/xyberos-plugins/tree/master/github) | `GithubPlugin` | `github_get_user`, `github_list_repos`, `github_create_issue` |
| M7 | `xyberos-gitlab` | [`gitlab/`](https://github.com/xyberos/xyberos-plugins/tree/master/gitlab) | `GitlabPlugin` | `gitlab_get_project`, `gitlab_list_projects` |
| M7 | `xyberos-slack` | [`slack/`](https://github.com/xyberos/xyberos-plugins/tree/master/slack) | `SlackPlugin` | `slack_post_message`, `slack_list_channels` |
| M7 | `xyberos-discord` | [`discord/`](https://github.com/xyberos/xyberos-plugins/tree/master/discord) | `DiscordPlugin` | `discord_send_message`, `discord_get_channel` |
| M7 | `xyberos-notion` | [`notion/`](https://github.com/xyberos/xyberos-plugins/tree/master/notion) | `NotionPlugin` | Notion search / create-page tools |
| M7 | `xyberos-jira` | [`jira/`](https://github.com/xyberos/xyberos-plugins/tree/master/jira) | `JiraPlugin` | `jira_search_issues`, Jira issue tools |
| M7 | `xyberos-linear` | [`linear/`](https://github.com/xyberos/xyberos-plugins/tree/master/linear) | `LinearPlugin` | `linear_search_issues`, `linear_create_issue` |
| M8 | `xyberos-stt` | [`stt/`](https://github.com/xyberos/xyberos-plugins/tree/master/stt) | `SttPlugin` | `stt_transcribe` — Whisper (local), Deepgram, AssemblyAI |
| M8 | `xyberos-tts` | [`tts/`](https://github.com/xyberos/xyberos-plugins/tree/master/tts) | `TtsPlugin` | `tts_synthesize` — ElevenLabs, OpenAI, AWS Polly, local Piper |
| M8 | `xyberos-vision` | [`vision/`](https://github.com/xyberos/xyberos-plugins/tree/master/vision) | `VisionPlugin` | `vision_describe`, `ocr_extract_text`, `image_generate` |
| M9 | `xyberos-auth` | [`auth/`](https://github.com/xyberos/xyberos-plugins/tree/master/auth) | `AuthPlugin` | `jwt_sign`, `jwt_verify` (OAuth2/OIDC/JWT) |
| M9 | `xyberos-storage` | [`storage/`](https://github.com/xyberos/xyberos-plugins/tree/master/storage) | `StoragePlugin` | `storage_list` / `storage_upload` / `storage_download` — S3, Azure Blob, GCS, OneDrive |
| M9 | `xyberos-db` | [`db/`](https://github.com/xyberos/xyberos-plugins/tree/master/db) | `DbPlugin` | `db_list_tables`, `db_query` — SQLite, PostgreSQL, MySQL, DuckDB |
| M9 | `xyberos-queues` | [`queues/`](https://github.com/xyberos/xyberos-plugins/tree/master/queues) | `QueuesPlugin` | `queue_publish`, `queue_poll` — Kafka, RabbitMQ, Redis Streams |
| M10 | `xyberos-observability` | [`observability/`](https://github.com/xyberos/xyberos-plugins/tree/master/observability) | `ObservabilityPlugin` | OTel / Prometheus / Langfuse / Sentry as `EventBus` exporters — `app.chat(...)` → trace |

### How to use each plugin

Every plugin follows the same recipe: install the package, then either load it
explicitly with `app.load_plugin(...)` or let `app.load_entry_points()`
auto-discover it. Plugins use only the public `xyberos` API (`Tool` /
`FunctionTool`, contracts), import optional third-party dependencies lazily,
and are installed with `pip install -e ./<folder>` from the plugins repo. An
unconfigured plugin registers nothing and logs a warning instead of taking the
app down.

#### Data & retrieval (M1–M5)

=== "Documents — `xyberos-documents`"

    ```bash
    pip install -e ./documents
    ```

    ```python
    from xyberos import create_app
    from xyberos.knowledge import IngestingKnowledge
    from xyberos.llm import HashEmbedder
    from xyberos.vector import SqliteVectorStore
    from xyberos_documents import DocumentsPlugin

    knowledge = IngestingKnowledge(SqliteVectorStore("kb.db"), embedder=HashEmbedder())
    app = create_app(knowledge=knowledge)
    app.load_plugin(DocumentsPlugin())

    app.tools.execute("ingest_document", None, path="manual.pdf")
    app.tools.execute("ingest_directory", None, path="./docs", extensions=[".md", ".pdf"])
    ```

    Loads PDF / DOCX / HTML / CSV / XLSX / text and feeds an
    `IngestingKnowledge`. Swap `HashEmbedder` (dev-only) for
    `OllamaEmbeddingLLM` / `OpenAIEmbeddingLLM` for real embeddings.

=== "HTTP/API — `xyberos-http-api`"

    ```bash
    pip install -e ./http-api
    ```

    ```python
    from xyberos import create_app
    from xyberos_http_api import HttpApiPlugin

    app = create_app()
    app.load_plugin(HttpApiPlugin("spec.json"))   # or a dict spec

    app.tools.execute("get_user", None, username="baltz")
    ```

    A declarative `base_url` / auth / operations spec becomes one typed `Tool`
    per operation.

=== "MCP — `xyberos-mcp`"

    ```bash
    pip install -e ./mcp
    ```

    ```python
    from xyberos import create_app
    from xyberos_mcp import McpPlugin

    app = create_app()
    app.load_plugin(McpPlugin({"demo": {"command": ["python", "server.py"]}}))

    app.tools.execute("demo_echo", None, text="hi")
    ```

    Connects to stdio or streamable-HTTP MCP servers and registers one typed
    `Tool` per server tool (allowlist-guarded).

=== "Vector stores — `xyberos-qdrant` / `xyberos-faiss` / `xyberos-redis`"

    ```bash
    pip install -e ./vector-qdrant -e ./vector-faiss -e ./vector-redis
    ```

    ```python
    from xyberos import create_app
    from xyberos_qdrant import QdrantPlugin

    app = create_app()
    app.load_plugin(QdrantPlugin())               # hosted or in-memory

    store = app.resolve("vector_store")
    store.upsert("ns", "doc-1", [1.0, 0.0, 0.0, 0.0], {"text": "north"})
    for hit in store.query("ns", [1.0, 0.1, 0.0, 0.0], top_k=2):
        print(hit.id, hit.score)
    ```

    `FaissPlugin()` registers a local `FaissVectorStore`; `RedisPlugin()`
    registers `RedisVectorStore`, `RedisMemory`, and `RedisStringCache`.

=== "Web search — `xyberos-web-search`"

    ```bash
    pip install -e ./web-search
    ```

    ```python
    from xyberos import create_app
    from xyberos_web_search import WebSearchPlugin

    app = create_app()
    app.load_plugin(WebSearchPlugin(provider="tavily"))   # TAVILY_API_KEY

    app.tools.execute("web_search", None, query="xyberos", top_k=5)
    ```

    One `WebSearch` contract; providers are Tavily, Serper, Brave, Exa, and
    Firecrawl.

#### LLM providers (M6)

=== "LLM providers — `xyberos-llm-providers`"

    ```bash
    pip install -e ./llm-providers
    ```

    ```python
    from xyberos import create_app
    from xyberos_llm_providers import LlmProvidersPlugin

    app = create_app()
    app.load_plugin(LlmProvidersPlugin(provider="deepseek"))  # or LLM_PROVIDER=deepseek
    print(app.llm.generate("Say hi"))
    ```

    Presets: `mistral`, `groq`, `deepseek`, `cohere`, `together`, `xai`,
    `openai`, `openrouter` (all over `OpenAICompatibleLLM`). Dedicated
    adapters: `azure_openai`, `bedrock`, `vertex`.

#### Community wave (M7)

=== "GitHub"

    ```bash
    pip install -e ./github
    ```

    ```python
    from xyberos import create_app
    from xyberos_github import GithubPlugin

    app = create_app()
    app.load_plugin(GithubPlugin())               # GITHUB_TOKEN (optional for public reads)
    app.tools.execute("github_get_user", None, username="octocat")
    app.tools.execute("github_list_repos", None, username="octocat", per_page=30)
    app.tools.execute("github_create_issue", None, owner="o", repo="r", title="Bug", body="...")
    ```

=== "GitLab"

    ```bash
    pip install -e ./gitlab
    ```

    ```python
    from xyberos import create_app
    from xyberos_gitlab import GitlabPlugin

    app = create_app()
    app.load_plugin(GitlabPlugin())               # GITLAB_TOKEN
    app.tools.execute("gitlab_get_project", None, project="group/repo")
    app.tools.execute("gitlab_list_projects", None, search="xyberos", per_page=20)
    ```

=== "Slack"

    ```bash
    pip install -e ./slack
    ```

    ```python
    from xyberos import create_app
    from xyberos_slack import SlackPlugin

    app = create_app()
    app.load_plugin(SlackPlugin())                # SLACK_TOKEN
    app.tools.execute("slack_post_message", None, channel="general", text="hello")
    app.tools.execute("slack_list_channels", None, limit=100)
    ```

=== "Discord"

    ```bash
    pip install -e ./discord
    ```

    ```python
    from xyberos import create_app
    from xyberos_discord import DiscordPlugin

    app = create_app()
    app.load_plugin(DiscordPlugin())              # DISCORD_TOKEN
    app.tools.execute("discord_send_message", None, channel_id="111", content="hello")
    app.tools.execute("discord_get_channel", None, channel_id="111")
    ```

=== "Notion"

    ```bash
    pip install -e ./notion
    ```

    ```python
    from xyberos import create_app
    from xyberos_notion import NotionPlugin

    app = create_app()
    app.load_plugin(NotionPlugin())               # NOTION_TOKEN
    app.tools.execute("notion_search", None, query="roadmap")
    app.tools.execute("notion_create_page", None, parent_id="...", title="New page")
    ```

=== "Jira"

    ```bash
    pip install -e ./jira
    ```

    ```python
    from xyberos import create_app
    from xyberos_jira import JiraPlugin

    app = create_app()
    app.load_plugin(JiraPlugin())                 # JIRA_BASE_URL + JIRA_EMAIL + JIRA_API_TOKEN
    app.tools.execute("jira_search_issues", None, jql="assignee = currentUser()", max_results=5)
    ```

=== "Linear"

    ```bash
    pip install -e ./linear
    ```

    ```python
    from xyberos import create_app
    from xyberos_linear import LinearPlugin

    app = create_app()
    app.load_plugin(LinearPlugin())               # LINEAR_API_KEY
    app.tools.execute("linear_search_issues", None, query="bug", first=10)
    app.tools.execute("linear_create_issue", None, team_id="TEAM", title="New issue")
    ```

#### Voice & vision (M8)

=== "Speech-to-text — `xyberos-stt`"

    ```bash
    pip install -e ./stt
    ```

    ```python
    from xyberos import create_app
    from xyberos_stt import SttPlugin

    app = create_app()
    app.load_plugin(SttPlugin(provider="deepgram"))   # DEEPGRAM_API_KEY
    transcript = app.tools.execute("stt_transcribe", None, audio_path="call.wav")
    ```

    Providers: `whisper` (local), `deepgram`, `assemblyai`.

=== "Text-to-speech — `xyberos-tts`"

    ```bash
    pip install -e ./tts
    ```

    ```python
    from xyberos import create_app
    from xyberos_tts import TtsPlugin

    app = create_app()
    app.load_plugin(TtsPlugin(provider="elevenlabs"))  # ELEVENLABS_API_KEY
    path = app.tools.execute("tts_synthesize", None, text="Hello!", output_path="hello.mp3")
    ```

    Providers: `elevenlabs`, `openai`, `polly` (AWS), `piper` (local CLI).

=== "Vision / OCR / image — `xyberos-vision`"

    ```bash
    pip install -e ./vision
    ```

    ```python
    from xyberos import create_app
    from xyberos_vision import VisionPlugin

    app = create_app()
    app.load_plugin(VisionPlugin())               # OPENAI_API_KEY; OCR needs tesseract
    app.tools.execute("vision_describe", None, image_path="photo.png")
    app.tools.execute("ocr_extract_text", None, image_path="scan.png")
    app.tools.execute("image_generate", None, prompt="a sunset", output_path="out.png")
    ```

#### Enterprise & infrastructure (M9)

=== "Auth — `xyberos-auth`"

    ```bash
    pip install -e ./auth
    ```

    ```python
    from xyberos import create_app
    from xyberos_auth import AuthPlugin

    app = create_app()
    app.load_plugin(AuthPlugin())                 # JWT config
    token = app.tools.execute("jwt_sign", None, payload={"sub": "user-1"}, ttl=3600)
    app.tools.execute("jwt_verify", None, token=token)
    ```

=== "Storage — `xyberos-storage`"

    ```bash
    pip install -e ./storage
    ```

    ```python
    from xyberos import create_app
    from xyberos_storage import StoragePlugin

    app = create_app()
    app.load_plugin(StoragePlugin())              # S3 / Azure Blob / GCS / OneDrive
    app.tools.execute("storage_upload", None, key="a/b.txt", file_path="local.txt")
    app.tools.execute("storage_list", None, prefix="a/")
    app.tools.execute("storage_download", None, key="a/b.txt", output_path="copy.txt")
    ```

=== "Database — `xyberos-db`"

    ```bash
    pip install -e ./db
    ```

    ```python
    from xyberos import create_app
    from xyberos_db import DbPlugin

    app = create_app()
    app.load_plugin(DbPlugin(backend="sqlite"))    # or dsn="postgres://user:pass@host/db"
    app.tools.execute("db_list_tables", None)
    rows = app.tools.execute("db_query", None, sql="SELECT id, name FROM users")
    ```

    `dsn` auto-detects the backend (`postgres://`, `mysql://`, `duckdb://`,
    anything else → SQLite path).

=== "Queues — `xyberos-queues`"

    ```bash
    pip install -e ./queues
    ```

    ```python
    from xyberos import create_app
    from xyberos_queues import QueuesPlugin

    app = create_app()
    app.load_plugin(QueuesPlugin())               # QUEUE_PROVIDER (kafka / rabbitmq / redis)
    app.tools.execute("queue_publish", None, queue="events", message={"type": "ping"})
    app.tools.execute("queue_poll", None, queue="events")
    ```

#### Observability (M10)

=== "Observability — `xyberos-observability`"

    ```bash
    pip install -e ./observability
    ```

    ```python
    from xyberos import create_app
    from xyberos_observability import ObservabilityPlugin

    app = create_app()
    app.load_plugin(ObservabilityPlugin())        # OBSERVABILITY_EXPORTERS=otel,prometheus,...
    app.chat("hello")                             # emits events to the configured exporters
    ```

    Exporters: OTel, Prometheus, Langfuse, Sentry — wired as `EventBus`
    exporters so `app.chat(...)` produces a trace.

### Install & validate

Install any subset of plugins from the repo, then run their tests and confirm
auto-discovery:

```bash
# from the xyberos-plugins repo — install any subset you need
pip install -e ./http-api -e ./documents
pip install -e ./vector-qdrant -e ./vector-faiss -e ./vector-redis
pip install -e ./mcp -e ./web-search -e ./llm-providers
pip install -e ./github -e ./gitlab -e ./slack -e ./discord -e ./notion -e ./jira -e ./linear
pip install -e ./stt -e ./tts -e ./vision
pip install -e ./auth -e ./storage -e ./db -e ./queues
pip install -e ./observability

# run a plugin's tests from its folder
cd http-api && python -m pytest tests -q

# auto-discover installed plugins through the entry-point group
python -c "from xyberos import create_app; app = create_app(); print(app.load_entry_points())"
```

> **See also:** the
> [Integration Roadmap RFC](RFCs/RFC-0019-integrations-roadmap.md) for status
> and what's planned, and [Learn 24 — Build & Contribute
> Plugins](learn/24-plugin-development.md) to ship your own.

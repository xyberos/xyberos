# 21. Knowledge Ingestion

[**← Previous**](20-lifecycle.md) · [**Next →**](22-training-tutorial.md)

Xyberos can index raw text into a semantic knowledge base and have the Brain
inject the relevant facts into every prompt. This tutorial shows how to ingest
knowledge from **local files** and **web URLs**, persist it, and wire it into an
app.

## How ingestion works

Ingestion is provided by **`IngestingKnowledge`** (`xyberos.knowledge`), a
subclass of `VectorKnowledge`:

```python
knowledge.ingest(text, chunk_size=512)  # -> number of chunks indexed
```

`ingest()` splits the text into paragraph-aware chunks (hard-splitting any
paragraph longer than `chunk_size`), embeds each chunk, and indexes it as a
fact in a `VectorStore`. The Brain later queries the same store by embedding
similarity and injects the top matches as `Relevant knowledge:`.

You need two things:

- a **`VectorStore`** to hold the index — use `SqliteVectorStore("kb.db")` for
  zero-dependency persistence, or `ChromaVectorStore`/`PgVectorStore`
  (`pip install xyberos[vectors]`).
- an **`embedder`** — a callable or any object with `embed(text)`. Without one,
  `ingest()` raises `ProviderError`.

| Embedder | When to use |
|---|---|
| `HashEmbedder()` | development/tests — deterministic, dependency-free, but only matches near-identical text |
| `OllamaEmbeddingLLM(model="nomic-embed-text")` | real local semantics, no cloud, no SDK (stdlib HTTP) |
| `OpenAIEmbeddingLLM(model, base_url=...)` | any OpenAI-compatible `/embeddings` endpoint |
| `SentenceTransformerEmbedder(model_name)` | `pip install xyberos[embeddings]` |

## 1. Set up a persistent knowledge base

```python
from xyberos.knowledge import IngestingKnowledge
from xyberos.llm import OllamaEmbeddingLLM
from xyberos.vector import SqliteVectorStore

kb = IngestingKnowledge(
    SqliteVectorStore("kb.db"),          # survives restarts; thread-safe
    embedder=OllamaEmbeddingLLM(model="nomic-embed-text"),  # ollama pull nomic-embed-text
)
```

## 2. Ingest a local file

`ingest()` takes **plain text**, so for a text/markdown file just read it:

```python
from pathlib import Path

markdown = Path("policies.md").read_text(encoding="utf-8")
count = kb.ingest(markdown)
print(f"indexed {count} chunks")
```

For binary formats (PDF, DOCX, HTML) the core stays dependency-free, so you
bring your own text extractor and pass its output to `ingest()`:

```python
# Example with pypdf (optional: pip install pypdf)
from pypdf import PdfReader

text = "\n\n".join(page.extract_text() or "" for page in PdfReader("manual.pdf").pages)
kb.ingest(text)
```

### Prefer the `xyberos-documents` plugin

Instead of hand-writing extractors, install the official document-loaders
plugin (RFC-0019 M1) from the
[`xyberos/xyberos-plugins`](https://github.com/xyberos/xyberos-plugins) repo. It
ships `PdfLoader` / `DocxLoader` / `HtmlLoader` / `CsvLoader` / `XlsxLoader`
(optional deps via `pip install xyberos[documents]`) and registers two tools
that feed an `IngestingKnowledge` directly:

```python
from xyberos import create_app
from xyberos.knowledge import IngestingKnowledge
from xyberos.llm import HashEmbedder
from xyberos.vector import SqliteVectorStore
from xyberos_documents import DocumentsPlugin

app = create_app(
    knowledge=IngestingKnowledge(SqliteVectorStore("learning.db"), embedder=HashEmbedder())
)
app.load_plugin(DocumentsPlugin())

app.tools.execute("ingest_document", None, path="report.pdf", chunk_size=512)
app.tools.execute("ingest_directory", None, path="docs/", extensions=[".pdf", ".docx"])
```

Or use the loaders standalone (no app required):

```python
from xyberos_documents import PdfLoader

for doc in PdfLoader().load("report.pdf"):
    print(doc.text)
```

## 3. Ingest a URL

Fetch the page with the standard library, strip the markup, then ingest:

```python
import re
import urllib.request

def fetch_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")
    html = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html).strip()

kb.ingest(fetch_text("https://example.com/faq"))
```

> For cleaner extraction on messy pages, install a parser such as
> BeautifulSoup (`pip install beautifulsoup4`) and replace the regex strip.

## 4. Wire it into an app

Pass the knowledge base to `create_app()` and the Brain will retrieve and
inject matching facts into every prompt:

```python
from xyberos import create_app
from xyberos.llm import OllamaLLM

app = create_app(
    llm=OllamaLLM(model="qwen2.5:1.5b"),
    knowledge=kb,
)

print(app.chat("What are your office hours?"))
# The LLM sees: "Relevant knowledge:\n- ...: Support is available 9am-6pm..."
```

If you also want the vector intent/memory/planner stack, build the app with
`create_app(knowledge=kb, ...)` and add the providers from the
[Training Tutorial](22-training-tutorial.md) — `create_semantic_app` builds its own
plain `VectorKnowledge`, so use `create_app` when you need the `ingest()`
capability.

## 5. Query the index directly

```python
from xyberos.runtime.context import CognitiveContext

ctx = CognitiveContext("tell me about refunds")
print(kb.query(ctx))                 # top facts formatted for prompt injection

for hit in kb.query_scored(ctx, top_k=3):   # raw scores for confidence gating
    print(f"{hit.score:.2f}  {hit.payload['value']}")
```

## Complete example

```python
"""Ingest a markdown file + a URL, then answer questions from the combined KB."""
import re
import urllib.request
from pathlib import Path

from xyberos import create_app
from xyberos.knowledge import IngestingKnowledge
from xyberos.llm import OllamaEmbeddingLLM, OllamaLLM
from xyberos.vector import SqliteVectorStore

def fetch_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")
    html = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()

kb = IngestingKnowledge(
    SqliteVectorStore("kb.db"),
    embedder=OllamaEmbeddingLLM(model="nomic-embed-text"),
)
kb.ingest(Path("policies.md").read_text(encoding="utf-8"))   # from a file
kb.ingest(fetch_text("https://example.com/faq"))             # from a URL

app = create_app(llm=OllamaLLM(model="qwen2.5:1.5b"), knowledge=kb)
print(app.chat("What are your office hours?"))
```

## Notes & limits

- **Chunking** — `ingest()` splits on blank lines and hard-splits long
  paragraphs at `chunk_size` (default 512 chars). Tune `chunk_size` to your
  documents; smaller chunks match more precisely, larger chunks carry more
  context.
- **Embedding quality matters** — `HashEmbedder` is a dev stand-in; for real
  paraphrase matching use a semantic embedder so questions phrased differently
  from the source text still retrieve the right facts.
- **Persistence** — `SqliteVectorStore("kb.db")` keeps the index across
  restarts; reuse the same path to build on an existing KB. It is thread-safe
  (one connection per thread).
- **No built-in parsers** — the core is dependency-free, so PDF/DOCX/HTML
  extraction is up to you (the examples above use `pypdf` and a stdlib regex
  strip). Feed the extracted text to `ingest()`. For batteries included, the
  `xyberos-documents` plugin provides ready-made loaders and
  `ingest_document` / `ingest_directory` tools (RFC-0019 M1).

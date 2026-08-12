# 22. Training Xyberos

[**← Previous**](21-knowledge-ingestion.md) · [**Next →**](23-customer-support-tutorial.md)

Xyberos becomes *trainable* through the RFC-0016 learning layer. There are two
levels of training:

1. **Runtime adaptation** (default, no weights, no retraining) — the system
   learns by accumulation: it records every turn, honors your feedback, and
   promotes successful outcomes back into its intent, planner, memory, and
   knowledge engines.
2. **Offline distillation** (optional, `xyberos[train]`) — export the episodes
   you have collected, train a small scikit-learn intent classifier (or rebuild
   an embedding index), and save it as an artifact you load at startup.

This tutorial walks the full loop: **capture → rate → promote → learn → evaluate
→ distill → serve**.

```
request ──▶ Brain pipeline ──▶ ExperienceStore.record
                                     │
                          app.feedback(rating)  ──▶ Episode.feedback
                                     │
                          ExamplePromoter.promote()  ──▶ intent/planner .learn()
                                     │
                          evaluate (intent_accuracy, recall@k, plan success)
                                     │
                          Trainer (offline distill)  ──▶ artifact (JSON/joblib)
                                     │
                          serve (learning.model config)  ──▶ new app
```

## Prerequisites

```bash
pip install xyberos            # base package — enough for runtime adaptation
pip install "xyberos[train]"   # adds scikit-learn + joblib for offline training
pip install "xyberos[vectors]" # optional chromadb / pgvector adapters
```

Everything in sections 1–4 needs nothing beyond the base package.

## 1. Capture — record every episode

Enable the experience layer so the Brain records an `Episode` (prompt, intent,
plan, response) after every completed turn.

```python
from xyberos import create_app
from xyberos.llm import CallableLLM

app = create_app(
    llm=CallableLLM(lambda prompt: f"answer: {prompt}"),
    config={"experience.enabled": True},
)

app.chat("I need a refund")      # records an episode
app.chat("What are your hours?") # records another

app.experience.stats()
# {'total': 2, 'by_outcome': {...}, 'by_intent': {...}}
```

Each turn also emits `brain.episode_recorded`, so you can observe the stream via
`app.events.subscribe("brain.episode_recorded", ...)`.

## 2. Rate — attach feedback

`app.feedback()` is the training signal. Ratings range from **-1.0** (bad) to
**+1.0** (great) and fire the `brain.feedback_recorded` event.

```python
episode_id = app.experience.query(limit=1)[0].id
app.feedback(episode_id, 1.0, note="great answer")
```

`promote_successful()` and `demote_failed()` in `xyberos.learning` turn the
ratings into positive and negative example sets:

```python
from xyberos.learning import demote_failed, promote_successful

good = promote_successful(app.experience)   # outcome=="success" or feedback >= 0.5
bad = demote_failed(app.experience)         # outcome=="failure" or feedback <= -0.5
```

## 3. Learn at runtime

### Intent that learns by accumulation

An `EmbeddingIntentEngine` classifies a request by its nearest labeled example.
Adding an example (`learn`) improves classification immediately — no retraining.

```python
from xyberos.intent import EmbeddingIntentEngine
from xyberos.llm import OpenAIEmbeddingLLM
from xyberos.vector import CosineVectorStore

embedder = OpenAIEmbeddingLLM(
    "text-embedding-3-small",
    base_url="https://api.openai.com/v1",
    api_key="sk-...",                     # any duck-typed embed(text) works
)
intent_engine = EmbeddingIntentEngine(CosineVectorStore(), embedder=embedder)

intent_engine.learn("refund", "please refund my order")
intent_engine.classify("I want my money back")   # -> Intent(name='refund', ...)
```

> **Local alternative:** for a fully-local, no-cloud embedder, use
> `OllamaEmbeddingLLM(model="nomic-embed-text")` (stdlib HTTP to Ollama's
> `/api/embed`, no SDK). It is a drop-in replacement for any `embedder=` slot.

> **Persistence:** everything learned at runtime lives in the `VectorStore`.
> `CosineVectorStore` is in-memory only, so use `SqliteVectorStore` (stdlib
> `sqlite3`, no extra dependencies) to keep learned examples across restarts:

```python
from xyberos.vector import SqliteVectorStore

store = SqliteVectorStore("learning.db")   # survives process restarts
intent_engine = EmbeddingIntentEngine(store, embedder=embedder)
```

The fastest way to get a fully persistent, semantic app is `create_semantic_app`
— one call wires intent, memory, knowledge, and planner to a shared
`SqliteVectorStore("learning.db")`, and enables the intent step:

```python
from xyberos import create_semantic_app

app = create_semantic_app(llm=llm, embedder=embedder)   # persistent by default
# swap the backend without touching the engines:
# app = create_semantic_app(llm=llm, embedder=embedder, store=ChromaVectorStore())
```

### Promote good outcomes automatically

`ExamplePromoter` connects the dots: it scans the experience store for
successful/positively-rated episodes and feeds them into your intent engine and
adaptive planner via `learn()`.

```python
from xyberos.intent import EmbeddingIntentEngine
from xyberos.learning import ExamplePromoter
from xyberos.planner import AdaptivePlanner
from xyberos.vector import CosineVectorStore

store = CosineVectorStore()
intent_engine = EmbeddingIntentEngine(store, embedder=embedder)
planner = AdaptivePlanner(app.llm, store=store, embedder=embedder)

promoter = ExamplePromoter(
    app.experience,
    intent_engine=intent_engine,
    planner=planner,
)
promoter.promote()   # -> intent_engine.learn(name, prompt) + planner.learn(prompt, plan)
```

### Few-shot planning

`AdaptivePlanner` retrieves the most similar past `request → plan` examples and
asks the LLM to follow that style. `learn()` adds examples; `promote()` above
does this automatically from episodes that carried a plan.

```python
planner.learn("refund an order", ["check order", "process refund", "confirm"])
plan = planner.plan(app.run("I need a refund").prompt)   # few-shot plan
```

### Semantic memory and knowledge

`VectorMemory` and `VectorKnowledge` replace substring matching with
embedding-based retrieval. They "learn by accumulation" too — every stored turn
or fact improves future retrieval.

```python
from xyberos.knowledge import VectorKnowledge
from xyberos.memory import VectorMemory

memory = VectorMemory(store, embedder=embedder, alpha=0.7)      # similarity + recency
knowledge = VectorKnowledge(store, embedder=embedder)

app = create_app(
    llm=app.llm,
    intent=intent_engine,
    planner=planner,
    memory=memory,
    knowledge=knowledge,
    config={"brain.intent": True},
)
```

The Brain runs the intent step before planning, so `context.intent.target` can
route tools automatically — and `ToolRunner.choose` honors that target first.

## 4. Evaluate

The `xyberos.utils` helpers measure whether training actually helped. Each takes
a plain `(input, expected)` dataset.

```python
from xyberos.utils import intent_accuracy, plan_success_rate, retrieval_recall_at_k

print(intent_accuracy(intent_engine, [
    ("please refund", "refund"),
    ("hello", "hello"),
]))                                        # top-1 intent accuracy

print(retrieval_recall_at_k(store, embedder, [
    ("refund policy", "refund-policy-doc"),
], k=5))                                    # recall@k

print(plan_success_rate(executor, [
    (app.run("x"), ["step_a", "step_b"]),
]))                                         # plan execution success
```

## 5. Distill offline (optional)

Once you have collected and rated enough episodes, export them and train a
small model — either a dependency-free embedding index or a scikit-learn
classifier (`xyberos[train]`).

```python
from xyberos.trainer import Trainer, export_dataset

dataset = export_dataset(app.experience)    # -> [(prompt, intent_label), ...]
print(len(dataset), "labeled examples")

trainer = Trainer(dataset)

# (a) dependency-free: an embedding index distilled from the examples
trainer.save("intent-model.json", algorithm="embedding")

# (b) scikit-learn classifier (needs `pip install xyberos[train]`)
trained = trainer.train_intent_sklearn(embedder)
trainer.save("intent-model.joblib", algorithm="sklearn", embedder=embedder)
```

Artifact formats:

- **embedding** — plain JSON `{"algorithm": "embedding", "examples": [[prompt, label], ...]}`;
  the embedder is *not* stored, so pass one when loading.
- **sklearn** — a joblib file containing the fitted classifier *and* its
  embedder, so no embedder is needed when loading.

## 6. Serve

Load the trained engine and hand it to `create_app` exactly like any other
intent engine — it stays behind the same `IntentEngine` contract.

```python
from xyberos import create_app
from xyberos.trainer import Trainer, engine_from_config

# embedding artifact: provide the embedder
served = Trainer.load("intent-model.json", embedder=embedder)

# sklearn artifact: no embedder needed
served = Trainer.load("intent-model.joblib")

# or wire it through config for zero-code startup
served = engine_from_config({"learning.model": "intent-model.joblib"})

app = create_app(intent=served, config={"brain.intent": True})
print(app.run("please refund").intent.name)   # -> 'refund'
```

## Full runnable example

A complete, self-contained script (no external services — it uses a tiny
keyword embedder and `CallableLLM` as stand-ins for a real embedding model and
LLM). Save it as `train_xyberos.py` and run with `python train_xyberos.py`.

```python
"""Train Xyberos end-to-end: capture -> rate -> promote -> learn -> evaluate -> distill -> serve."""

from xyberos import create_app
from xyberos.experience import InMemoryExperience
from xyberos.intent import EmbeddingIntentEngine, HeuristicIntentEngine, IntentRule
from xyberos.learning import ExamplePromoter
from xyberos.llm import CallableLLM
from xyberos.planner import AdaptivePlanner
from xyberos.trainer import Trainer, engine_from_config, export_dataset
from xyberos.utils import intent_accuracy
from xyberos.vector import CosineVectorStore

VOCAB = ("refund", "hours", "hello")

def embedder(text):  # stand-in for a real embedding model
    vector = [0.0] * len(VOCAB)
    for word in text.lower().split():
        for i, term in enumerate(VOCAB):
            if term in word or word in term:
                vector[i] += 1.0
    return vector

llm = CallableLLM(lambda prompt: f"answer: {prompt}")
experience = InMemoryExperience()
student = EmbeddingIntentEngine(CosineVectorStore(), embedder=embedder)
planner = AdaptivePlanner(llm, store=CosineVectorStore(), embedder=embedder)

# 1-2. Capture with rule-based intent labels, then rate every episode
app = create_app(
    llm=llm,
    intent=HeuristicIntentEngine([
        IntentRule("refund", ("refund",)),
        IntentRule("hours", ("hours", "open")),
        IntentRule("hello", ("hello",)),
    ]),
    planner=planner,
    experience=experience,
    config={"brain.intent": True, "experience.enabled": True},
)
app.chat("I need a refund")
app.chat("hello there")
for episode in experience.query():
    app.feedback(episode.id, 1.0)

# 3. Promote good episodes into the student intent engine + planner
promoter = ExamplePromoter(experience, intent_engine=student, planner=planner)
promoter.promote()

# 4. Evaluate the student
dataset = export_dataset(experience)
print("accuracy:", intent_accuracy(
    student, [("please refund", "refund"), ("hi hello", "hello")]
))

# 5. Distill + save an artifact
trainer = Trainer(dataset)
trainer.save("intent-model.json")

# 6. Reload and serve
served = engine_from_config({"learning.model": "intent-model.json"}, embedder=embedder)
app2 = create_app(llm=llm, intent=served, config={"brain.intent": True})
print("served intent:", app2.run("please refund").intent.name)   # -> 'refund'
```

Expected output:

```text
accuracy: 1.0
served intent: refund
```

## Next steps

- **Deepen the loop** — run `promote()` on a schedule or after each batch of
  feedback; keep ratings visible in `app.experience.stats()`.
- **Close the plan loop** — combine `AdaptivePlanner` with `PlanExecutor` to
  execute, verify, and re-plan steps at runtime.
- **Measure regressions** — add the evaluation metrics from section 4 to CI so a
  change that makes the engines worse fails the build.
- **Swap backends** — `CosineVectorStore` is for development; `SqliteVectorStore`
  persists everything with zero extra dependencies, and
  `ChromaVectorStore`/`PgVectorStore` (`xyberos[vectors]`) scale up to larger or
  distributed indexes behind the same engines.

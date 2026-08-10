# Xyberos Tutorial — Build a Customer Support Assistant

> **Beginner friendly.** No AI experience and no API keys required. In about 30
> minutes you'll build a working AI **customer support assistant** — a bot that
> knows your company's policies, remembers the conversation, looks up orders,
> opens tickets, asks a human to approve refunds, and hands tough cases to a
> real agent. Every step is a complete, copy-pasteable program.

## What you'll build

| Step | Your assistant learns to… | Concept you're learning |
|---|---|---|
| 1–3 | say hello with a real (local) model | apps, the pipeline, LLMs |
| 4 | answer "what are your hours?" from a fact sheet | **knowledge** |
| 5 | remember what you told it | **memory** |
| 6 | look up orders and open tickets | **tools** |
| 7 | handle repeat questions *without* the LLM | **hybrid router** |
| 8 | run a refund that waits for a human "yes" | **workflows** |
| 9 | escalate to a human agent | **agents** |
| 10 | serve it as a web API | **FastAPI + async + streaming** |
| 11 | survive failures and block bad prompts | **hardening + security** |

## Before you start

- **Python 3.10 or newer** — check with `python --version`.
- Install Xyberos (the core is **zero-dependency** — just the standard library):

```bash
pip install xyberos
```

- *(Optional but recommended)* A local [Ollama](https://ollama.com) server so
  you can use a **real model with no API key and no cloud**:

```bash
ollama pull llama3.2
```

  Don't want to install Ollama? No problem — every example runs with a
  deterministic stand-in, so nothing here is required to follow along.

> **How to follow along:** put each snippet in its own file (e.g. `step1.py`)
> and run it with `python step1.py`. Each step is a complete program, not a
> fragment.

---

# Part 1 — Hello, Xyberos

## 1. Your first app

```python
from xyberos import create_app

app = create_app()
print(app.chat("Hello, world!"))   # -> Hello, world!
```

What just happened?

- `create_app()` builds a **fully-wired AI application** for you — model,
  memory, knowledge, planner, tools, security, and more. You didn't wire any
  of it by hand.
- `app.chat("...")` sends your text through the whole **cognitive pipeline**
  and returns the reply as a string.
- With no model configured, Xyberos uses `EchoLLM`, which simply echoes your
  prompt back. That's the "Hello, world!" of AI apps — **zero setup, zero
  cost, zero API keys.**

## 2. What's actually happening under the hood

Use `app.run()` instead of `app.chat()` and you get back a `CognitiveContext`
— an object that carries everything about the request:

```python
from xyberos import create_app

app = create_app()
ctx = app.run("Hello, world!")

print(ctx.prompt)      # the input
print(ctx.response)    # the model's reply
print(ctx.succeeded)   # True when there was no error
print(ctx.metadata)    # open-ended dict you can attach anything to
```

A single `app.chat(prompt)` runs the **automated pipeline**:

```text
Workflow → Memory → Knowledge → Intent → Plan → Tools → LLM → Memory
 (pre-steps) (history)  (facts)   (goal)   (steps) (actions) (reply) (remember)
```

The key idea: **the "brain" orchestrates all of this automatically.** You add
capabilities (facts, history, tools) and the brain uses them in the right
order. You rarely call subsystems yourself — you configure them and
`app.chat()` does the rest.

The app also exposes those subsystems directly, so you can inspect them:

```python
app.llm            # the model
app.memory         # conversation history
app.knowledge      # facts
app.planner        # produces plans
app.tools          # registered tools
app.events         # pub/sub observability
```

## 3. Use a real model — with no API keys

The simplest way to use a real model is **Ollama**, a free local server. After
`ollama pull llama3.2`:

```python
from xyberos import create_app
from xyberos.llm import OllamaLLM

app = create_app(llm=OllamaLLM(model="llama3.2"))
print(app.chat("Explain quantum computing in one sentence."))
```

`OllamaLLM` talks to your local Ollama server over plain HTTP — **no SDK, no
cloud, no API key.**

Other ways to plug in a model:

- `CallableLLM(func)` — wrap any plain `prompt -> text` function. The perfect
  fake for building and testing before you spend money on a model:

  ```python
  from xyberos import create_app
  from xyberos.llm import CallableLLM

  app = create_app(llm=CallableLLM(lambda prompt: f"[support] {prompt}"))
  ```

- `OpenAICompatibleLLM` — any OpenAI-compatible `/chat/completions` endpoint
  (OpenAI, vLLM, LM Studio, llama.cpp).
- `OpenAILLM`, `AnthropicLLM`, `GeminiLLM` — the official SDKs, imported lazily
  (they raise a clear error if the SDK isn't installed).

---

# Part 2 — Build the support assistant

Now we build the real thing. Each section adds **one capability** to the same
customer-support bot, so by the end you'll have a complete app.

## 4. Teach it facts — Knowledge

Support bots answer "what are your hours?" or "what's your refund policy?"
from a **fact sheet**. That's the `Knowledge` subsystem: facts that are
injected into the prompt so the model answers from *your* data.

```python
from xyberos import create_app
from xyberos.knowledge import SqliteKnowledge
from xyberos.llm import CallableLLM

knowledge = SqliteKnowledge("facts.db")              # durable, stdlib sqlite
knowledge.add("hours", "Support is available 9am-6pm Mon-Fri.")
knowledge.add("billing", "Billing questions go to billing@example.com.")
knowledge.add("refund", "Refunds are processed within 5-7 business days.")

app = create_app(
    llm=CallableLLM(lambda prompt: prompt),          # echo so you can SEE the injection
    knowledge=knowledge,
)
print(app.chat("what are your hours?"))
```

You'll see the model's input already contains your fact:

```text
what are your hours?

Relevant knowledge:
{'hours': 'Support is available 9am-6pm Mon-Fri.'}
```

That's the whole trick — the brain retrieves matching facts and **enriches the
prompt** before calling the model. Use `SqliteKnowledge("facts.db")` for facts
that survive restarts, or `InMemoryKnowledge({...})` for throwaway ones.

## 5. Make it remember — Memory

Users say "my order is A-100" and then "what did I just ask about?" — the bot
must **remember the conversation**. That's `Memory` (and `create_app()` wires it
in for you):

```python
from xyberos import create_app
from xyberos.memory import SqliteMemory

app = create_app(memory=SqliteMemory("chat.db"))     # survives restarts
app.chat("my order is A-100")
print(app.chat("what did I just ask about?"))        # sees the history
```

Past turns are added to the prompt as conversation history, so the model
answers in context. Use `SqliteMemory` for real persistence or the default
in-memory memory for quick tests. Inspect what it remembers:

```python
for entry in app.memory.retrieve(None):
    print(entry.prompt, "->", entry.response)
```

## 6. Give it hands — Tools

A bot that only talks gets stuck. **Tools** are named capabilities it can act
on — look up an order, open a ticket. The easiest way is `FunctionTool`, which
turns a plain typed function into a tool and derives a JSON schema from the
signature:

```python
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import FunctionTool, ToolRegistry

ORDERS = {"A-100": "shipped", "A-200": "delivered", "B-300": "processing"}

def lookup_order(order_id: str = "unknown") -> str:
    """Look up the status of an order by id."""
    status = ORDERS.get(order_id.upper(), "not found")
    return f"Order {order_id} status: {status}"

def open_ticket() -> str:
    """Open a new support ticket."""
    return "A support ticket has been opened (ticket #T-1001)."

registry = ToolRegistry([
    FunctionTool("lookup_order", lookup_order, description="Look up an order's status"),
    FunctionTool("open_ticket", open_ticket, description="Open a new support ticket"),
])

# Run a tool by name, passing its arguments:
print(registry.execute("lookup_order", CognitiveContext("order"), order_id="A-100"))
# -> Order A-100 status: shipped

# The JSON schema is generated from the function signature:
print(registry.get("lookup_order").schema)
```

Notice the types: `FunctionTool` reads the signature (`order_id: str`),
generates a JSON schema, and **validates/coerces** arguments before calling the
function. Hand-executing tools like this is the simplest way to start; later
you can let the LLM *choose* which tool to run.

## 7. Handle repeat questions without the LLM — the hybrid router

Here's the smart part. A support bot gets the **same questions over and over**
(\"hours?\", \"refund?\", \"status?\"). Calling the LLM for every repeat is slow
and expensive. The **hybrid router** answers each request with the *cheapest
confident tier* first:

```text
Template → Tool → Knowledge → Memory → Cache → LLM → Degrade
 (canned)  (actions)  (facts)  (history)  (learned)  (novel tail)  (fallback)
```

- Tiers 0–4 can answer **without any LLM call**.
- The LLM handles only the **novel tail**, and it **teaches** the cache — so
  the same question next time is served by the cache, not the model.

The easiest way to get this is `create_semantic_app` with a **real embedder**
(semantic matching needs one; the default `HashEmbedder` is for development).

#### Fully-local semantic stack

If you run Ollama, you get a fully-local, no-cloud stack — one server for chat
*and* embeddings (pull the embedding model once):

```bash
ollama pull nomic-embed-text
```

```python
from xyberos import create_semantic_app
from xyberos.llm import OllamaLLM, OllamaEmbeddingLLM

app = create_semantic_app(
    llm=OllamaLLM(model="llama3.2"),
    embedder=OllamaEmbeddingLLM(model="nomic-embed-text"),  # real semantic matching
    router="hybrid",  # template → tool → knowledge → memory → cache → LLM
)

print(app.chat("What time are you open?"))    # answered cheaply after warm-up
```

Other embedders are drop-in: `SentenceTransformerEmbedder` (local, needs
`pip install xyberos[embeddings]`) or `OpenAIEmbeddingLLM` (remote).

## 8. Automate a process — Workflows

Refunds shouldn't be instant — a human should approve them. **Workflows** let
you model a process with steps that can **pause for human input** and resume
later, even after a server restart.

```python
from xyberos.exceptions import WorkflowPaused
from xyberos.runtime.context import CognitiveContext
from xyberos.workflows import GraphWorkflow, WorkflowCheckpoint

refund = GraphWorkflow("verify")

def verify(context):
    if GraphWorkflow.RESUME_KEY in context.metadata:          # resumed with a value?
        decision = context.metadata[GraphWorkflow.RESUME_KEY]
        context.response = "approved" if decision == "yes" else "rejected"
        return context
    raise WorkflowPaused(prompt="Approve this refund? Reply yes or no.")

refund.add_node("verify", verify)

# Start the flow -> it pauses for approval
run = refund.execute(CognitiveContext("refund A-100"))
print(run.status)     # paused
print(run.prompt)     # Approve this refund? Reply yes or no.

# A human decides "yes" -> the flow resumes and finishes
run = refund.resume(run, "yes")
print(run.context.response)   # approved
```

Pause a run across restarts with a checkpoint:

```python
checkpoint = WorkflowCheckpoint("runs.db")
run = refund.execute(CognitiveContext("refund B-300"))
checkpoint.save("run-1", run)          # save the paused run to disk
# ...server restarts...
restored = checkpoint.load("run-1")
refund.resume(restored, "no")          # -> context.response == "rejected"
```

For a simple fixed sequence, `SequentialWorkflow([step1, step2, ...])` runs
steps in order. Use `GraphWorkflow` when you need branches, loops, or
human-in-the-loop.

## 9. Add teammates — Agents

Some requests are too hard for the bot. **Agents** let you hand a request from
one participant to another — here a *supervisor* hands off to a *support
worker*:

```python
from xyberos import create_app
from xyberos.agents import RoleAgent, handoff, post

def supervisor_run(context):
    post(context, handoff("support_worker", sender="supervisor"))
    return context

def worker_run(context):
    context.response = f"Escalated: a human agent will follow up on '{context.prompt}'."
    return context

app = create_app()
app.register_agent(RoleAgent("supervisor", "triage", run=supervisor_run))
app.register_agent(RoleAgent("support_worker", "resolver", run=worker_run))

result = app.run_agents("I need a human", agent_names=["supervisor", "support_worker"])
print(result.response)   # Escalated: a human agent will follow up on 'I need a human'.
```

`handoff(...)` tells the runtime to run the named agent next. The whole
exchange is recorded on `app.agents.messages`, so you get a full audit trail.

## 10. Serve it on the web — FastAPI

To turn the bot into a real service, expose it over HTTP. Xyberos has an async
API (`app.achat`) that works perfectly inside FastAPI:

```python
# server.py  (pip install fastapi uvicorn)
from fastapi import FastAPI
from pydantic import BaseModel

from xyberos import create_app
from xyberos.llm import OllamaLLM

app = FastAPI(title="Support Assistant")
bot = create_app(llm=OllamaLLM(model="llama3.2"))

class ChatRequest(BaseModel):
    prompt: str

@app.post("/chat")
async def chat(body: ChatRequest):
    return {"response": await bot.achat(body.prompt)}
```

Run it:

```bash
pip install fastapi uvicorn
uvicorn server:app --reload
```

```bash
curl -X POST localhost:8000/chat -H 'Content-Type: application/json' \
     -d '{"prompt": "what are your hours?"}'
```

**Streaming** — if the model supports it, tokens arrive incrementally as
`brain.token_streamed` events, which you can forward to the browser as
server-sent events.

**Observability** — every request publishes events to `app.events`. Record them
all with an `EventRecorder` and expose a dashboard:

```python
from xyberos.events import EventRecorder

recorder = EventRecorder(limit=10_000).subscribe_to(bot.events)
# ...after some traffic...
print(recorder.counts())   # {'brain.response_produced': 12, ...}
```

## 11. Harden it for production

A real service retries transient failures, times out, and never says anything
harmful. All of this is configuration:

```python
from xyberos import create_app

app = create_app(config={
    "brain.max_attempts": 3,     # retry transient LLM failures
    "brain.retry_backoff": 0.2,  # wait (exponential) before retrying
    "brain.timeout": 60,         # seconds per LLM call
    "brain.rate_limit": 10,      # max LLM calls per second
    "security.audit_path": "audit.db",  # log every security event to disk
})
```

**Kill switch** — halt the whole bot instantly (e.g. for an emergency):

```python
app.security.engage_kill_switch("emergency maintenance")
app.chat("hello")            # raises SecurityHaltError
app.security.disengage_kill_switch()
app.chat("hello")            # works again
```

**Guardrails** — block harmful prompts:

```python
from xyberos import Guardrail

app.security.add_guardrail(
    Guardrail("no-hacks", lambda ctx: "hack" not in ctx.prompt)
)
```

---

# Part 3 — The full picture & next steps

## 12. How it all fits together

By now your assistant has every capability. Here's what `app.chat("...")` does
with them, in order:

1. **Workflow** — any pre-steps run; a step that sets the response short-circuits.
2. **Memory** — past turns are added as conversation history.
3. **Knowledge** — matching facts are injected into the prompt.
4. **Intent / Plan** — the request is classified and a plan is computed.
5. **Router / Tools** — a confident cheap tier (or a tool) may answer first.
6. **LLM** — only the novel tail reaches the model; its answer is cached.
7. **Memory** — the completed turn is stored for next time.

You can observe the memory behavior directly:

```python
from xyberos import create_app

app = create_app()
app.chat("hello")
app.chat("what did I just say?")

for entry in app.memory.retrieve(None):
    print(entry.prompt, "->", entry.response)
```

## 13. More building blocks

Quick looks at a few more subsystems, all covered in the
[API reference](api-reference.md) and [Extending Xyberos](extensions.md).

**Plugins & auto-discovery** — extend the kernel by registering services, and
let modules register themselves with zero wiring:

```python
from xyberos import create_app
from xyberos.contracts import Plugin

class GreetingPlugin(Plugin):
    name = "greeting"
    def register(self, kernel):
        kernel.register("greeting", "hello from plugin")

app = create_app()
app.load_plugin(GreetingPlugin())
print(app.resolve("greeting"))       # hello from plugin

# app.load_plugins_from("app.plugins")   # convention scan
# app.load_entry_points()                # installed entry points
```

**Structured outputs** — parse LLM text into data, or it raises
`StructuredOutputError`:

```python
from xyberos.llm import structured

data = structured(app.llm, "Return JSON: {'city': 'Paris'}")   # -> {'city': 'Paris'}
```

**LLM-driven planning** — ask the model to break a request into ordered steps
(recorded on `context.plan`):

```python
from xyberos import create_app
from xyberos.planner import LLMPlanner
from xyberos.llm import CallableLLM

app = create_app(
    config={"brain.inject_plan": True},   # optional: feed the plan to the model
    planner=LLMPlanner(CallableLLM(lambda p: "research\ndraft\nreview")),
)
print(app.run("build a report").plan)      # ['research', 'draft', 'review']
```

## 14. Take it further

- **Run the finished example.** The repo ships a complete, runnable version of
  exactly this app — a FastAPI support assistant with order lookup, refund
  approval, escalation, streaming, events, and hardening — in
  [`examples/support_assistant/`](https://github.com/xyberos/xyberos/blob/main/examples/support_assistant/README.md).
  Try its zero-setup smoke test (`python smoke_test.py`).
- **Make it learn.** Turn successful conversations into training data and let
  the bot improve over time — see the [Training Tutorial](training-tutorial.md).
- **Extend it.** Every subsystem is a plugin surface. See
  [Extending Xyberos](extensions.md) and the [API reference](api-reference.md).

---

# Appendix

## Glossary

| Term | Meaning |
|---|---|
| **App** | A fully-wired Xyberos instance — `create_app()` gives you one. |
| **Brain** | The orchestrator that runs the automated pipeline for each request. |
| **LLM** | The model. Duck-typed: anything with `generate(prompt) -> str` works. |
| **Embedder** | Anything with `embed(text) -> list[float]`; powers semantic matching. |
| **Memory** | Conversation history injected into the prompt. |
| **Knowledge** | Facts injected into the prompt. |
| **Tool** | A named capability the bot can act on. |
| **Workflow** | An ordered process that can pause for human input. |
| **Agent** | A named participant that processes a context; agents can hand off. |
| **Router** | Picks the cheapest confident tier to answer a request. |
| **Event** | A pub/sub notification fired as the pipeline runs. |

## Common gotchas

- **Semantic matching needs a real embedder.** The default `HashEmbedder` only
  matches near-identical text. Pass `embedder=` (e.g. `OllamaEmbeddingLLM` or
  `SentenceTransformerEmbedder`) for paraphrase matching.
- **SQLite files are written next to your script** (`chat.db`, `facts.db`,
  `runs.db`, `learning.db`). Keep them out of git or pass explicit paths.
- **`create_semantic_app` is persistent by default** (`learning.db`) — it
  accumulates learned facts and cache across runs. Pass `store=CosineVectorStore()`
  for a clean in-memory session in demos and tests.
- **The brain captures providers at construction.** Replace a provider after
  `create_app()`? Create a fresh app instead.
- **Don't call the LLM for every request.** Teach the cache with the hybrid
  router and watch LLM calls drop.

## The whole app in one file

Here's the complete support assistant — every step above, together:

```python
from xyberos import create_app
from xyberos.agents import RoleAgent, handoff, post
from xyberos.exceptions import WorkflowPaused
from xyberos.knowledge import SqliteKnowledge
from xyberos.llm import OllamaLLM
from xyberos.memory import SqliteMemory
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import FunctionTool, ToolRegistry
from xyberos.workflows import GraphWorkflow

# --- model (needs `ollama pull llama3.2`; swap in CallableLLM to go offline) --
llm = OllamaLLM(model="llama3.2")

# --- facts + history -------------------------------------------------------
knowledge = SqliteKnowledge("facts.db")
knowledge.add("hours", "Support is available 9am-6pm Mon-Fri.")
knowledge.add("refund", "Refunds are processed within 5-7 business days.")

app = create_app(llm=llm, memory=SqliteMemory("chat.db"), knowledge=knowledge)

# --- tools -----------------------------------------------------------------
ORDERS = {"A-100": "shipped", "B-300": "processing"}

def lookup_order(order_id: str = "unknown") -> str:
    return f"Order {order_id} status: {ORDERS.get(order_id.upper(), 'not found')}"

def open_ticket() -> str:
    return "A support ticket has been opened (ticket #T-1001)."

registry = ToolRegistry([
    FunctionTool("lookup_order", lookup_order, description="Look up an order's status"),
    FunctionTool("open_ticket", open_ticket, description="Open a new support ticket"),
])

# --- human-in-the-loop refund workflow -------------------------------------
refund = GraphWorkflow("verify")

def verify(context):
    if GraphWorkflow.RESUME_KEY in context.metadata:
        decision = context.metadata[GraphWorkflow.RESUME_KEY]
        context.response = "approved" if decision == "yes" else "rejected"
        return context
    raise WorkflowPaused(prompt="Approve this refund? Reply yes or no.")

refund.add_node("verify", verify)

# --- escalation agents -----------------------------------------------------
def supervisor_run(context):
    post(context, handoff("support_worker", sender="supervisor"))
    return context

def worker_run(context):
    context.response = "Escalated: a human agent will follow up."
    return context

app.register_agent(RoleAgent("supervisor", "triage", run=supervisor_run))
app.register_agent(RoleAgent("support_worker", "resolver", run=worker_run))

# --- use it ----------------------------------------------------------------
print(app.chat("what are your hours?"))                                      # knowledge
print(registry.execute("lookup_order", CognitiveContext("o"), order_id="A-100"))  # tool
run = refund.execute(CognitiveContext("refund A-100"))                       # workflow pauses
print(run.status, run.prompt)
print(refund.resume(run, "yes").context.response)                            # approved
print(app.run_agents("help", agent_names=["supervisor", "support_worker"]).response)
```

> The full, production-shaped version of this file — FastAPI server, streaming,
> events, checkpointing across restarts — is in
> [`examples/support_assistant/`](https://github.com/xyberos/xyberos/blob/main/examples/support_assistant/README.md).

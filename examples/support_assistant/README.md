# Xyberos Support Assistant

A runnable FastAPI service built on the current Xyberos API. It exercises every
subsystem with a real (local) model:

- **LLM** — `OllamaLLM` (local Ollama server, stdlib HTTP), with a deterministic
  `XYBEROS_MODEL=echo` fallback so it runs without a model server.
- **Memory** — `SqliteMemory` conversation history, survives restarts.
- **Knowledge** — `SqliteKnowledge` facts (hours, billing, refund policy).
- **Planner** — `LLMPlanner` derives an ordered plan per request.
- **Tools** — typed `FunctionTool`s (`lookup_order`, `open_ticket`) called
  explicitly from the request handlers.
- **Workflows** — a `GraphWorkflow` refund flow that **pauses for human
  approval** and is checkpointed to SQLite across restarts.
- **Agents** — a supervisor `RoleAgent` that hands off to a support worker.
- **Async** — `/chat` awaits `app.achat`.
- **Streaming** — `/stream/{prompt}` streams model tokens as server-sent events.
- **Observability** — an `EventRecorder` powers `/events`.
- **Hardening** — retries, backoff, and timeouts via `Config`.

## Run

```bash
pip install -e ../..              # install the Xyberos core (no runtime deps)
pip install -r requirements.txt   # fastapi + uvicorn for the server
uvicorn app.main:app --reload     # from this directory
```

> Requires a local [Ollama](https://ollama.com) server for real responses
> (default model `llama3.2`). To run without one, set `XYBEROS_MODEL=echo` —
> the app then uses a deterministic provider so every endpoint works offline.

## Endpoints

| Method | Path | Body | What it demonstrates |
|---|---|---|---|
| GET | `/health` | — | model + status |
| POST | `/chat` | `{"prompt": "..."}` | full automated pipeline (async); order ids are handled by the typed tool |
| GET | `/events` | — | `EventRecorder` per-event counts |
| POST | `/refund` | `{"prompt": "..."}` | start a human-in-the-loop refund (pauses) |
| POST | `/refund/{run_id}/approve` | `{"decision": "yes"\|"no"}` | resume the paused workflow |
| POST | `/escalate` | `{"prompt": "..."}` | supervisor → worker handoff |
| GET | `/stream/{prompt}` | — | SSE of streamed tokens (needs a streaming model) |

## Try it

```bash
curl -X POST localhost:8000/chat -H 'Content-Type: application/json' \
     -d '{"prompt": "what are your hours?"}'

curl -X POST localhost:8000/refund -H 'Content-Type: application/json' \
     -d '{"prompt": "refund A-100"}'
# -> {"run_id": "...", "status": "paused", "prompt": "Approve this refund? Reply yes or no."}

curl -X POST localhost:8000/refund/<run_id>/approve -H 'Content-Type: application/json' \
     -d '{"decision": "yes"}'
# -> {"status": "completed", "response": "approved"}

curl -N localhost:8000/stream/tell me a haiku
```

## Data

SQLite files (`chat.db`, `facts.db`, `runs.db`) are written to
`examples/support_assistant/data/` (override with `XYBEROS_DATA_DIR`).

## Smoke test

No server, no model, no network needed:

```bash
python smoke_test.py
```

"""FastAPI server for the Xyberos support assistant.

Run (requires a local Ollama server for real models, or set ``XYBEROS_MODEL=echo``):

    pip install -r requirements.txt
    uvicorn app.main:app --reload

Endpoints:
    GET  /health                    model + status
    POST /chat                      {prompt} -> full automated pipeline (async)
    GET  /events                    EventRecorder counts
    POST /refund                    {prompt} -> start a human-in-the-loop refund
    POST /refund/{run_id}/approve   {decision: yes|no} -> resume the refund
    POST /escalate                  {prompt} -> supervisor -> worker handoff
    GET  /stream/{prompt}           SSE of streamed tokens (needs a streaming model)
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, cast

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from xyberos.events import TOKEN_STREAMED
from xyberos.runtime.context import CognitiveContext

from .assistant import build_app, extract_order_id

app = FastAPI(title="Xyberos Support Assistant")
xyberos_app = build_app()


class ChatRequest(BaseModel):
    prompt: str


class RefundDecision(BaseModel):
    decision: str


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "model": getattr(xyberos_app.llm, "_model", "echo")}


@app.post("/chat")
async def chat(request: ChatRequest) -> dict[str, Any]:
    """Run the full pipeline. Order lookups are handled by the typed tool."""
    prompt = request.prompt
    order_id = extract_order_id(prompt)
    if order_id is not None:
        registry = cast(Any, xyberos_app).tool_registry
        response = registry.execute(
            "lookup_order", CognitiveContext(prompt), order_id=order_id
        )
        return {
            "response": response,
            "tool": "lookup_order",
            "plan": None,
            "facts": {},
            "memory_len": len(xyberos_app.memory.retrieve(None)),
        }

    context = await xyberos_app.arun(prompt, metadata={"user": "web"})
    return {
        "response": context.response,
        "plan": context.plan,
        "facts": xyberos_app.knowledge.query(context),
        "memory_len": len(xyberos_app.memory.retrieve(None)),
        "response_events": cast(Any, xyberos_app).recorder.count_for("brain.response_produced"),
    }


@app.get("/events")
def events() -> dict[str, Any]:
    return {"counts": cast(Any, xyberos_app).recorder.counts()}


@app.post("/refund")
def start_refund(request: ChatRequest) -> dict[str, Any]:
    """Start a refund request; it pauses awaiting human approval."""
    app_untyped = cast(Any, xyberos_app)
    run = app_untyped.refund_graph.execute(CognitiveContext(request.prompt))
    if run.status == "paused":
        run_id = uuid.uuid4().hex
        app_untyped.refund_checkpoint.save(run_id, run)
        return {"run_id": run_id, "status": "paused", "prompt": run.prompt}
    return {"run_id": None, "status": run.status, "response": run.context.response}


@app.post("/refund/{run_id}/approve")
def approve_refund(run_id: str, decision: RefundDecision) -> dict[str, Any]:
    """Resume a paused refund with a human decision (yes/no)."""
    app_untyped = cast(Any, xyberos_app)
    try:
        run = app_untyped.refund_graph.resume_from_checkpoint(
            app_untyped.refund_checkpoint, run_id, decision.decision
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": run.status, "response": run.context.response}


@app.post("/escalate")
def escalate(request: ChatRequest) -> dict[str, Any]:
    """Supervisor hands off to a support worker (multi-agent collaboration)."""
    context = xyberos_app.agents.run(
        CognitiveContext(request.prompt),
        agent_names=["supervisor", "support_worker"],
    )
    return {
        "response": context.response,
        "handoffs": [
            {"from": m.sender, "to": m.recipient, "kind": m.kind}
            for m in xyberos_app.agents.messages
        ],
    }


@app.get("/stream/{prompt}")
async def stream(prompt: str) -> StreamingResponse:
    """Server-sent-events of tokens streamed by the model."""
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def on_token(event: Any) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, event.data["token"])

    subscriber = xyberos_app.events.subscribe(TOKEN_STREAMED, on_token)

    async def consume() -> None:
        await asyncio.to_thread(xyberos_app.chat, prompt)
        await queue.put(None)  # sentinel

    async def generate():
        consumer = asyncio.create_task(consume())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield f"data: {item}\n\n"
        finally:
            consumer.cancel()
            xyberos_app.events.unsubscribe(TOKEN_STREAMED, subscriber)

    return StreamingResponse(generate(), media_type="text/event-stream")

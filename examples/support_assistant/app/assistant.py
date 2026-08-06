"""Wiring for the support assistant — the core layer only (no web framework).

``build_app`` returns a fully-wired :class:`~xyberos.Xyberos` instance that
exercises every subsystem: SQLite memory/knowledge, typed tools, LLM-driven
planning, a human-in-the-loop refund workflow, multi-agent escalation, event
observability, and config-driven hardening.
"""

from __future__ import annotations

import os
import re
from typing import Any, cast

from xyberos import create_app
from xyberos.agents import RoleAgent, handoff, post
from xyberos.events import EventRecorder
from xyberos.exceptions import WorkflowPaused
from xyberos.knowledge import SqliteKnowledge
from xyberos.llm import CallableLLM, OllamaLLM
from xyberos.memory import SqliteMemory
from xyberos.planner import LLMPlanner
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import FunctionTool, ToolRegistry
from xyberos.workflows import GraphWorkflow, WorkflowCheckpoint


HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.getenv(
    "XYBEROS_DATA_DIR", os.path.join(os.path.dirname(HERE), "data")
)

ORDER_RE = re.compile(r"\b([A-Z]-?\d+)\b", re.IGNORECASE)
ORDERS = {"A-100": "shipped", "A-200": "delivered", "B-300": "processing"}


def lookup_order(order_id: str = "unknown") -> str:
    """Look up the status of an order by id."""
    status = ORDERS.get(order_id.upper(), "not found")
    return f"Order {order_id} status: {status}"


def open_ticket() -> str:
    """Open a new support ticket."""
    return "A support ticket has been opened (ticket #T-1001)."


def build_llm(model: str | None = None):
    """Build the LLM: an Ollama model by default, or a deterministic echo.

    ``model="echo"`` (or ``XYBEROS_MODEL=echo``) uses a deterministic local
    provider so the app runs without a model server.
    """
    model = model or os.getenv("XYBEROS_MODEL", "qwen2.5:1.5b")
    if model == "echo":
        return CallableLLM(lambda prompt: f"[support] {prompt}")
    return OllamaLLM(model=model, base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"))


def build_app(model: str | None = None, *, data_dir: str = DEFAULT_DATA_DIR):
    """Build a fully-wired Xyberos support-assistant application."""
    os.makedirs(data_dir, exist_ok=True)
    llm = build_llm(model)

    knowledge = SqliteKnowledge(os.path.join(data_dir, "facts.db"))
    knowledge.add("hours", "Support is available 9am-6pm Mon-Fri.")
    knowledge.add("billing", "Billing questions go to billing@example.com.")
    knowledge.add("refund", "Refunds are processed within 5-7 business days.")

    app = create_app(
        config={
            "logger_name": "support_assistant",
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "brain.max_attempts": 2,
            "brain.retry_backoff": 0.2,
            "brain.timeout": 60,
        },
        llm=llm,
        memory=SqliteMemory(os.path.join(data_dir, "chat.db")),
        knowledge=knowledge,
        planner=LLMPlanner(llm),
    )

    # Observability: record every event for the /events endpoint.
    cast(Any, app).recorder = EventRecorder(limit=10_000).subscribe_to(app.events)

    # Typed tools, called explicitly from the request handlers (tool selection
    # here is intent-based rather than the built-in prompt-name heuristic).
    cast(Any, app).tool_registry = ToolRegistry(
        [
            FunctionTool("lookup_order", lookup_order, description="Look up an order's status"),
            FunctionTool("open_ticket", open_ticket, description="Open a new support ticket"),
        ]
    )

    # Human-in-the-loop refund workflow, checkpointed across restarts.
    refund_graph = GraphWorkflow("verify")

    def verify(context: CognitiveContext):
        if GraphWorkflow.RESUME_KEY in context.metadata:
            decision = context.metadata[GraphWorkflow.RESUME_KEY]
            context.response = "approved" if decision == "yes" else "rejected"
            return context
        raise WorkflowPaused(prompt="Approve this refund? Reply yes or no.")

    refund_graph.add_node("verify", verify)
    cast(Any, app).refund_graph = refund_graph
    cast(Any, app).refund_checkpoint = WorkflowCheckpoint(os.path.join(data_dir, "runs.db"))

    # Multi-agent escalation: a supervisor hands off to a support worker.
    def supervisor_run(context: CognitiveContext):
        post(context, handoff("support_worker", sender="supervisor"))
        return context

    def worker_run(context: CognitiveContext):
        context.response = f"Escalated: a human agent will follow up on '{context.prompt}'."
        return context

    app.register_agent(RoleAgent("supervisor", "triage", run=supervisor_run))
    app.register_agent(RoleAgent("support_worker", "resolver", run=worker_run))

    return app


def extract_order_id(prompt: str) -> str | None:
    """Return an order id referenced in ``prompt`` (e.g. ``A-100``), if any."""
    match = ORDER_RE.search(prompt)
    return match.group(1) if match else None

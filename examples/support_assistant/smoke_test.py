"""Smoke test for the support assistant — exercises every subsystem.

Run:  python examples/support_assistant/smoke_test.py

Uses the deterministic "echo" model and a temp data directory, so it needs no
Ollama server and no network. If httpx is installed, the FastAPI endpoints are
exercised too via TestClient.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DATA = tempfile.mkdtemp(prefix="xyberos_support_")
os.environ["XYBEROS_DATA_DIR"] = DATA
os.environ["XYBEROS_MODEL"] = "echo"  # deterministic, no server needed

from xyberos.runtime.context import CognitiveContext  # noqa: E402

from app.assistant import build_app, extract_order_id  # noqa: E402

app = build_app(model="echo", data_dir=DATA)


def check(label: str, condition: bool) -> None:
    if not condition:
        raise SystemExit(f"FAILED: {label}")
    print(f"ok: {label}")


# 1. Automated pipeline: memory, knowledge, planner, and LLM.
app.chat("hello")
context = app.run("what are your hours?")
check("memory stores turns", len(app.memory.retrieve(None)) == 2)
check("history recalled", "hello" in context.response)
check("plan recorded", context.plan is not None)
check("knowledge matches prompt", "hours" in app.knowledge.query(context))
check("response produced", context.response is not None)

# 2. Typed tools (explicit invocation).
order_id = extract_order_id("what is the status of A-100?")
check("order id extracted", order_id == "A-100")
tool_response = app.tool_registry.execute("lookup_order", context, order_id=order_id)
check("typed tool result", tool_response == "Order A-100 status: shipped")

# 3. Human-in-the-loop refund workflow (checkpointed).
run = app.refund_graph.execute(CognitiveContext("refund A-100"))
check("refund pauses", run.status == "paused")
check("refund asks for approval", run.prompt == "Approve this refund? Reply yes or no.")
app.refund_checkpoint.save("smoke-yes", run)
resumed = app.refund_graph.resume_from_checkpoint(app.refund_checkpoint, "smoke-yes", "yes")
check("refund approved", resumed.status == "completed" and resumed.context.response == "approved")

run_no = app.refund_graph.execute(CognitiveContext("refund B-300"))
app.refund_checkpoint.save("smoke-no", run_no)
rejected = app.refund_graph.resume_from_checkpoint(app.refund_checkpoint, "smoke-no", "no")
check("refund rejected", rejected.context.response == "rejected")

# 4. Multi-agent escalation (supervisor -> worker handoff).
escalated = app.agents.run(
    CognitiveContext("billing dispute"), agent_names=["supervisor", "support_worker"]
)
check("agent handoff response", escalated.response.startswith("Escalated"))
check("handoff recorded", any(m.kind == "handoff" for m in app.agents.messages))

# 5. Observability.
check("events recorded", app.recorder.count > 0)

# 6. FastAPI endpoints (only when httpx is available).
if importlib.util.find_spec("httpx") is not None:
    from fastapi.testclient import TestClient  # noqa: E402

    from app.main import app as web_app  # noqa: E402

    client = TestClient(web_app)
    check("health", client.get("/health").json()["status"] == "ok")
    chat = client.post("/chat", json={"prompt": "status of A-100"}).json()
    check("chat tool", chat["tool"] == "lookup_order" and "shipped" in chat["response"])
    refund = client.post("/refund", json={"prompt": "refund A-200"}).json()
    check("refund paused via api", refund["status"] == "paused")
    approved = client.post(
        f"/refund/{refund['run_id']}/approve", json={"decision": "yes"}
    ).json()
    check("refund approved via api", approved["response"] == "approved")
    escalate = client.post("/escalate", json={"prompt": "help"}).json()
    check("escalate via api", escalate["response"].startswith("Escalated"))
    event_counts = client.get("/events").json()["counts"]
    check("events endpoint", event_counts.get("brain.response_produced", 0) >= 1)
else:
    print("skipping FastAPI endpoint checks (httpx not installed)")

print("\nSupport assistant smoke test passed.")

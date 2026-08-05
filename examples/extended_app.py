"""End-to-end walkthrough of the Xyberos application API.

Run:  python examples/extended_app.py
"""

import asyncio
from typing import Any

from xyberos import create_app
from xyberos.agents import RoleAgent, handoff, post
from xyberos.contracts import Agent, Plugin, Tool
from xyberos.events import RESPONSE_PRODUCED, EventRecorder
from xyberos.exceptions import WorkflowPaused
from xyberos.kernel.kernel import Kernel
from xyberos.knowledge import InMemoryKnowledge
from xyberos.memory import InMemoryMemory
from xyberos.planner import SequentialPlanner
from xyberos.llm import AsyncLLM, CallableLLM, structured
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import FunctionTool, ToolRegistry
from xyberos.workflows import GraphWorkflow, SequentialWorkflow


class GreetingPlugin(Plugin):
    @property
    def name(self) -> str:
        return "greeting"

    def register(self, kernel: object) -> None:
        if not isinstance(kernel, Kernel):
            return
        kernel.register("greeting", "hello")

    def unregister(self, kernel: object) -> None:
        if not isinstance(kernel, Kernel):
            return
        kernel.registry.unregister("greeting")


class UppercaseTool(Tool):
    @property
    def name(self) -> str:
        return "uppercase"

    def execute(self, context: object, **arguments: Any):
        if not isinstance(context, CognitiveContext):
            return ""
        return context.prompt.upper()


class AuditAgent(Agent):
    @property
    def name(self) -> str:
        return "audit"

    def run(self, context: object) -> object:
        if not isinstance(context, CognitiveContext):
            return context
        context.metadata.setdefault("agents", []).append("audited")
        return context


def step_validate(context: CognitiveContext) -> None:
    context.metadata.setdefault("steps", []).append("validated")


def main() -> None:
    # 1. Default app (EchoLLM) and custom model.
    app = create_app()
    print("1) chat (echo):", app.chat("hello world"))
    app = create_app(llm=CallableLLM(lambda prompt: f"handled: {prompt}"))
    print("   chat (custom):", app.chat("hi"))

    # 2. Service registry + dependency injection.
    app.register("custom_greeting", "hello-from-service")
    print("2) resolve:", app.resolve("custom_greeting"))
    print("   inject:", app.inject(lambda custom_greeting: custom_greeting))

    # 3. Multi-agent runtime.
    app.register_agent(AuditAgent())
    result = app.run_agents("multi", metadata={"request": "1"})
    print("3) run_agents:", result.response, result.metadata)

    # 4. Plugins.
    app.load_plugin(GreetingPlugin())
    print("4) plugin:", app.resolve("greeting"))
    app.unload_plugin("greeting")

    # 5. Workflow.
    workflow = SequentialWorkflow([step_validate])
    wf_result = workflow.run(CognitiveContext("wf"))
    print("5) workflow:", wf_result.metadata)

    # 6. Providers.
    memory = InMemoryMemory()
    memory.store(CognitiveContext("remember"))
    print("6) memory:", memory.retrieve(None))

    knowledge = InMemoryKnowledge({"kernel": "core"})
    print("   knowledge:", knowledge.query(CognitiveContext("kernel")))

    planner = SequentialPlanner(("analyze", "do"))
    print("   plan:", planner.plan(CognitiveContext("task")))

    tools = ToolRegistry([UppercaseTool()])
    print("   tool:", tools.execute("uppercase", CognitiveContext("tool")))

    # 7. Events and observability.
    responses: list[str] = []
    recorder = EventRecorder(limit=100).subscribe_to(app.events)
    app.events.subscribe(RESPONSE_PRODUCED, lambda e: responses.append(e.data["response"]))
    app.chat("hello")
    print("7) events:", recorder.count, "recorded; response event:", responses)

    # 8. State graph with human-in-the-loop.
    graph = GraphWorkflow("ask")

    def ask(context: CognitiveContext) -> CognitiveContext | None:
        if GraphWorkflow.RESUME_KEY in context.metadata:
            context.response = "approved"
            return context
        raise WorkflowPaused(prompt="Approve the action?")

    graph.add_node("ask", ask)
    run = graph.execute(CognitiveContext("task"))
    run = graph.resume(run, "yes")
    print("8) graph:", run.status, run.context.response)

    # 9. Multi-agent collaboration (handoff + roles).
    def boss(context: CognitiveContext) -> CognitiveContext:
        post(context, handoff("worker", sender="boss"))
        return context

    def worker(context: CognitiveContext) -> CognitiveContext:
        context.response = "worked"
        return context

    app = create_app()
    app.register_agent(RoleAgent("boss", "supervisor", run=boss))
    app.register_agent(RoleAgent("worker", "performer", run=worker))
    result = app.run_agents("task", agent_names=["boss", "worker"])
    print("9) agents:", result.response, [m.sender + "->" + m.recipient for m in app.agents.messages])

    # 10. Structured output and a typed function tool.
    data = structured(CallableLLM(lambda prompt: '{"city": "Paris"}'), "where?")

    def search(query: str, limit: int = 10) -> str:
        return f"search({query}, limit={limit})"

    tool = FunctionTool("search", search)
    print("10) structured:", data, "| tool:", tool.execute(None, query="x", limit="5"))

    # 11. Async chat.
    async def agenerate(prompt: str) -> str:
        return f"async:{prompt}"

    app = create_app(llm=AsyncLLM(agenerate))
    print("11) async:", asyncio.run(app.achat("hello")))

    # 12. Production hardening (retry via config).
    attempts: list[int] = []

    def flaky(prompt: str) -> str:
        attempts.append(1)
        if len(attempts) < 3:
            raise RuntimeError("transient")
        return "ok"

    app = create_app(
        config={"brain.max_attempts": 3, "brain.retry_backoff": 0},
        llm=CallableLLM(flaky),
    )
    print("12) retry:", app.chat("hi"), "| attempts:", len(attempts))


if __name__ == "__main__":
    main()

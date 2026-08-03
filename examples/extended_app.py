"""End-to-end walkthrough of the Xyberos application API.

Run:  python examples/extended_app.py
"""

from xyberos import create_app
from xyberos.brain.llm import CallableLLM
from xyberos.contracts import Agent, Plugin, Tool
from xyberos.knowledge import InMemoryKnowledge
from xyberos.memory import InMemoryMemory
from xyberos.planner import SequentialPlanner
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import ToolRegistry
from xyberos.workflows import SequentialWorkflow


class GreetingPlugin(Plugin):
    @property
    def name(self) -> str:
        return "greeting"

    def register(self, kernel) -> None:
        kernel.register("greeting", "hello")

    def unregister(self, kernel) -> None:
        kernel.registry.unregister("greeting")


class UppercaseTool(Tool):
    @property
    def name(self) -> str:
        return "uppercase"

    def execute(self, context, **arguments):
        return context.prompt.upper()


class AuditAgent(Agent):
    @property
    def name(self) -> str:
        return "audit"

    def run(self, context):
        context.metadata.setdefault("agents", []).append("audited")
        return context


def step_validate(context) -> None:
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


if __name__ == "__main__":
    main()

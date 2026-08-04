"""Hello world to full stack: a single runnable Xyberos mini-app.

Run:
    python examples/hello_world_to_full_stack/app.py

Every stage builds on the previous one and prints its own output, so you can
watch the framework grow from a one-liner into a small full-stack app. The
final stage composes everything into one coherent "support assistant".
"""

from collections.abc import Mapping
from typing import Any, cast

from xyberos import Xyberos, chat, create_app
from xyberos.contracts import Agent, Plugin, Tool
from xyberos.kernel.kernel import Kernel
from xyberos.knowledge import InMemoryKnowledge
from xyberos.llm import CallableLLM
from xyberos.memory import InMemoryMemory
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import ToolRegistry, ToolRunner
from xyberos.workflows import SequentialWorkflow


def banner(title: str) -> None:
    """Print a section header so each stage's output is easy to follow."""
    print("\n" + "=" * 64)
    print(title)
    print("=" * 64)


# ---------------------------------------------------------------------------
# Reusable building blocks for the final "full stack" stage.
# ---------------------------------------------------------------------------


class RefundTool(Tool):
    """Answers refund questions directly instead of calling the model."""

    @property
    def name(self) -> str:
        return "refund"

    def execute(self, context: object, **arguments: Any):
        return "refund: Your refund request has been created (ticket #101)."


class AuditAgent(Agent):
    """Adds an audit marker to the context metadata on every pass."""

    @property
    def name(self) -> str:
        return "audit"

    def run(self, context: object) -> object:
        if not isinstance(context, CognitiveContext):
            return context
        context.metadata.setdefault("audits", []).append("checked")
        return context


class SupportPlugin(Plugin):
    """Registers a support-hours service with the kernel."""

    @property
    def name(self) -> str:
        return "support"

    def register(self, kernel: object) -> None:
        if not isinstance(kernel, Kernel):
            return
        kernel.register("support_hours", "9am-6pm Mon-Fri")

    def unregister(self, kernel: object) -> None:
        if not isinstance(kernel, Kernel):
            return
        kernel.registry.unregister("support_hours")


def add_disclaimer(context: CognitiveContext) -> None:
    """A workflow step that stamps the response with a disclaimer."""
    context.metadata["disclaimer"] = "demo only"


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------


def stage_hello_world() -> None:
    banner("Stage 0 - Hello world")
    # create_app() wires up a complete app using the default EchoLLM.
    app = create_app()
    print("app.chat :", app.chat("Hello, Xyberos!"))

    # The module-level helper is the one-liner version of the same thing.
    print("chat()   :", chat("Hello again"))


def stage_custom_model() -> None:
    banner("Stage 1 - Swap in a custom model")
    app = create_app(llm=CallableLLM(lambda prompt: f"model: {prompt}"))
    print("custom   :", app.chat("hi"))

    # The facade class works the same way if you prefer direct construction.
    direct = Xyberos(llm=CallableLLM(lambda prompt: f"direct: {prompt}"))
    print("direct   :", direct.chat("hi"))


def stage_config_and_services() -> None:
    banner("Stage 2 - Configuration, services and dependency injection")
    app = create_app(config={"logger_name": "example.full_stack", "log_level": "INFO"})
    print("config   :", app.config.get("logger_name"))

    app.register("answer", 42)  # register a plain service
    print("resolve  :", app.resolve("answer"))

    def build_message(config: Mapping[str, Any]) -> str:
        return f"built with {config.get('logger_name')}"

    app.register_factory("message", build_message)
    print("factory  :", app.resolve("message"))

    # inject() builds any callable from registered services.
    def double(answer: int) -> int:
        return answer * 2

    print("inject   :", app.inject(double))  # 84


def stage_memory() -> None:
    banner("Stage 3 - Memory provider")
    memory = InMemoryMemory()
    memory.store(CognitiveContext("first request"))
    memory.store(CognitiveContext("second request"))
    print("stored   :", len(memory.retrieve(None)), "contexts")


def stage_knowledge() -> None:
    banner("Stage 4 - Knowledge provider")
    knowledge = InMemoryKnowledge(
        {"kernel": "platform services", "brain": "response generation"}
    )
    print("query    :", knowledge.query(CognitiveContext("what does the kernel do")))


def stage_tools() -> None:
    banner("Stage 5 - Tools")
    tools = ToolRegistry([RefundTool()])
    print("names    :", tools.names)
    print("execute  :", tools.execute("refund", CognitiveContext("I want a refund")))


def stage_tool_runner() -> None:
    banner("Stage 6 - Tool runner (name-based dispatch)")
    runner = ToolRunner([RefundTool()])
    # "refund" appears in the prompt, so the runner selects that tool.
    print("dispatch :", runner.dispatch(CognitiveContext("I want a refund")))
    # No tool name matches, so the heuristic falls back to the first tool.
    print("fallback :", runner.dispatch(CognitiveContext("hello")))


def stage_workflow() -> None:
    banner("Stage 7 - Workflow")
    workflow = SequentialWorkflow([add_disclaimer])
    result = workflow.run(CognitiveContext("request"))
    print("metadata :", result.metadata)


def stage_agents() -> None:
    banner("Stage 8 - Agents")
    app = create_app(llm=CallableLLM(lambda prompt: f"model: {prompt}"))
    app.register_agent(AuditAgent())
    result = app.run_agents("hello", agent_names=["audit", "default"])
    print("response :", result.response)
    print("metadata :", result.metadata)


def stage_plugins() -> None:
    banner("Stage 9 - Plugins")
    app = create_app()
    app.load_plugin(SupportPlugin())
    print("service  :", app.resolve("support_hours"))
    app.unload_plugin("support")
    try:
        app.resolve("support_hours")
    except Exception as exc:  # noqa: BLE001 - showing the service is now gone
        print("after unload:", type(exc).__name__)


def stage_full_stack() -> None:
    banner("Stage 10 - Full stack: a support assistant")

    # One app, one script, every layer working together.
    app = create_app(llm=CallableLLM(lambda prompt: f"assistant: {prompt}"))

    memory = app.memory  # built-in InMemoryMemory
    knowledge = cast(InMemoryKnowledge, app.knowledge)
    knowledge.add("hours", "Support is available 9am-6pm Mon-Fri.")
    knowledge.add("billing", "Billing questions go to billing@example.com.")
    tools = app.tools  # the registry shared with the app's tool runner
    tools.register(RefundTool())
    app.load_plugin(SupportPlugin())  # contributes the support_hours service
    app.register_agent(AuditAgent())  # runs on every request

    def assist(prompt: str) -> CognitiveContext:
        context = CognitiveContext(prompt=prompt)
        memory.store(context)  # 1. remember the request

        # 2. A tool answers directly when the prompt names it...
        tool_name = next((name for name in tools.names if name in prompt), None)
        # 3. ...otherwise the model generates a response.
        response = tools.execute(tool_name, context) if tool_name else app.llm.generate(prompt)

        context.response = response

        # 4. A workflow and an agent post-process the request.
        SequentialWorkflow([add_disclaimer]).run(context)
        app.agents.run(context, agent_names=["audit"])

        print(f"  prompt : {prompt}")
        print(f"  answer : {context.response}")
        print(f"  facts  : {knowledge.query(context)}")
        print(f"  meta   : {context.metadata}")
        print(f"  plugin : support_hours = {app.resolve('support_hours')}")
        return context

    assist("I need a refund")  # handled by the tool
    assist("What are your hours?")  # handled by the model + knowledge base


def main() -> None:
    stage_hello_world()
    stage_custom_model()
    stage_config_and_services()
    stage_memory()
    stage_knowledge()
    stage_tools()
    stage_tool_runner()
    stage_workflow()
    stage_agents()
    stage_plugins()
    stage_full_stack()


if __name__ == "__main__":
    main()

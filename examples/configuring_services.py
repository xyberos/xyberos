"""Three approaches to configuring services in Xyberos.

Run:  python examples/configuring_services.py

Shows how to wire up an LLM, tools, and knowledge using:
  Stage 1 — Explicit (pass instances to create_app / Xyberos)
  Stage 2 — Class/factory (register factories, kernel DI resolves them)
  Stage 3 — Plugin (auto-discovered via convention scan)
"""

from xyberos import Xyberos, create_app
from xyberos.contracts import Plugin, Tool
from xyberos.knowledge import InMemoryKnowledge
from xyberos.llm import CallableLLM


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------


def _banner(title: str) -> None:
    print("\n" + "=" * 56)
    print(title)
    print("=" * 56)


class UppercaseTool(Tool):
    """A tool that returns the prompt in uppercase."""

    @property
    def name(self) -> str:
        return "uppercase"

    def execute(self, context: object, **arguments: object):
        return context.prompt.upper() if hasattr(context, "prompt") else "NO PROMPT"


class KnowledgePlugin(Plugin):
    """Plugin that registers knowledge when auto-discovered."""

    @property
    def name(self) -> str:
        return "knowledge_plugin"

    def register(self, kernel: object) -> None:
        knowledge = InMemoryKnowledge({"hours": "9am-6pm", "support": "support@example.com"})
        kernel.register("custom_knowledge", knowledge, replace=True)

    def unregister(self, kernel: object) -> None:
        kernel.registry.unregister("custom_knowledge")


def _build_llm_from_config(config):
    """Factory: the kernel DI-injects config by name, so we can swap models."""
    provider = config.get("llm_provider", "echo")
    if provider == "echo":
        return CallableLLM(lambda p: f"[echo] {p}")
    return CallableLLM(lambda p: f"[{provider}] {p}")


# ---------------------------------------------------------------------------
# Stage 1 — Explicit: pass everything at construction time
# ---------------------------------------------------------------------------


def stage_explicit() -> None:
    _banner("1. Explicit — pass instances to create_app / Xyberos")

    # Via create_app (convenience — fills defaults for missing services)
    app = create_app(
        llm=CallableLLM(lambda p: f"response: {p}"),
        knowledge=InMemoryKnowledge({"greeting": "hello world"}),
    )
    print("chat  :", app.chat("say hello"))

    # Via Xyberos directly (full control — no defaults)
    manual = Xyberos(
        llm=CallableLLM(lambda p: f"custom: {p}"),
    )
    print("manual:", manual.chat("direct"))


# ---------------------------------------------------------------------------
# Stage 2 — Class / factory: register with the kernel, resolved via DI
# ---------------------------------------------------------------------------


def stage_factory() -> None:
    _banner("2. Factory — register a callable, kernel DI resolves it")

    app = create_app(config={"llm_provider": "openai"})

    # Register a factory keyed by name.  The kernel inspects the factory's
    # parameter names and resolves them from the registry (config, logger, …).
    app.register_factory("llm", _build_llm_from_config, replace=True)

    print("chat:", app.chat("test"))
    # Change config at runtime — re-resolve picks up the new value.
    app.config.set("llm_provider", "claude")
    resolved = app.resolve("llm")
    print("chat:", resolved.generate("test"))


# ---------------------------------------------------------------------------
# Stage 3 — Plugin: auto-discovered (convention scan or entry points)
# ---------------------------------------------------------------------------


def _fake_package_for_demo():
    """Create a throwaway package containing a plugin, so the demo is self-contained.

    In a real app you would place ``KnowledgePlugin`` inside an ``app/plugins/``
    package and call ``app.load_plugins_from("app.plugins")`` — no manual wiring.
    """
    import sys
    from types import ModuleType

    m = ModuleType("_demo_plugins")
    m.__path__ = ["_demo_plugins"]
    m.KnowledgePlugin = KnowledgePlugin
    sys.modules["_demo_plugins"] = m


def stage_plugin() -> None:
    _banner("3. Plugin — auto-discovered by convention scan")

    _fake_package_for_demo()

    app = create_app()

    # Convention scan: walks the package and loads every Plugin subclass.
    app.load_plugins_from("_demo_plugins")

    # The plugin's services are now registered — resolve and query.
    from xyberos.runtime.context import CognitiveContext

    knowledge = app.resolve("custom_knowledge")
    print("query hours :", knowledge.query(CognitiveContext("What are the hours?")))
    print("query support:", knowledge.query(CognitiveContext("support contact")))
    print("plugins discovered:", list(app.plugins.names))

    # Clean up the fake module.
    import sys

    del sys.modules["_demo_plugins"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    stage_explicit()
    stage_factory()
    stage_plugin()


if __name__ == "__main__":
    main()

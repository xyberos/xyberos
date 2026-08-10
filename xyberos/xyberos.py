"""Public API for the Xyberos core."""

from collections.abc import Callable, Iterable, Mapping
from typing import Any, TypeVar, cast

from .agents import MultiAgentRuntime, RuntimeAgent
from .brain.brain import Brain
from .contracts.agent import Agent
from .contracts.experience import ExperienceStore
from .contracts.intent import IntentEngine
from .contracts.knowledge import KnowledgeProvider
from .contracts.memory import MemoryProvider
from .contracts.planner import Planner
from .contracts.plugin import Plugin
from .contracts.router import Router
from .contracts.vector import VectorStore
from .contracts.workflow import Workflow
from .events import FEEDBACK_RECORDED, EventBus
from .experience import InMemoryExperience
from .intent import HeuristicIntentEngine, build_intent_cascade
from .kernel.config import Config
from .kernel.kernel import Kernel
from .kernel.logger import Logger
from .kernel.registry import ServiceRegistry
from .knowledge import InMemoryKnowledge, VectorKnowledge
from .llm import EchoLLM, HashEmbedder, LLMProvider
from .memory import InMemoryMemory, VectorMemory
from .planner import AdaptivePlanner, SequentialPlanner
from .plugins.loader import PluginLoader
from .runtime.context import CognitiveContext
from .runtime.runtime import Runtime
from .security import Security
from .tools import ToolRegistry, ToolRunner
from .vector import SqliteVectorStore
from .workflows import SequentialWorkflow

T = TypeVar("T")


class Xyberos:
    """Public application facade that composes the independent core layers."""

    def __init__(
        self,
        config: Mapping[str, Any] | None = None,
        llm: LLMProvider | None = None,
        memory: MemoryProvider | None = None,
        knowledge: KnowledgeProvider | None = None,
        tools: ToolRegistry | None = None,
        planner: Planner | None = None,
        workflow: Workflow | None = None,
        tool_runner: ToolRunner | None = None,
        intent: IntentEngine | None = None,
        experience: ExperienceStore | None = None,
        router: Router | None = None,
    ) -> None:
        self.kernel = Kernel(config)
        self.kernel.register("llm", llm or EchoLLM())
        self.kernel.register("memory", memory or InMemoryMemory())
        self.kernel.register("knowledge", knowledge or InMemoryKnowledge())
        resolved_tools = tools or ToolRegistry()
        self.kernel.register("tools", resolved_tools)
        self.kernel.register("tool_runner", tool_runner or ToolRunner(resolved_tools))
        self.kernel.register("planner", planner or SequentialPlanner())
        self.kernel.register("workflow", workflow or SequentialWorkflow())
        self.kernel.register("intent", intent or HeuristicIntentEngine())
        self.kernel.register("experience", experience or InMemoryExperience())
        if router is not None:
            self.kernel.register("router", router)
        self.brain = self.kernel.inject(Brain, security=self.kernel.security)
        self.kernel.register("brain", self.brain)
        self.runtime = self.kernel.inject(Runtime, security=self.kernel.security)
        self.kernel.register("runtime", self.runtime)
        self.agent = RuntimeAgent("default", self.runtime)
        self.agents = MultiAgentRuntime([self.agent])
        self.kernel.register("agents", self.agents)

    @property
    def config(self) -> Config:
        return self.kernel.config

    @property
    def logger(self) -> Logger:
        return self.kernel.logger

    @property
    def registry(self) -> ServiceRegistry:
        return self.kernel.registry

    @property
    def plugins(self) -> PluginLoader:
        return self.kernel.plugins

    @property
    def events(self) -> EventBus:
        return cast(EventBus, self.resolve("events"))

    @property
    def security(self) -> Security:
        return cast(Security, self.resolve("security"))

    @property
    def llm(self) -> LLMProvider:
        return cast(LLMProvider, self.resolve("llm"))

    @property
    def memory(self) -> MemoryProvider:
        return cast(MemoryProvider, self.resolve("memory"))

    @property
    def knowledge(self) -> KnowledgeProvider:
        return cast(KnowledgeProvider, self.resolve("knowledge"))

    @property
    def tools(self) -> ToolRegistry:
        return cast(ToolRegistry, self.resolve("tools"))

    @property
    def tool_runner(self) -> ToolRunner:
        return cast(ToolRunner, self.resolve("tool_runner"))

    @property
    def planner(self) -> Planner:
        return cast(Planner, self.resolve("planner"))

    @property
    def intent(self) -> IntentEngine:
        return cast(IntentEngine, self.resolve("intent"))

    @property
    def experience(self) -> ExperienceStore:
        return cast(ExperienceStore, self.resolve("experience"))

    @property
    def workflow(self) -> Workflow:
        return cast(Workflow, self.resolve("workflow"))

    @property
    def started(self) -> bool:
        return self.kernel.started

    def register(self, name: str, service: T, *, replace: bool = False) -> T:
        return self.kernel.register(name, service, replace=replace)

    def register_factory(
        self,
        name: str,
        factory: Callable[..., T],
        *,
        singleton: bool = True,
        replace: bool = False,
    ) -> Callable[..., T]:
        return self.kernel.register_factory(name, factory, singleton=singleton, replace=replace)

    def resolve(self, name: str) -> object:
        return self.kernel.resolve(name)

    def load_plugin(self, plugin: Plugin) -> Plugin:
        """Load a plugin into this application's platform kernel."""
        return self.plugins.load(plugin)

    def unload_plugin(self, name: str) -> Plugin:
        """Unload a previously loaded plugin by name."""
        return self.plugins.unload(name)

    def load_entry_points(self, group: str = "xyberos.plugins") -> tuple[Plugin, ...]:
        """Auto-discover and load every installed plugin declared as an entry point."""
        loaded = self.plugins.load_entry_points(group)
        # Propagate any provider replacements to the already-constructed brain
        # (plugins register via kernel.register("x", ..., replace=True), but the
        # brain captured its provider references during __init__).
        for name in (
            "llm",
            "memory",
            "knowledge",
            "planner",
            "workflow",
            "tool_runner",
            "intent",
            "experience",
        ):
            setattr(self.brain, name, self.resolve(name))
        return loaded

    def load_plugins_from(self, package: str) -> tuple[Plugin, ...]:
        """Auto-discover and load every Plugin subclass found in ``package``."""
        return self.plugins.load_from_package(package)

    def register_agent(self, agent: Agent) -> Agent:
        """Register an agent in the application's multi-agent runtime."""
        return self.agents.register(agent)

    def remove_agent(self, name: str) -> Agent:
        """Remove a registered agent by name."""
        return self.agents.remove(name)

    def inject(self, target: Callable[..., T], /, **overrides: object) -> T:
        """Construct or invoke a callable with registered dependencies."""
        return self.kernel.inject(target, **overrides)

    def start(self) -> None:
        self.kernel.start()

    def stop(self) -> None:
        self.kernel.stop()

    def run(self, prompt: str, *, metadata: Mapping[str, Any] | None = None) -> CognitiveContext:
        """Run one prompt and return its complete cognitive context."""
        context = CognitiveContext(prompt=prompt, metadata=dict(metadata or {}))
        return self.runtime.run(context)

    async def arun(self, prompt: str, *, metadata: Mapping[str, Any] | None = None) -> CognitiveContext:
        """Async variant of :meth:`run`, awaiting the async pipeline."""
        context = CognitiveContext(prompt=prompt, metadata=dict(metadata or {}))
        return await self.runtime.arun(context)

    def chat(self, prompt: str, *, metadata: Mapping[str, Any] | None = None) -> str:
        """Convenience API returning only the generated text."""
        response = self.run(prompt, metadata=metadata).response
        if response is None:
            raise RuntimeError("the cognitive pipeline produced no response")
        return response

    async def achat(self, prompt: str, *, metadata: Mapping[str, Any] | None = None) -> str:
        """Async convenience API returning only the generated text."""
        response = (await self.arun(prompt, metadata=metadata)).response
        if response is None:
            raise RuntimeError("the cognitive pipeline produced no response")
        return response

    def run_agents(
        self,
        prompt: str,
        *,
        metadata: Mapping[str, Any] | None = None,
        agent_names: Iterable[str] | None = None,
    ) -> CognitiveContext:
        """Run all or selected registered agents against a fresh context."""
        context = CognitiveContext(prompt=prompt, metadata=dict(metadata or {}))
        return self.agents.run(context, agent_names=agent_names)

    def feedback(self, episode_id: str, rating: float, *, note: str | None = None) -> None:
        """Attach a rating (-1.0..1.0) to a recorded episode (RFC-0016).

        Ratings become the training signal for the learning layer; the
        ``brain.feedback_recorded`` event is emitted on the event bus.
        """
        self.experience.feedback(episode_id, rating, note=note)
        self.events.emit(FEEDBACK_RECORDED, episode_id=episode_id, rating=rating)


def create_app(
    config: Mapping[str, Any] | None = None,
    llm: LLMProvider | None = None,
    memory: MemoryProvider | None = None,
    knowledge: KnowledgeProvider | None = None,
    tools: ToolRegistry | None = None,
    planner: Planner | None = None,
    workflow: Workflow | None = None,
    tool_runner: ToolRunner | None = None,
    intent: IntentEngine | None = None,
    experience: ExperienceStore | None = None,
    router: Router | None = None,
) -> Xyberos:
    """Build a ready-to-use Xyberos application."""
    return Xyberos(
        config=config,
        llm=llm,
        memory=memory,
        knowledge=knowledge,
        tools=tools,
        tool_runner=tool_runner,
        planner=planner,
        workflow=workflow,
        intent=intent,
        experience=experience,
        router=router,
    )


def create_semantic_app(
    config: Mapping[str, Any] | None = None,
    llm: LLMProvider | None = None,
    embedder: Any | None = None,
    store: VectorStore | None = None,
    *,
    experience: ExperienceStore | None = None,
    tools: ToolRegistry | None = None,
    workflow: Workflow | None = None,
    tool_runner: ToolRunner | None = None,
    router: Router | None = None,
) -> Xyberos:
    """Build a ready-to-use app backed by one shared, persistent VectorStore.

    This is the one-line persistent setup for the RFC-0016 trainable engines:
    intent, memory, and knowledge all share a single
    :class:`~vector.sqlite.SqliteVectorStore` (``learning.db`` by default), so
    everything learned survives restarts with zero extra configuration.

    ``embedder`` is any ``embed(text)`` object (e.g. ``OpenAIEmbeddingLLM``); it
    defaults to a deterministic :class:`~llm.HashEmbedder` for development.
    Swap ``store`` for any other ``VectorStore`` (``ChromaVectorStore``,
    ``PgVectorStore``, or a plugin-provided one) to change the backend without
    touching the engines.
    """
    embedder = embedder or HashEmbedder()
    store = store or SqliteVectorStore("learning.db")
    effective_config = dict(config or {})
    effective_config.setdefault("brain.intent", True)
    return create_app(
        config=effective_config,
        llm=llm,
        memory=VectorMemory(store, embedder=embedder),
        knowledge=VectorKnowledge(store, embedder=embedder),
        intent=build_intent_cascade(
            store=store,
            embedder=embedder,
            llm=llm,
            threshold=float(effective_config.get("intent.threshold", 0.9)),
        ),
        planner=AdaptivePlanner(llm, store=store, embedder=embedder),
        tools=tools,
        tool_runner=tool_runner,
        workflow=workflow,
        experience=experience,
        router=router,
    )


def chat(
    prompt: str,
    *,
    config: Mapping[str, Any] | None = None,
    llm: LLMProvider | None = None,
    memory: MemoryProvider | None = None,
    knowledge: KnowledgeProvider | None = None,
    tools: ToolRegistry | None = None,
    planner: Planner | None = None,
    workflow: Workflow | None = None,
    tool_runner: ToolRunner | None = None,
) -> str:
    """One-shot helper for the default application configuration."""
    return create_app(
        config=config,
        llm=llm,
        memory=memory,
        knowledge=knowledge,
        tools=tools,
        tool_runner=tool_runner,
        planner=planner,
        workflow=workflow,
    ).chat(prompt)


async def achat(
    prompt: str,
    *,
    config: Mapping[str, Any] | None = None,
    llm: LLMProvider | None = None,
    memory: MemoryProvider | None = None,
    knowledge: KnowledgeProvider | None = None,
    tools: ToolRegistry | None = None,
    planner: Planner | None = None,
    workflow: Workflow | None = None,
    tool_runner: ToolRunner | None = None,
) -> str:
    """One-shot async helper for the default application configuration."""
    return await create_app(
        config=config,
        llm=llm,
        memory=memory,
        knowledge=knowledge,
        tools=tools,
        tool_runner=tool_runner,
        planner=planner,
        workflow=workflow,
    ).achat(prompt)


__all__ = ["Xyberos", "achat", "chat", "create_app"]

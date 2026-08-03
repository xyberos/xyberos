"""Public API for the Xyberos core."""

from collections.abc import Callable, Mapping
from typing import Any

from .agents import MultiAgentRuntime, RuntimeAgent
from .brain.brain import Brain
from .brain.llm import EchoLLM, LLMProvider
from .kernel.kernel import Kernel
from .runtime.context import CognitiveContext
from .runtime.runtime import Runtime


class Xyberos:
    """Public application facade that composes the independent core layers."""

    def __init__(self, config: Mapping[str, Any] | None = None, llm: LLMProvider | None = None) -> None:
        self.kernel = Kernel(config)
        self.kernel.register("llm", llm or EchoLLM())
        self.brain = self.kernel.inject(Brain)
        self.kernel.register("brain", self.brain)
        self.runtime = self.kernel.inject(Runtime)
        self.kernel.register("runtime", self.runtime)
        self.agent = RuntimeAgent("default", self.runtime)
        self.agents = MultiAgentRuntime([self.agent])
        self.kernel.register("agents", self.agents)

    @property
    def config(self):
        return self.kernel.config

    @property
    def logger(self):
        return self.kernel.logger

    @property
    def registry(self):
        return self.kernel.registry

    @property
    def plugins(self):
        return self.kernel.plugins

    @property
    def started(self) -> bool:
        return self.kernel.started

    def register(self, name: str, service: object, *, replace: bool = False) -> object:
        return self.kernel.register(name, service, replace=replace)

    def register_factory(self, name: str, factory, *, singleton: bool = True, replace: bool = False):
        return self.kernel.register_factory(name, factory, singleton=singleton, replace=replace)

    def resolve(self, name: str) -> object:
        return self.kernel.resolve(name)

    def load_plugin(self, plugin):
        """Load a plugin into this application's platform kernel."""
        return self.plugins.load(plugin)

    def unload_plugin(self, name: str):
        """Unload a previously loaded plugin by name."""
        return self.plugins.unload(name)

    def register_agent(self, agent):
        """Register an agent in the application's multi-agent runtime."""
        return self.agents.register(agent)

    def remove_agent(self, name: str):
        """Remove a registered agent by name."""
        return self.agents.remove(name)

    def inject(self, target: Callable[..., object], /, **overrides: object) -> object:
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

    def chat(self, prompt: str, *, metadata: Mapping[str, Any] | None = None) -> str:
        """Convenience API returning only the generated text."""
        response = self.run(prompt, metadata=metadata).response
        if response is None:
            raise RuntimeError("the cognitive pipeline produced no response")
        return response

    def run_agents(
        self, prompt: str, *, metadata: Mapping[str, Any] | None = None, agent_names=None
    ) -> CognitiveContext:
        """Run all or selected registered agents against a fresh context."""
        context = CognitiveContext(prompt=prompt, metadata=dict(metadata or {}))
        return self.agents.run(context, agent_names=agent_names)


def create_app(config: Mapping[str, Any] | None = None, llm: LLMProvider | None = None) -> Xyberos:
    """Build a ready-to-use Xyberos application."""
    return Xyberos(config=config, llm=llm)


def chat(prompt: str, *, config: Mapping[str, Any] | None = None, llm: LLMProvider | None = None) -> str:
    """One-shot helper for the default application configuration."""
    return create_app(config=config, llm=llm).chat(prompt)


__all__ = ["Xyberos", "create_app", "chat"]

"""Composition root for a Xyberos instance."""

from collections.abc import Mapping
from typing import Any

try:
    from ..brain.brain import Brain
    from ..brain.llm import EchoLLM, LLMProvider
    from ..runtime.context import CognitiveContext
    from ..runtime.runtime import Runtime
except ImportError:  # pragma: no cover - depends on import style
    from brain.brain import Brain
    from brain.llm import EchoLLM, LLMProvider
    from runtime.context import CognitiveContext
    from runtime.runtime import Runtime

from .config import Config
from .logger import Logger
from .registry import ServiceRegistry


class Kernel:
    """Wire configuration, logging, cognition, and execution into one service."""

    def __init__(self, config: Config | Mapping[str, Any] | None = None, llm: LLMProvider | None = None) -> None:
        self.config = config if isinstance(config, Config) else Config(config)
        self.registry = ServiceRegistry()
        self._started = False
        self.logger = Logger(
            name=self.config.get("logger_name", "xyberos"),
            level=self.config.get("log_level", "INFO"),
        )
        self.register("config", self.config)
        self.register("logger", self.logger)
        self.register("llm", llm or EchoLLM())
        self.brain = self.inject(Brain)
        self.register("brain", self.brain)
        self.runtime = self.inject(Runtime)
        self.register("runtime", self.runtime)

    @property
    def started(self) -> bool:
        """Whether the kernel lifecycle is currently active."""
        return self._started

    def register(self, name: str, service: object, *, replace: bool = False) -> object:
        """Register a shared service and return it.

        Registered services with a ``start`` or ``stop`` method participate in
        the kernel lifecycle in registration order and reverse order,
        respectively.
        """
        registered = self.registry.register(name, service, replace=replace)
        if self._started:
            start = getattr(service, "start", None)
            if callable(start):
                start()
        return registered

    def register_factory(
        self, name: str, factory: object, *, singleton: bool = True, replace: bool = False
    ) -> object:
        """Register a dependency-injected service factory."""
        if self._started:
            raise RuntimeError("register factories before starting the kernel")
        return self.registry.register_factory(name, factory, singleton=singleton, replace=replace)  # type: ignore[arg-type]

    def resolve(self, name: str) -> object:
        """Retrieve a registered shared service by name."""
        return self.registry.resolve(name)

    def inject(self, target: object, /, **overrides: object) -> object:
        """Construct or invoke a callable with registered dependencies."""
        return self.registry.inject(target, **overrides)  # type: ignore[arg-type]

    def start(self) -> None:
        """Start all registered lifecycle-aware services."""
        if self._started:
            return
        for service in self.registry.values():
            start = getattr(service, "start", None)
            if callable(start):
                start()
        self._started = True

    def stop(self) -> None:
        """Stop registered lifecycle-aware services in reverse order."""
        if not self._started:
            return
        try:
            for service in reversed(self.registry.values()):
                stop = getattr(service, "stop", None)
                if callable(stop):
                    stop()
        finally:
            self._started = False

    def run(self, prompt: str, *, metadata: Mapping[str, Any] | None = None) -> CognitiveContext:
        """Run one prompt and return its complete cognitive context."""
        context = CognitiveContext(prompt=prompt, metadata=dict(metadata or {}))
        return self.runtime.run(context)

    def chat(self, prompt: str, *, metadata: Mapping[str, Any] | None = None) -> str:
        """Convenience API returning only the generated text."""
        response = self.run(prompt, metadata=metadata).response
        assert response is not None
        return response

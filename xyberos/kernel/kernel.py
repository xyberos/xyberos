"""Composition root for a Xyberos instance."""

from collections.abc import Mapping
from typing import Any

try:
    from ..brain.brain import Brain
    from ..brain.llm import LLMProvider
    from ..runtime.context import CognitiveContext
    from ..runtime.runtime import Runtime
except ImportError:  # pragma: no cover - depends on import style
    from brain.brain import Brain
    from brain.llm import LLMProvider
    from runtime.context import CognitiveContext
    from runtime.runtime import Runtime

from .config import Config
from .logger import Logger


class Kernel:
    """Wire configuration, logging, cognition, and execution into one service."""

    def __init__(self, config: Config | Mapping[str, Any] | None = None, llm: LLMProvider | None = None) -> None:
        self.config = config if isinstance(config, Config) else Config(config)
        self._services: dict[str, object] = {}
        self._started = False
        self.logger = Logger(
            name=self.config.get("logger_name", "xyberos"),
            level=self.config.get("log_level", "INFO"),
        )
        self.brain = Brain(llm=llm, logger=self.logger)
        self.runtime = Runtime(self.brain)
        self.register("config", self.config)
        self.register("logger", self.logger)
        self.register("brain", self.brain)
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
        if not isinstance(name, str) or not name.strip():
            raise ValueError("service name must be a non-empty string")
        if name in self._services and not replace:
            raise KeyError(f"Service is already registered: {name}")
        if self._started:
            start = getattr(service, "start", None)
            if callable(start):
                start()
        self._services[name] = service
        return service

    def resolve(self, name: str) -> object:
        """Retrieve a registered shared service by name."""
        try:
            return self._services[name]
        except KeyError as exc:
            raise KeyError(f"No service registered with name: {name}") from exc

    def start(self) -> None:
        """Start all registered lifecycle-aware services."""
        if self._started:
            return
        for service in self._services.values():
            start = getattr(service, "start", None)
            if callable(start):
                start()
        self._started = True

    def stop(self) -> None:
        """Stop registered lifecycle-aware services in reverse order."""
        if not self._started:
            return
        try:
            for service in reversed(tuple(self._services.values())):
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

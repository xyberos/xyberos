"""Composition root for a Xyberos instance."""

from collections.abc import Mapping
from typing import Any

try:
    from ..brain.brain import Brain
    from ..brain.llm import ChatModel
    from ..runtime.context import CognitiveContext
    from ..runtime.runtime import Runtime
except ImportError:  # pragma: no cover - depends on import style
    from xyberos_v2.brain.brain import Brain
    from xyberos_v2.brain.llm import ChatModel
    from xyberos_v2.runtime.context import CognitiveContext
    from xyberos_v2.runtime.runtime import Runtime

from .config import Config
from .logger import Logger


class Kernel:
    """Wire configuration, logging, cognition, and execution into one service."""

    def __init__(self, config: Config | Mapping[str, Any] | None = None, llm: ChatModel | None = None) -> None:
        self.config = config if isinstance(config, Config) else Config(config)
        self.logger = Logger(
            name=self.config.get("logger_name", "xyberos"),
            level=self.config.get("log_level", "INFO"),
        )
        self.brain = Brain(llm=llm, logger=self.logger)
        self.runtime = Runtime(self.brain)

    def run(self, prompt: str, *, metadata: Mapping[str, Any] | None = None) -> CognitiveContext:
        """Run one prompt and return its complete cognitive context."""
        context = CognitiveContext(prompt=prompt, metadata=dict(metadata or {}))
        return self.runtime.run(context)

    def chat(self, prompt: str, *, metadata: Mapping[str, Any] | None = None) -> str:
        """Convenience API returning only the generated text."""
        response = self.run(prompt, metadata=metadata).response
        assert response is not None
        return response

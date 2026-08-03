"""Adapter exposing an existing Runtime as a named agent."""

from typing import TYPE_CHECKING

try:
    from ..contracts.agent import Agent
    from ..runtime.context import CognitiveContext
except ImportError:  # pragma: no cover - depends on import style
    from contracts.agent import Agent
    from runtime.context import CognitiveContext

if TYPE_CHECKING:
    try:
        from ..runtime.runtime import Runtime
    except ImportError:  # pragma: no cover - depends on import style
        from runtime.runtime import Runtime


class RuntimeAgent(Agent):
    """Run one existing Runtime as an agent in a multi-agent pipeline."""

    def __init__(self, name: str, runtime: "Runtime") -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("agent name must be a non-empty string")
        self._name = name
        self._runtime = runtime

    @property
    def name(self) -> str:
        return self._name

    def run(self, context: object) -> CognitiveContext:
        if not isinstance(context, CognitiveContext):
            raise TypeError("context must be a CognitiveContext")
        return self._runtime.run(context)

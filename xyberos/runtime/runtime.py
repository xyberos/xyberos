"""Runtime execution for cognitive requests."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    try:  # Supports both ``import runtime`` and ``import Xyberos_v2.runtime``.
        from ..brain.brain import Brain
    except ImportError:  # pragma: no cover - depends on import style
        from brain.brain import Brain

from .context import CognitiveContext


class Runtime:
    """Executes contexts with a configured :class:`~brain.brain.Brain`."""

    def __init__(self, brain: "Brain") -> None:
        self.brain = brain

    def run(self, context: CognitiveContext) -> CognitiveContext:
        """Populate and return ``context`` after asking the brain to respond."""
        if not isinstance(context, CognitiveContext):
            raise TypeError("context must be a CognitiveContext")

        try:
            context.response = self.brain.chat(context)
            context.error = None
        except Exception as exc:
            context.error = exc
            raise
        return context

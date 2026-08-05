"""Runtime execution for cognitive requests."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..brain.brain import Brain

from ..events import EventBus
from ..events.names import REQUEST_COMPLETED, REQUEST_FAILED, REQUEST_STARTED
from ..exceptions.workflow import WorkflowPaused
from .context import CognitiveContext


class Runtime:
    """Executes contexts with a configured :class:`~brain.brain.Brain`."""

    def __init__(self, brain: "Brain", events: EventBus | None = None) -> None:
        self.brain = brain
        self.events = events

    def run(self, context: CognitiveContext) -> CognitiveContext:
        """Populate and return ``context`` after asking the brain to respond."""
        if not isinstance(context, CognitiveContext):
            raise TypeError("context must be a CognitiveContext")

        if self.events is not None:
            self.events.emit(REQUEST_STARTED, context=context)

        try:
            context.response = self.brain.chat(context)
            context.error = None
        except WorkflowPaused:
            raise  # a workflow pause, not a request failure
        except Exception as exc:
            context.error = exc
            if self.events is not None:
                self.events.emit(REQUEST_FAILED, context=context, error=str(exc))
            raise
        if self.events is not None:
            self.events.emit(REQUEST_COMPLETED, context=context)
        return context

"""A minimal sequential workflow engine."""

from collections.abc import Callable, Iterable

from ..contracts.workflow import Workflow
from ..runtime.context import CognitiveContext


WorkflowStep = Callable[[CognitiveContext], CognitiveContext | None]


class SequentialWorkflow(Workflow):
    """Apply registered steps in order to one canonical context.

    A step may mutate the context in place and return ``None``, or return a
    replacement ``CognitiveContext``. This makes the engine suitable for
    composing runtime execution, validation, and future planning/tool steps.
    """

    def __init__(self, steps: Iterable[WorkflowStep] = ()) -> None:
        self._steps = list(steps)
        if not all(callable(step) for step in self._steps):
            raise TypeError("all workflow steps must be callable")

    @property
    def steps(self) -> tuple[WorkflowStep, ...]:
        """The immutable ordered view of configured workflow steps."""
        return tuple(self._steps)

    def add_step(self, step: WorkflowStep) -> None:
        """Append a step to the workflow."""
        if not callable(step):
            raise TypeError("workflow step must be callable")
        self._steps.append(step)

    def run(self, context: object) -> CognitiveContext:
        """Execute each step and return the final cognitive context."""
        if not isinstance(context, CognitiveContext):
            raise TypeError("context must be a CognitiveContext")

        current = context
        for step in self._steps:
            result = step(current)
            if result is None:
                continue
            if not isinstance(result, CognitiveContext):
                raise TypeError("workflow steps must return a CognitiveContext or None")
            current = result
        return current

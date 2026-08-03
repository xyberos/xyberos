"""A minimal sequential planning engine."""

from typing import Any

from ..contracts.planner import Planner


class SequentialPlanner(Planner):
    """Produce an ordered list of plan steps for an execution context.

    The default step names are generic; callers can supply their own ordered
    steps via the constructor.
    """

    DEFAULT_STEPS = ("analyze", "execute", "review")

    def __init__(self, steps: tuple[str, ...] = DEFAULT_STEPS) -> None:
        self._steps = tuple(steps)

    def plan(self, context: object) -> Any:
        """Build a plan whose steps reference the context prompt."""
        prompt = getattr(context, "prompt", "")
        return [f"{step}: {prompt}" for step in self._steps]

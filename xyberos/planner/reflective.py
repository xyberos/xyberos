"""Reflective planner with confidence scoring (RFC-0016, Phase 1)."""

from __future__ import annotations

from typing import Any

from ..contracts.planner import Planner
from ..exceptions.llm import StructuredOutputError
from ..llm import EchoLLM, LLMProvider, structured
from .llm import LLMPlanner

_REFLECTION_INSTRUCTION = (
    "Review the following plan for the request. Return ONLY a JSON object with "
    '"confidence" (0.0 to 1.0, how likely this plan succeeds) and "revised_plan" '
    "(an array of improved steps, or null to keep the plan unchanged).\n\n"
    "Request: {request}\nPlan:\n{plan}"
)


class ReflectivePlanner(Planner):
    """Score and optionally revise a plan with a reflection pass.

    Delegates plan generation to a base planner (:class:`~planner.LLMPlanner` by
    default) and, when an LLM is supplied, runs a second reflection pass that
    records a confidence score on ``context.metadata["plan.confidence"]`` and
    returns a revised plan when the model suggests one.
    """

    def __init__(
        self,
        planner: Planner | None = None,
        *,
        llm: LLMProvider | None = None,
        reflection_prompt: str | None = None,
    ) -> None:
        self._planner = planner or LLMPlanner(llm or EchoLLM())
        self._llm = llm
        self._reflection_prompt = reflection_prompt or _REFLECTION_INSTRUCTION

    def plan(self, context: object) -> Any:
        request = getattr(context, "prompt", "")
        plan = self._planner.plan(context)
        confidence = 1.0
        if self._llm is not None:
            reflection: Any = {}
            try:
                reflection = structured(
                    self._llm,
                    self._reflection_prompt.format(request=request, plan=_render_plan(plan)),
                )
            except StructuredOutputError:
                reflection = {}
            if isinstance(reflection, dict):
                try:
                    confidence = float(reflection.get("confidence", 1.0))
                except (TypeError, ValueError):
                    confidence = 1.0
                revised = reflection.get("revised_plan")
                if revised is not None:
                    plan = revised
        metadata = getattr(context, "metadata", None)
        if isinstance(metadata, dict):
            metadata["plan.confidence"] = confidence
        return plan


def _render_plan(plan: Any) -> str:
    if isinstance(plan, str):
        return plan
    if isinstance(plan, (list, tuple)):
        return "\n".join(f"- {step}" for step in plan)
    return str(plan)

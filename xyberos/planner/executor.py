"""Plan execution with verification and re-planning (RFC-0016, Phase 2).

The :class:`PlanExecutor` closes the loop that RFC-Roadmap §6 asked for: it runs
each plan step, verifies the intermediate result, and re-plans on failure —
bounded so a bad plan cannot spin forever.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..events import EventBus
from ..events.names import PLAN_REPLANNED, PLAN_STEP_EXECUTED, PLAN_STEP_FAILED
from ..tools import ToolRunner

# A verifier decides whether a step's result is acceptable: (step, result) -> bool.
Verifier = Callable[[Any, Any], bool]

# A replan strategy turns (remaining_steps, failed_step, error) into a new plan
# (list of steps) or None to mean "skip the failed step and continue".
Replanner = Callable[[list[Any], Any, Any], list[Any] | None]


@dataclass
class PlanResult:
    """The outcome of executing a plan."""

    steps: list[Any]
    results: list[Any] = field(default_factory=list)
    error: Any | None = None
    replans: int = 0
    executed: int = 0

    @property
    def completed(self) -> bool:
        """Whether every step ran without an unrecoverable failure."""
        return self.error is None


@dataclass
class _Outcome:
    ok: bool
    value: Any | None = None
    error: Any | None = None


class PlanExecutor:
    """Run plan steps through tools or step callables, verifying and re-planning.

    A step may be:
      * a string naming a registered tool (run with no extra arguments),
      * a ``{"tool": name, "args": {...}}`` mapping,
      * a plain callable ``(context) -> result``.

    After each step the configured ``verify`` decides success (by default a
    non-``None`` result that is not an exception). On failure the executor
    consults the ``replan`` strategy — by default it drops the failed step and
    continues; a custom strategy can return a revised plan. Total tool calls are
    bounded by ``max_steps`` and re-plans by ``max_replans``.
    """

    def __init__(
        self,
        tool_runner: ToolRunner | None = None,
        *,
        verify: Verifier | None = None,
        replan: Replanner | None = None,
        max_steps: int = 10,
        max_replans: int = 3,
        events: EventBus | None = None,
    ) -> None:
        if max_steps <= 0 or max_replans < 0:
            raise ValueError("max_steps must be positive and max_replans non-negative")
        if verify is not None and not callable(verify):
            raise TypeError("verify must be callable")
        if replan is not None and not callable(replan):
            raise TypeError("replan must be callable")
        self._tool_runner = tool_runner
        self._verify = verify or _default_verify
        self._replan = replan
        self._max_steps = max_steps
        self._max_replans = max_replans
        self._events = events

    def execute(self, context: object, plan: Any) -> PlanResult:
        """Execute ``plan`` steps in order; returns a :class:`PlanResult`."""
        pending = list(plan or [])
        result = PlanResult(steps=pending)
        while pending and result.executed < self._max_steps:
            step = pending[0]
            outcome = self._run_step(context, step)
            if outcome.ok:
                result.results.append(outcome.value)
                result.executed += 1
                pending.pop(0)
                self._emit(PLAN_STEP_EXECUTED, context=context, step=_describe(step))
                continue

            self._emit(PLAN_STEP_FAILED, context=context, step=_describe(step), error=outcome.error)
            if result.replans >= self._max_replans:
                result.error = outcome.error
                return result
            result.replans += 1
            revised = self._replan_steps(context, pending, step, outcome.error)
            self._emit(PLAN_REPLANNED, context=context, step=_describe(step))
            if revised is None:
                # Default strategy: drop the failed step so execution progresses.
                pending.pop(0)
            else:
                # Custom strategy: replace the remaining plan (retry or re-plan).
                pending = revised
        return result

    def _run_step(self, context: object, step: Any) -> _Outcome:
        try:
            if callable(step):
                value = step(context)
            elif isinstance(step, dict):
                name = step.get("tool")
                if not name:
                    return _Outcome(ok=False, error=TypeError("step dict requires a 'tool' key"))
                value = self._dispatch(name, context, step.get("args", {}) or {})
            elif isinstance(step, str):
                value = self._dispatch(step, context, {})
            else:
                return _Outcome(ok=False, error=TypeError(f"unsupported step: {step!r}"))
        except Exception as exc:  # noqa: BLE001 - step failures are retryable outcomes
            return _Outcome(ok=False, error=exc)
        if not self._verify(step, value):
            return _Outcome(
                ok=False,
                error=ValueError(f"step failed verification: {_describe(step)}"),
            )
        return _Outcome(ok=True, value=value)

    def _dispatch(self, name: str, context: object, arguments: dict[str, Any]) -> Any:
        if self._tool_runner is None:
            raise ValueError(f"no tool runner configured for step {name!r}")
        return self._tool_runner.run(name, context, **arguments)

    def _replan_steps(
        self, context: object, pending: list[Any], step: Any, error: Any
    ) -> list[Any] | None:
        if self._replan is not None:
            revised = self._replan(list(pending), step, error)
            if isinstance(revised, (list, tuple)):
                return list(revised)
        return None

    def _emit(self, name: str, *, context: object | None = None, **data: Any) -> None:
        if self._events is not None:
            self._events.emit(name, context=context, **data)


def _default_verify(step: Any, value: Any) -> bool:
    """Accept a non-``None`` result that is not an exception."""
    return value is not None and not isinstance(value, BaseException)


def _describe(step: Any) -> str:
    if isinstance(step, str):
        return step
    if isinstance(step, dict):
        return str(step.get("tool", step))
    name = getattr(step, "__name__", None)
    return name if isinstance(name, str) else "callable"

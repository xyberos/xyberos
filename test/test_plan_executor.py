"""Tests for the PlanExecutor (RFC-0016, Phase 2)."""

from xyberos.events import PLAN_STEP_EXECUTED, PLAN_STEP_FAILED, EventBus
from xyberos.planner import PlanExecutor
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import FunctionTool, ToolRunner
from xyberos.tools.registry import ToolRegistry


def _runner(*tools):
    return ToolRunner(ToolRegistry(list(tools)))


def test_plan_executor_runs_tool_name_steps():
    runner = _runner(
        FunctionTool("step_a", lambda: "A"),
        FunctionTool("step_b", lambda: "B"),
    )
    executor = PlanExecutor(runner)

    result = executor.execute(CognitiveContext("x"), ["step_a", "step_b"])

    assert result.completed
    assert result.executed == 2
    assert result.results == ["A", "B"]


def test_plan_executor_runs_dict_and_callable_steps():
    runner = _runner(FunctionTool("add", lambda a, b: a + b))
    executor = PlanExecutor(runner)
    context = CognitiveContext("hi")

    result = executor.execute(
        context,
        [{"tool": "add", "args": {"a": 1, "b": 2}}, lambda ctx: ctx.prompt.upper()],
    )

    assert result.results == [3, "HI"]


def test_plan_executor_drops_failed_step_by_default():
    def flaky(ctx):
        return None  # fails default verification (None)

    executor = PlanExecutor(max_replans=1)

    result = executor.execute(CognitiveContext("x"), [flaky, lambda ctx: "done"])

    assert result.completed
    assert result.executed == 1
    assert result.results == ["done"]
    assert result.replans == 1


def test_plan_executor_uses_custom_replan_strategy():
    calls = {"n": 0}

    def flaky(ctx):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient failure")
        return "recovered"

    def replan(pending, step, error):
        return pending  # retry the failed step

    executor = PlanExecutor(replan=replan, max_replans=1)

    result = executor.execute(CognitiveContext("x"), [flaky, lambda ctx: "done"])

    assert result.completed
    assert result.results == ["recovered", "done"]


def test_plan_executor_gives_up_after_max_replans():
    executor = PlanExecutor(max_replans=0, verify=lambda step, value: value is not None)

    result = executor.execute(CognitiveContext("x"), [lambda ctx: None])

    assert not result.completed
    assert result.error is not None


def test_plan_executor_respects_max_steps():
    executor = PlanExecutor(max_steps=2)

    result = executor.execute(CognitiveContext("x"), [lambda ctx: 1, lambda ctx: 2, lambda ctx: 3])

    assert result.executed == 2
    assert result.results == [1, 2]


def test_plan_executor_emits_step_events():
    runner = _runner(FunctionTool("step_a", lambda: "A"), FunctionTool("step_b", lambda: None))
    events = EventBus()
    executor = PlanExecutor(
        runner,
        verify=lambda step, value: value is not None,
        max_replans=0,
        events=events,
    )
    seen = []
    events.subscribe(PLAN_STEP_EXECUTED, lambda event: seen.append(event.name))
    events.subscribe(PLAN_STEP_FAILED, lambda event: seen.append(event.name))

    executor.execute(CognitiveContext("x"), ["step_a", "step_b"])

    assert seen.count(PLAN_STEP_EXECUTED) == 1
    assert seen.count(PLAN_STEP_FAILED) == 1

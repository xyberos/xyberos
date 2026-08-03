from xyberos.planner import SequentialPlanner
from xyberos.runtime.context import CognitiveContext


def test_sequential_planner_builds_ordered_steps():
    planner = SequentialPlanner()
    context = CognitiveContext("ship the feature")

    assert planner.plan(context) == [
        "analyze: ship the feature",
        "execute: ship the feature",
        "review: ship the feature",
    ]


def test_sequential_planner_accepts_custom_steps():
    planner = SequentialPlanner(("plan", "do"))
    context = CognitiveContext("task")

    assert planner.plan(context) == ["plan: task", "do: task"]

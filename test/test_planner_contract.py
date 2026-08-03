import pytest

from xyberos.contracts import Planner
from xyberos.runtime.context import CognitiveContext


class StaticPlanner(Planner):
    def plan(self, context):
        return [{"action": "respond", "prompt": context.prompt}]


def test_planner_contract_requires_a_plan_method():
    with pytest.raises(TypeError):
        Planner()


def test_planner_contract_can_plan_without_brain_or_runtime_dependencies():
    context = CognitiveContext("make a plan")
    planner = StaticPlanner()

    assert planner.plan(context) == [{"action": "respond", "prompt": "make a plan"}]

"""Tests for LLM-driven planning and config-gated plan injection."""

import json

import pytest

from xyberos import create_app
from xyberos.brain.brain import Brain
from xyberos.kernel.config import Config
from xyberos.llm import CallableLLM
from xyberos.planner import LLMPlanner
from xyberos.runtime.context import CognitiveContext


def test_llm_planner_derives_steps_from_the_llm():
    planner = LLMPlanner(CallableLLM(lambda prompt: "research\ndraft\nreview"))

    assert planner.plan(CognitiveContext("build a report")) == ["research", "draft", "review"]


def test_llm_planner_supports_a_custom_parse():
    planner = LLMPlanner(CallableLLM(lambda prompt: '["a", "b"]'), parse=json.loads)

    assert planner.plan(CognitiveContext("x")) == ["a", "b"]


def test_llm_planner_handles_empty_output_and_validation():
    planner = LLMPlanner(CallableLLM(lambda prompt: "  \n\n"))

    assert planner.plan(CognitiveContext("x")) == []

    with pytest.raises(TypeError, match="callable"):
        LLMPlanner(CallableLLM(lambda prompt: "x"), parse=object())


class NonStringLLM:
    def generate(self, prompt):
        return 1


def test_llm_planner_rejects_non_string_llm_output():
    planner = LLMPlanner(NonStringLLM())

    with pytest.raises(TypeError, match="string"):
        planner.plan(CognitiveContext("x"))


def test_brain_injects_plan_into_prompt_when_configured():
    seen = []
    brain = Brain(
        llm=CallableLLM(lambda prompt: (seen.append(prompt) or "ok")),
        planner=LLMPlanner(CallableLLM(lambda prompt: "research\ndraft")),
        config=Config({"brain.inject_plan": True}),
    )

    brain.chat(CognitiveContext("build a report"))

    assert "Plan:" in seen[0]
    assert "- research" in seen[0]
    assert "- draft" in seen[0]


def test_brain_does_not_inject_plan_by_default():
    seen = []
    brain = Brain(
        llm=CallableLLM(lambda prompt: (seen.append(prompt) or "ok")),
        planner=LLMPlanner(CallableLLM(lambda prompt: "research")),
    )

    brain.chat(CognitiveContext("build a report"))

    assert "Plan:" not in seen[0]
    assert seen[0] == "build a report"


def test_app_injects_plan_via_config_flag():
    app = create_app(
        config={"brain.inject_plan": True},
        llm=CallableLLM(lambda prompt: prompt),  # echo the enriched prompt
        planner=LLMPlanner(CallableLLM(lambda prompt: "step one\nstep two")),
    )

    response = app.chat("build a report")

    assert response.startswith("build a report")
    assert "Plan:" in response
    assert "- step one" in response
    assert "- step two" in response

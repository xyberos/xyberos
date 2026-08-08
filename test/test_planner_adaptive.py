"""Tests for the Phase 1 planner engines (RFC-0016)."""

from xyberos.llm import CallableLLM
from xyberos.planner import AdaptivePlanner, ReflectivePlanner
from xyberos.planner.sequential import SequentialPlanner
from xyberos.runtime.context import CognitiveContext
from xyberos.vector import CosineVectorStore

_VOCAB = ("refund", "policy", "joke", "hello", "order", "hours", "shipping", "rules", "greeting")


def _embedder(text):
    vector = [0.0] * len(_VOCAB)
    for word in text.lower().split():
        for index, term in enumerate(_VOCAB):
            if term in word or word in term:
                vector[index] += 1.0
    return vector


def test_adaptive_planner_parses_plan():
    llm = CallableLLM(lambda prompt: "check order\nprocess refund")
    planner = AdaptivePlanner(llm)

    plan = planner.plan(CognitiveContext("refund my order"))

    assert plan == ["check order", "process refund"]


def test_adaptive_planner_injects_few_shot_examples():
    store = CosineVectorStore()
    seen = []

    def llm(prompt):
        seen.append(prompt)
        return "do it"

    planner = AdaptivePlanner(CallableLLM(llm), store=store, embedder=_embedder)
    planner.learn("refund an order", ["check order", "process refund"])

    planner.plan(CognitiveContext("please refund"))

    assert seen
    assert "examples" in seen[0]
    assert "check order" in seen[0]


def test_adaptive_planner_learn_is_noop_without_store():
    planner = AdaptivePlanner(CallableLLM(lambda prompt: "step"))
    planner.learn("request", ["step"])  # must not raise

    assert planner.plan(CognitiveContext("x")) == ["step"]


def test_reflective_planner_records_confidence_and_revises():
    llm = CallableLLM(
        lambda prompt: '{"confidence": 0.4, "revised_plan": ["step-a", "step-b"]}'
    )
    planner = ReflectivePlanner(SequentialPlanner(), llm=llm)
    context = CognitiveContext("do the thing")

    plan = planner.plan(context)

    assert plan == ["step-a", "step-b"]
    assert context.metadata.get("plan.confidence") == 0.4


def test_reflective_planner_without_llm_keeps_base_plan():
    planner = ReflectivePlanner(SequentialPlanner())
    context = CognitiveContext("analyze the request")

    plan = planner.plan(context)

    assert plan == [
        "analyze: analyze the request",
        "execute: analyze the request",
        "review: analyze the request",
    ]
    assert context.metadata.get("plan.confidence") == 1.0

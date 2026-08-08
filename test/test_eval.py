"""Tests for the RFC-0016 evaluation harness (xyberos.utils.eval)."""

from xyberos.intent import HeuristicIntentEngine, IntentRule
from xyberos.planner import PlanExecutor
from xyberos.runtime.context import CognitiveContext
from xyberos.utils import intent_accuracy, plan_success_rate, retrieval_recall_at_k
from xyberos.vector import CosineVectorStore


def _embedder(text):
    return [1.0, 0.0] if "alpha" in text else [0.0, 1.0]


def test_intent_accuracy_scores_top1_classification():
    engine = HeuristicIntentEngine([IntentRule("refund", ("refund",))])
    dataset = [("please refund", "refund"), ("hello", "greeting"), ("refund now", "refund")]

    assert intent_accuracy(engine, dataset) == 2 / 3


def test_intent_accuracy_empty_dataset_is_zero():
    engine = HeuristicIntentEngine([IntentRule("refund", ("refund",))])

    assert intent_accuracy(engine, []) == 0.0


def test_retrieval_recall_at_k_finds_expected_items():
    store = CosineVectorStore()
    store.upsert("eval", "doc1", [1.0, 0.0])
    store.upsert("eval", "doc2", [0.0, 1.0])
    dataset = [("alpha topic", "doc1"), ("beta topic", "doc2")]

    assert retrieval_recall_at_k(store, _embedder, dataset, k=1) == 1.0


def test_retrieval_recall_at_k_penalizes_misses():
    store = CosineVectorStore()
    store.upsert("eval", "doc1", [1.0, 0.0])
    dataset = [("alpha topic", "doc1"), ("gamma topic", "missing")]

    assert retrieval_recall_at_k(store, _embedder, dataset, k=1) == 0.5


def test_plan_success_rate_measures_execution():
    executor = PlanExecutor(max_replans=0)
    dataset = [
        (CognitiveContext("ok"), [lambda ctx: "fine"]),
        (CognitiveContext("fail"), [lambda ctx: None]),
    ]

    assert plan_success_rate(executor, dataset) == 0.5

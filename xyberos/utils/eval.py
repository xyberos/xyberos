"""Evaluation helpers for the trainable engines (RFC-0016, Phase 2).

Small, dependency-free metrics so you can measure whether "training" helps:
intent top-1 accuracy, retrieval recall@k, and plan success rate. Each takes a
plain ``(input, expected)`` dataset.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from ..contracts.intent import IntentEngine
from ..contracts.vector import VectorStore
from ..llm.embeddings import embed_text
from ..planner.executor import PlanExecutor
from ..runtime.context import CognitiveContext


def intent_accuracy(
    engine: IntentEngine,
    dataset: Iterable[tuple[str, str]],
    *,
    context_factory: Callable[[str], Any] | None = None,
) -> float:
    """Top-1 intent classification accuracy over ``(prompt, expected_intent)`` pairs."""
    make_context: Callable[[str], Any] = context_factory or (
        lambda prompt: CognitiveContext(prompt)
    )
    correct = 0
    total = 0
    for prompt, expected in dataset:
        total += 1
        if engine.classify(make_context(prompt)).name == expected:
            correct += 1
    return correct / total if total else 0.0


def retrieval_recall_at_k(
    store: VectorStore,
    embedder: Any,
    dataset: Iterable[tuple[str, str]],
    *,
    namespace: str = "eval",
    k: int = 5,
) -> float:
    """Fraction of ``(query, expected_id)`` pairs where ``expected_id`` is in the top-k."""
    found = 0
    total = 0
    for query, expected_id in dataset:
        vector = embed_text(embedder, query)
        hits = store.query(namespace, vector, top_k=k)
        total += 1
        if any(hit.id == expected_id for hit in hits):
            found += 1
    return found / total if total else 0.0


def plan_success_rate(
    executor: PlanExecutor,
    dataset: Iterable[tuple[Any, Any]],
) -> float:
    """Fraction of ``(context, plan)`` pairs executed without an unrecoverable error."""
    ok = 0
    total = 0
    for context, plan in dataset:
        total += 1
        if executor.execute(context, plan).completed:
            ok += 1
    return ok / total if total else 0.0

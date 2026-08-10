"""Factories for assembling intent classification cascades (RFC-0017, M8)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..contracts.intent import IntentEngine
from ..contracts.vector import VectorStore
from ..llm import LLMProvider
from .cascade import CascadeIntentEngine
from .embedding import EmbeddingIntentEngine
from .heuristic import HeuristicIntentEngine, IntentRule
from .llm import LLMIntentEngine

# Conservative, phrase-based default rules. Phrases (rather than single words)
# avoid collisions with learned embedding intents — e.g. "refund" is intentionally
# NOT under billing so a learned "refund" intent can win via embedding.
DEFAULT_RULES: tuple[IntentRule, ...] = (
    IntentRule("greeting", ("hello", "hi", "hey", "good morning", "good afternoon", "good evening")),
    IntentRule("farewell", ("goodbye", "bye", "see you", "thanks for your help")),
    IntentRule("help", ("help me", "i need help", "support", "assist me")),
    IntentRule(
        "order_status",
        ("order status", "track my order", "track my shipment", "where is my order", "where is my package"),
    ),
    IntentRule("billing", ("billing", "invoice", "payment")),
    IntentRule("account", ("reset my password", "change my password", "forgot my password", "login", "sign in")),
    IntentRule("technical", ("not working", "it crashed", "error message", "is broken")),
)


def build_intent_cascade(
    store: VectorStore | None = None,
    embedder: Any | None = None,
    llm: LLMProvider | None = None,
    rules: Iterable[IntentRule] | None = None,
    *,
    threshold: float = 0.9,
    fallback: str = "general",
    default_target: str | None = None,
) -> IntentEngine:
    """Assemble the recommended Heuristic → Embedding → LLM intent cascade.

    The cheapest engine that is confident enough wins:

    * **HeuristicIntentEngine** (tier 0) — deterministic phrase/keyword rules;
      a match answers with full confidence.
    * **EmbeddingIntentEngine** (tier 1) — nearest learned example; answers
      when the similarity clears ``threshold``.
    * **LLMIntentEngine** (tier 2) — last resort; handles novel phrasing when
      an LLM is available.

    Engines are only added when their dependencies are present: the embedding
    tier needs ``store`` + ``embedder``, the LLM tier needs ``llm``. With no
    store and no LLM, the cascade degrades to the heuristic engine alone.

    ``threshold`` is the cost-vs-quality dial (RFC-0017): raise it to escalate
    to the LLM sooner, lower it to let the embedding tier answer more often.
    The right value depends on the embedder. The default ``HashEmbedder`` is
    biased toward high cosine scores (unrelated phrases score ~0.6-0.8), so a
    conservative ``0.9`` is used to only accept near-identical matches; a real
    semantic embedder (e.g. ``OpenAIEmbeddingLLM``) supports lower thresholds
    like ``0.7`` for paraphrase matching.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0.0 and 1.0")

    engines: list[IntentEngine] = [HeuristicIntentEngine(tuple(rules or DEFAULT_RULES))]
    if store is not None and embedder is not None:
        engines.append(EmbeddingIntentEngine(store, embedder=embedder))
    if llm is not None:
        engines.append(LLMIntentEngine(llm=llm))
    if len(engines) == 1:
        return engines[0]
    return CascadeIntentEngine(
        *engines,
        fallback=fallback,
        confidence_threshold=threshold,
        default_target=default_target,
    )

"""Intent engine providers for the IntentEngine contract (RFC-0016).

Phase 0 shipped the dependency-free :class:`HeuristicIntentEngine`; Phase 1
adds :class:`LLMIntentEngine`, :class:`EmbeddingIntentEngine`, and the
confidence-gated :class:`CascadeIntentEngine`. RFC-0017 (M8) adds
:func:`build_intent_cascade` for assembling the recommended
Heuristic → Embedding → LLM stack.
"""

from .cascade import CascadeIntentEngine
from .embedding import EmbeddingIntentEngine
from .factory import DEFAULT_RULES, build_intent_cascade
from .heuristic import HeuristicIntentEngine, IntentRule
from .llm import LLMIntentEngine

__all__ = [
    "CascadeIntentEngine",
    "DEFAULT_RULES",
    "EmbeddingIntentEngine",
    "HeuristicIntentEngine",
    "IntentRule",
    "LLMIntentEngine",
    "build_intent_cascade",
]

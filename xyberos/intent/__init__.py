"""Intent engine providers for the IntentEngine contract (RFC-0016).

Phase 0 shipped the dependency-free :class:`HeuristicIntentEngine`; Phase 1
adds :class:`LLMIntentEngine`, :class:`EmbeddingIntentEngine`, and the
confidence-gated :class:`CascadeIntentEngine`.
"""

from .cascade import CascadeIntentEngine
from .embedding import EmbeddingIntentEngine
from .heuristic import HeuristicIntentEngine, IntentRule
from .llm import LLMIntentEngine

__all__ = [
    "CascadeIntentEngine",
    "EmbeddingIntentEngine",
    "HeuristicIntentEngine",
    "IntentRule",
    "LLMIntentEngine",
]

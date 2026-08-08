"""Intent engine providers for the IntentEngine contract (RFC-0016).

Phase 0 ships the dependency-free :class:`HeuristicIntentEngine`; LLM-driven,
embedding-based, and cascade engines follow in Phase 1.
"""

from .heuristic import HeuristicIntentEngine, IntentRule

__all__ = ["HeuristicIntentEngine", "IntentRule"]

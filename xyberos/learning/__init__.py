"""Learning layer for the trainable engines (RFC-0016).

``filters`` provides the promote/demote signals, ``promoter`` automates
feeding successful episodes back into the trainable providers, and
``KnowledgePromoter`` grows the knowledge base from rated answers (RFC-0018,
M6).
"""

from .filters import demote_failed, promote_successful, to_examples
from .knowledge import KnowledgePromoter
from .promoter import ExamplePromoter

__all__ = [
    "ExamplePromoter",
    "KnowledgePromoter",
    "demote_failed",
    "promote_successful",
    "to_examples",
]

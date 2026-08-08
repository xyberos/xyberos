"""Learning layer for the trainable engines (RFC-0016).

``filters`` provides the promote/demote signals and ``promoter`` automates
feeding successful episodes back into the trainable providers.
"""

from .filters import demote_failed, promote_successful, to_examples
from .promoter import ExamplePromoter

__all__ = ["ExamplePromoter", "demote_failed", "promote_successful", "to_examples"]

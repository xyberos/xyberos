"""Vector store extension contract introduced by RFC-0016 (Phase 0).

Vector stores give Memory, Knowledge, Intent, and Planner providers a semantic
retrieval substrate so they can "learn by accumulation": adding an item improves
retrieval without any retraining. The contract intentionally depends on
``object``/plain data (not Runtime's Context type), matching every other
extension contract so providers stay independent of core layers.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScoredHit:
    """One ranked result from a :class:`VectorStore` query.

    ``score`` is provider-defined but higher must mean more relevant (e.g.
    cosine similarity). ``payload`` carries whatever application data was
    attached at ``upsert`` time.
    """

    id: str
    score: float
    payload: Mapping[str, Any] | None = None


class VectorStore(ABC):
    """Stores named vectors in namespaces and retrieves them by similarity.

    Namespaces are independent buckets (e.g. one for memory turns, one for
    knowledge facts, one for intent examples) so a single store can back
    several subsystems without collisions.
    """

    @abstractmethod
    def upsert(
        self,
        namespace: str,
        id: str,
        vector: Sequence[float],
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        """Insert or replace ``id`` in ``namespace`` with ``vector``."""

    @abstractmethod
    def query(
        self,
        namespace: str,
        vector: Sequence[float],
        *,
        top_k: int = 5,
        threshold: float | None = None,
    ) -> list[ScoredHit]:
        """Return the ``top_k`` nearest vectors, best score first.

        ``threshold`` optionally filters out hits with a score below it.
        """

    @abstractmethod
    def delete(self, namespace: str, id: str) -> None:
        """Remove ``id`` from ``namespace``."""

    @abstractmethod
    def clear(self, namespace: str) -> None:
        """Remove every vector stored under ``namespace``."""

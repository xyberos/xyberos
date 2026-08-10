"""Stratified memory: durable facts vs episodic history (RFC-0018, M7)."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import Any
from uuid import uuid4

from ..contracts.memory import Memory
from ..contracts.vector import VectorStore
from ..llm.embeddings import embed_text
from .in_memory import InMemoryMemory

# A fact extractor turns a ``(prompt, response)`` turn into a list of facts.
FactExtractor = Callable[[Any, Any], Sequence[str]]

_FACT_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bmy ([^.,;]+) is ([^.,;]+)", "user {0}: {1}"),
    (r"\bi am (?:from|based in) ([^.,;]+)", "user location: {0}"),
    (r"\bremember (?:that )?([^.,;]+)", "remembered: {0}"),
)


def extract_facts_deterministic(prompt: Any, response: Any) -> list[str]:
    """Rule-based durable-fact extraction over the user turn (LLM-free).

    Captures explicit, self-describing statements — ``my X is Y``, ``I am
    from X``, ``remember that X`` — so preferences/decisions can be stored as
    durable facts while raw transcripts stay in episodic memory. An LLM-based
    extractor can be swapped in for richer extraction.
    """
    if not isinstance(prompt, str):
        return []
    lower = prompt.lower()
    facts: list[str] = []
    for pattern, template in _FACT_PATTERNS:
        for match in re.finditer(pattern, lower):
            groups = [group.strip() for group in match.groups() if group]
            if groups:
                facts.append(template.format(*groups))
    return facts


class StratifiedMemory(Memory):
    """Separate durable facts from episodic history (RFC-0018, M7).

    Wraps an inner :class:`Memory` that keeps raw episodic transcripts and
    maintains a separate facts namespace in a :class:`VectorStore`. When a
    turn is stored, durable facts are extracted — by an LLM ``extract_facts``
    callable when supplied, otherwise by the deterministic rule-based
    extractor — and indexed as facts.

    :meth:`retrieve` delegates to the inner memory (episodes), so Brain
    behavior is unchanged; :meth:`facts` returns the most relevant durable
    facts, which template responders can inject as context (RFC-0017, M5).
    """

    def __init__(
        self,
        inner: Memory | None = None,
        store: VectorStore | None = None,
        *,
        embedder: Any | None = None,
        namespace: str = "facts",
        top_k: int = 5,
        extract_facts: FactExtractor | None = None,
    ) -> None:
        if store is None:
            raise ValueError("store is required for the facts namespace")
        if not isinstance(store, VectorStore):  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
            raise TypeError("store must be a VectorStore")
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")
        self._inner = inner or InMemoryMemory()
        self._store = store
        self._embedder = embedder
        self._namespace = namespace
        self._top_k = top_k
        self._extract_facts = extract_facts or extract_facts_deterministic

    def store(self, context: object) -> None:
        """Store the episode and index any durable facts it contains."""
        self._inner.store(context)
        prompt = getattr(context, "prompt", None)
        response = getattr(context, "response", None)
        for fact in self._extract_facts(prompt, response):
            self._add_fact(fact)

    def retrieve(self, context: object) -> Any:
        """Return episodic history from the wrapped memory."""
        return self._inner.retrieve(context)

    def facts(self, context: object, *, threshold: float = 0.0) -> list[str]:
        """Return the most relevant durable facts for ``context``.

        ``threshold`` filters out low-similarity facts; raise it to only inject
        highly relevant facts (e.g. into template context).
        """
        prompt = getattr(context, "prompt", None)
        if not isinstance(prompt, str) or not prompt or self._embedder is None:
            return []
        vector = embed_text(self._embedder, prompt)
        hits = self._store.query(self._namespace, vector, top_k=self._top_k, threshold=threshold)
        return [str((hit.payload or {}).get("fact")) for hit in hits]

    def clear_facts(self) -> None:
        """Drop every indexed durable fact."""
        self._store.clear(self._namespace)

    def _add_fact(self, fact: str) -> None:
        vector = embed_text(self._embedder, fact)
        self._store.upsert(
            self._namespace,
            uuid4().hex,
            vector,
            payload={"fact": fact},
        )

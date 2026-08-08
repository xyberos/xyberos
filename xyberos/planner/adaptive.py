"""Few-shot adaptive planning over a VectorStore (RFC-0016, Phase 1)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import uuid4

from ..contracts.planner import Planner
from ..contracts.vector import VectorStore
from ..llm import EchoLLM, LLMProvider
from ..llm.embeddings import embed_text
from .llm import LLMPlanner

_INSTRUCTION = (
    "Break the following request into a short, ordered plan. "
    "Return one step per line with no numbering or bullet prefixes.\n\n"
)


class AdaptivePlanner(Planner):
    """LLM planner that few-shot learns from past ``request -> plan`` examples.

    When a :class:`VectorStore` and embedder are provided, ``plan`` retrieves the
    ``top_k`` most similar past requests, renders their plans as demonstrations,
    and asks the LLM to follow that style. ``learn(request, plan)`` records a new
    example so the planner improves by accumulation — no retraining.
    """

    def __init__(
        self,
        llm: LLMProvider | None = None,
        *,
        parse: Callable[[str], Any] | None = None,
        store: VectorStore | None = None,
        embedder: Any | None = None,
        namespace: str = "plans",
        top_k: int = 3,
    ) -> None:
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")
        self._llm = llm or EchoLLM()
        self._parse = parse or LLMPlanner._default_parse
        self._store = store
        self._embedder = embedder
        self._namespace = namespace
        self._top_k = top_k

    def plan(self, context: object) -> Any:
        request = getattr(context, "prompt", "")
        instruction = _INSTRUCTION
        examples = self._retrieve_examples(request)
        if examples:
            instruction += (
                "Here are examples of how similar requests were planned:\n" + examples + "\n\n"
            )
        instruction += f"Request: {request}"
        response = self._llm.generate(instruction)
        if not isinstance(response, str):
            raise TypeError("LLM must return a string")
        return self._parse(response)

    def learn(self, request: str, plan: Any) -> None:
        """Record a ``request -> plan`` example for future few-shot retrieval."""
        if self._store is None or self._embedder is None:
            return
        vector = embed_text(self._embedder, request)
        self._store.upsert(
            self._namespace,
            uuid4().hex,
            vector,
            payload={"request": request, "plan": plan},
        )

    def _retrieve_examples(self, request: str) -> str:
        if self._store is None or self._embedder is None or not request:
            return ""
        vector = embed_text(self._embedder, request)
        hits = self._store.query(self._namespace, vector, top_k=self._top_k)
        lines = []
        for hit in hits:
            payload = hit.payload or {}
            plan = payload.get("plan")
            plan_text = (
                "\n".join(f"- {step}" for step in plan)
                if isinstance(plan, (list, tuple))
                else str(plan)
            )
            lines.append(f"Request: {payload.get('request', '')}\nPlan:\n{plan_text}")
        return "\n\n".join(lines)

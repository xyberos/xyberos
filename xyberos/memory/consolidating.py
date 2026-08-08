"""LLM-consolidating memory wrapper (RFC-0016, Phase 1)."""

from __future__ import annotations

from typing import Any

from ..contracts.memory import Memory
from ..llm import LLMProvider
from .in_memory import InMemoryMemory
from .sqlite import MemoryEntry

_SUMMARY_PROMPT = (
    "Condense the following conversation turns into a short memory summary "
    "that preserves important facts, decisions, and user preferences. "
    "Respond with plain prose.\n\n{transcript}"
)


class ConsolidatingMemory(Memory):
    """Wrap another Memory and periodically consolidate old turns.

    After ``interval`` stored turns, the oldest turns are collapsed into a
    single summary entry — LLM-written when an LLM is supplied, otherwise a
    deterministic transcript digest — while the most recent ``keep`` turns are
    retained verbatim. This bounds history growth while preserving the gist of
    older context.
    """

    def __init__(
        self,
        inner: Memory | None = None,
        *,
        llm: LLMProvider | None = None,
        interval: int = 50,
        keep: int = 10,
        summary_prompt: str | None = None,
    ) -> None:
        if interval <= 0 or keep <= 0:
            raise ValueError("interval and keep must be positive integers")
        if keep >= interval:
            raise ValueError("keep must be smaller than interval")
        self._inner = inner or InMemoryMemory()
        self._llm = llm
        self._interval = interval
        self._keep = keep
        self._summary_prompt = summary_prompt or _SUMMARY_PROMPT
        self._count = 0

    def retrieve(self, context: object) -> Any:
        """Delegate retrieval to the wrapped memory."""
        return self._inner.retrieve(context)

    def store(self, context: object) -> None:
        self._inner.store(context)
        self._count += 1
        if self._count >= self._interval:
            self._consolidate()
            self._count = 0

    def _consolidate(self) -> None:
        entries = list(self._inner.retrieve(object()) or [])
        if len(entries) <= self._keep:
            return
        old = entries[: -self._keep]
        recent = entries[-self._keep :]
        summary = self._summarize(old)
        if hasattr(self._inner, "clear"):
            self._inner.clear()
        self._inner.store(MemoryEntry(prompt="[consolidated]", response=summary))
        for entry in recent:
            self._inner.store(entry)

    def _summarize(self, entries: list[Any]) -> str:
        transcript = "\n\n".join(self._format_entries(entries))
        if self._llm is None:
            prompts = [getattr(entry, "prompt", None) for entry in entries]
            snippets = [p[:40] for p in prompts if isinstance(p, str) and p]
            return "Summarized history: " + (" | ".join(snippets) if snippets else "(empty)")
        return self._llm.generate(self._summary_prompt.format(transcript=transcript))

    @staticmethod
    def _format_entries(entries: list[Any]) -> list[str]:
        lines = []
        for entry in entries:
            user = getattr(entry, "prompt", None)
            assistant = getattr(entry, "response", None)
            line = f"user: {user}" if user is not None else ""
            if assistant is not None:
                line = f"{line}\nassistant: {assistant}" if line else f"assistant: {assistant}"
            lines.append(line if line else str(entry))
        return lines

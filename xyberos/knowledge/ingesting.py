"""Knowledge ingestion over chunks (RFC-0016, Phase 1)."""

from __future__ import annotations

from uuid import uuid4

from .vector import VectorKnowledge


class IngestingKnowledge(VectorKnowledge):
    """A :class:`VectorKnowledge` that can ingest raw documents as chunked facts."""

    def ingest(self, text: str, *, chunk_size: int = 512) -> int:
        """Split ``text`` into chunks and index each as a fact; return count."""
        chunks = _chunk_text(text, chunk_size)
        for chunk in chunks:
            self.add(uuid4().hex, chunk)
        return len(chunks)


def _chunk_text(text: str, chunk_size: int) -> list[str]:
    """Split ``text`` into paragraph-aware chunks of at most ``chunk_size`` chars."""
    text = text.strip()
    if not text:
        return []
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    chunks: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= chunk_size:
            chunks.append(paragraph)
        else:
            chunks.extend(_hard_split(paragraph, chunk_size))
    return chunks


def _hard_split(text: str, size: int) -> list[str]:
    return [text[index : index + size] for index in range(0, len(text), size)]

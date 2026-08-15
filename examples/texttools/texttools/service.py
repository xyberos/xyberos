"""Text utility tools contributed by the ``texttools`` plugin.

These are dependency-free, pure-Python helpers that demonstrate the
:class:`~xyberos.contracts.Tool` contract: a stable ``name`` plus an
``execute(context, **arguments)`` that returns a structured result.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from xyberos.contracts import Tool

__all__ = ["CountWordsTool", "EchoTool", "SlugifyTool"]


def _as_text(value: Any) -> str:
    """Coerce a tool argument to text (``None`` -> empty string)."""
    return "" if value is None else str(value)


class CountWordsTool(Tool):
    """Count the words in a piece of text."""

    @property
    def name(self) -> str:
        return "count_words"

    def execute(self, context: object, **arguments: Any) -> Any:
        text = _as_text(arguments.get("text"))
        return {"text": text, "words": len(re.findall(r"[\w']+", text, flags=re.UNICODE))}


class SlugifyTool(Tool):
    """Turn arbitrary text into a URL-safe ASCII slug."""

    @property
    def name(self) -> str:
        return "slugify"

    def execute(self, context: object, **arguments: Any) -> Any:
        text = _as_text(arguments.get("text"))
        ascii_text = (
            unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        )
        ascii_text = re.sub(r"[^a-zA-Z0-9\s-]", "", ascii_text).strip().lower()
        return {"slug": re.sub(r"[\s_-]+", "-", ascii_text)}


class EchoTool(Tool):
    """Return the input text unchanged (useful for verifying tool wiring)."""

    @property
    def name(self) -> str:
        return "echo"

    def execute(self, context: object, **arguments: Any) -> Any:
        return {"echo": _as_text(arguments.get("text"))}

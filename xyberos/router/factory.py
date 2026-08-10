"""Factory for assembling the recommended hybrid responder chain (RFC-0017)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..contracts.responder import Responder, Template
from .cache import CacheResponder
from .chain import ResponderChain
from .degraded import DegradedResponder
from .knowledge import KnowledgeResponder
from .llm import LLMResponder
from .memory import MemoryResponder
from .template import TemplateResponder
from .tool import ToolResponder


def build_router(
    *,
    llm: Any | None = None,
    tool_runner: Any | None = None,
    knowledge: Any | None = None,
    memory: Any | None = None,
    cache: CacheResponder | None = None,
    cache_store: Any | None = None,
    cache_embedder: Any | None = None,
    templates: Iterable[Template] | None = None,
    fallback: Responder | Any | None = None,
    degrade: str = "refusal",
    capabilities: Iterable[str] | None = None,
) -> ResponderChain:
    """Assemble the recommended hybrid responder chain, cheapest-first.

    Order (RFC-0017): Template → Tool → Knowledge → Memory → Cache → LLM, with
    an actionable :class:`DegradedResponder` as the final fallback (which only
    fires when no LLM tier is present, since the LLM always answers).

    Tiers are only added when their dependencies are supplied:

    * ``templates`` → ``TemplateResponder``
    * ``tool_runner`` → ``ToolResponder``
    * ``knowledge`` → ``KnowledgeResponder``
    * ``memory`` → ``MemoryResponder``
    * ``cache`` (or ``cache_store`` + ``cache_embedder``) → ``CacheResponder``
    * ``llm`` → ``LLMResponder``

    ``fallback`` defaults to a ``DegradedResponder``; pass any ``Responder`` or
    ``context -> answer`` callable to override it.
    """
    responders: list[tuple[str, Responder]] = []
    if templates:
        responders.append(("template", TemplateResponder(templates)))
    if tool_runner is not None:
        responders.append(("tool", ToolResponder(tool_runner)))
    if knowledge is not None:
        responders.append(("knowledge", KnowledgeResponder(knowledge)))
    if memory is not None:
        responders.append(("memory", MemoryResponder(memory)))
    if cache is not None:
        responders.append(("cache", cache))
    elif cache_store is not None:
        responders.append(("cache", CacheResponder(cache_store, embedder=cache_embedder)))
    if llm is not None:
        responders.append(("llm", LLMResponder(llm)))

    final: Responder | Any
    if fallback is not None:
        final = fallback
    else:
        final = DegradedResponder(degrade, capabilities=capabilities)
    return ResponderChain(responders, fallback=final)

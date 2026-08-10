"""Agent-to-agent message contract and helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..runtime.context import CognitiveContext


# Context metadata key where agents queue pending messages for the runtime.
MESSAGES_KEY = "xyberos.messages"


def _empty_metadata() -> dict[str, Any]:
    """A fresh metadata dict for each Message instance."""
    return {}


@dataclass(frozen=True)
class Message:
    """An immutable message exchanged between agents.

    ``recipient`` is a registered agent name, or ``"*"`` to broadcast to every
    agent. A message with ``kind == "handoff"`` transfers control to
    ``recipient`` — the runtime runs that agent next.
    """

    sender: str
    recipient: str
    content: Any = None
    kind: str = "message"
    metadata: dict[str, Any] = field(default_factory=_empty_metadata)


def handoff(target: str, content: Any = None, *, sender: str = "") -> Message:
    """Build a ``handoff`` message directing control to ``target``."""
    return Message(sender=sender, recipient=target, content=content, kind="handoff")


def post(context: CognitiveContext, message: Message) -> None:
    """Queue ``message`` for the runtime to route after the current agent runs.

    Call this from inside an agent's ``run`` to send a message or request a
    handoff. The runtime records the message, delivers it to recipients that
    implement ``receive(message)``, and follows handoffs.
    """
    context.metadata.setdefault(MESSAGES_KEY, []).append(message)

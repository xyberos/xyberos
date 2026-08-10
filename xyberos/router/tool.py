"""Tool-based responder — tier 2 of the hybrid chain (RFC-0017, M10)."""

from __future__ import annotations

from typing import Any

from ..contracts.responder import Responder


class ToolResponder(Responder):
    """Wrap a :class:`~tools.ToolRunner` as a formal router tier.

    Runs a tool only when there is a *genuine* match:

    * the classified intent's ``target`` names a registered tool, or
    * a registered tool name appears in the request prompt.

    Otherwise returns ``None`` so the chain escalates to the next tier.

    ``ToolRunner.dispatch`` is deliberately not wrapped unconditionally: its
    ``choose`` falls back to the *first registered tool* when nothing matches,
    which would run an arbitrary tool for every request. This responder gates
    on a real match first (RFC-0017, M10).
    """

    def __init__(self, tool_runner: Any) -> None:
        self._tool_runner = tool_runner

    @property
    def tool_runner(self) -> Any:
        """The wrapped tool runner."""
        return self._tool_runner

    def respond(self, context: object) -> Any | None:
        """Dispatch the matching tool, or return ``None`` to escalate."""
        if not self._matches(context):
            return None
        try:
            return self._tool_runner.dispatch(context)
        except ValueError:
            return None

    def confidence(self, context: object) -> float:
        """``1.0`` when a tool genuinely matches, ``0.0`` otherwise."""
        return 1.0 if self._matches(context) else 0.0

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #

    def _matches(self, context: object) -> bool:
        """Whether a registered tool is a genuine match for this request."""
        names = self._tool_runner.names
        if not names:
            return False

        intent = getattr(context, "intent", None)
        target = getattr(intent, "target", None)
        if target and target in names:
            return True

        prompt = getattr(context, "prompt", None)
        if isinstance(prompt, str):
            return any(name and name in prompt for name in names)
        return False

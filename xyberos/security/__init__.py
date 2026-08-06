"""Security service for Xyberos — kill switch, guardrails, and audit logging.

Provides a Kernel-level security layer that gates every request through the
Runtime and Brain pipelines.

Example::

    from xyberos.security import KillSwitch, Security, Guardrail

    security = Security()
    security.add_guardrail(Guardrail("block-threats", lambda ctx: "hack" not in ctx.prompt))

    # Engage kill switch to halt all processing:
    security.kill_switch.engage("emergency maintenance")

    # Check before processing:
    security.kill_switch.check()  # raises SecurityHaltError if active
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from typing import Any

from ..contracts.service import Service
from ..events.names import (
    SECURITY_GUARDRAIL_TRIGGERED,
    SECURITY_KILL_DISENGAGED,
    SECURITY_KILL_ENGAGED,
    SECURITY_REQUEST_BLOCKED,
)
from ..exceptions.security import GuardrailTriggeredError, SecurityHaltError


class KillSwitch:
    """A safety gate that can halt all pipeline processing.

    When ``active`` is ``True``:

    - **soft** mode: new requests are rejected; in-flight requests complete.
    - **hard** mode: all requests are rejected, including in-flight.

    The switch must be explicitly disengaged — it never auto-recovers.
    """

    def __init__(self) -> None:
        self._active = False
        self._mode: str = "soft"
        self._reason: str | None = None
        self._activated_at: float | None = None

    # -- public read-only properties ------------------------------------------

    @property
    def active(self) -> bool:
        """``True`` when the kill switch is engaged."""
        return self._active

    @property
    def mode(self) -> str:
        """The current kill mode: ``"soft"`` or ``"hard"``."""
        return self._mode

    @property
    def reason(self) -> str | None:
        """Human-readable reason the switch was engaged, if any."""
        return self._reason

    @property
    def activated_at(self) -> float | None:
        """POSIX timestamp of when the switch was engaged, if ever."""
        return self._activated_at

    # -- actions --------------------------------------------------------------

    def engage(self, reason: str = "", *, mode: str = "soft") -> None:
        """Activate the kill switch, blocking future requests.

        Args:
            reason: Human-readable explanation for the kill.
            mode: ``"soft"`` (reject new only) or ``"hard"`` (reject all).
        """
        if mode not in ("soft", "hard"):
            raise ValueError("mode must be 'soft' or 'hard'")
        self._active = True
        self._mode = mode
        self._reason = reason or None
        self._activated_at = time.time()

    def disengage(self) -> None:
        """Deactivate the kill switch, allowing requests again."""
        self._active = False
        self._mode = "soft"
        self._reason = None
        self._activated_at = None

    def check(self) -> None:
        """Raise :class:`SecurityHaltError` if the kill switch is active.

        Callers should invoke this at every gating point (Runtime entry, each
        Brain pipeline stage).
        """
        if self._active:
            raise SecurityHaltError(self._reason or "kill switch is active")

    def __repr__(self) -> str:
        state = "ACTIVE" if self._active else "inactive"
        extra = f" mode={self._mode}" if self._active else ""
        reason = f" reason={self._reason!r}" if self._reason else ""
        return f"KillSwitch({state}{extra}{reason})"


class Guardrail:
    """A named content filter that inspects contexts before or after processing.

    A guardrail callable receives the ``CognitiveContext`` and should raise
    :class:`GuardrailTriggeredError` (or return ``False``) to block the
    request.
    """

    def __init__(self, name: str, check: Callable[[object], bool]) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("guardrail name must be a non-empty string")
        if not callable(check):
            raise TypeError("guardrail check must be callable")
        self.name = name
        self._check = check

    def inspect(self, context: object) -> bool:
        """Return ``True`` if the context passes this guardrail.

        Returns:
            ``True`` if the context is safe; ``False`` or raises if blocked.
        """
        return self._check(context)

    def __repr__(self) -> str:
        return f"Guardrail({self.name!r})"


class Security(Service):
    """Kernel-level security service: kill switch, guardrails, and audit log.

    Registered with the Kernel as ``"security"``. The Runtime and Brain check
    it at every gating point::

        security = kernel.resolve("security")
        security.kill_switch.check()
        security.guard(context)
    """

    def __init__(self) -> None:
        self.kill_switch = KillSwitch()
        self._guardrails: dict[str, Guardrail] = {}
        self._audit_log: list[dict[str, Any]] = []
        self._events: object = None  # set by Kernel after registration

    # -- guardrails -----------------------------------------------------------

    def add_guardrail(self, guardrail: Guardrail) -> Guardrail:
        """Register a content guardrail."""
        if not isinstance(guardrail, Guardrail):
            raise TypeError("guardrail must be a Guardrail instance")
        self._guardrails[guardrail.name] = guardrail
        return guardrail

    def remove_guardrail(self, name: str) -> Guardrail:
        """Remove and return a previously registered guardrail."""
        if name not in self._guardrails:
            raise KeyError(f"no guardrail named '{name}'")
        return self._guardrails.pop(name)

    @property
    def guardrail_names(self) -> tuple[str, ...]:
        """Names of all registered guardrails."""
        return tuple(self._guardrails)

    def guard(self, context: object) -> None:
        """Run all guardrails against *context*.

        Raises:
            GuardrailTriggeredError: if any guardrail blocks the context.
        """
        for guardrail in self._guardrails.values():
            try:
                passed = guardrail.inspect(context)
            except GuardrailTriggeredError:
                self._audit("guardrail_triggered", guardrail=guardrail.name)
                raise
            if not passed:
                self._audit("guardrail_triggered", guardrail=guardrail.name)
                raise GuardrailTriggeredError(guardrail.name)

    # -- audit log ------------------------------------------------------------

    def _audit(self, event: str, **extra: object) -> None:
        entry = {
            "event": event,
            "timestamp": time.time(),
            "kill_switch_active": self.kill_switch.active,
            **extra,
        }
        self._audit_log.append(entry)

    @property
    def audit_log(self) -> tuple[dict[str, Any], ...]:
        """All recorded security audit entries, in order."""
        return tuple(self._audit_log)

    # -- kill switch event helpers --------------------------------------------

    def _emit(self, event_name: str, **data: object) -> None:
        """Emit a security event if an event bus is attached."""
        if self._events is not None:
            bus = self._events
            bus.emit(event_name, context=None, data=data)  # type: ignore[union-attr]

    def engage_kill_switch(self, reason: str = "", *, mode: str = "soft") -> None:
        """Engage the kill switch and emit a security event."""
        self.kill_switch.engage(reason, mode=mode)
        self._audit("kill_engaged", reason=reason, mode=mode)
        self._emit(SECURITY_KILL_ENGAGED, reason=reason, mode=mode)

    def disengage_kill_switch(self) -> None:
        """Disengage the kill switch and emit a security event."""
        self.kill_switch.disengage()
        self._audit("kill_disengaged")
        self._emit(SECURITY_KILL_DISENGAGED)

    def block_request(self, context: object) -> None:
        """Record and raise a blocked-request security event."""
        self._audit("request_blocked")
        self._emit(SECURITY_REQUEST_BLOCKED)
        self.kill_switch.check()  # raises SecurityHaltError

    # -- Service contract -----------------------------------------------------

    @property
    def name(self) -> str:
        return "security"

    def __repr__(self) -> str:
        guards = len(self._guardrails)
        return f"Security(kill={self.kill_switch}, guardrails={guards}, audit_entries={len(self._audit_log)})"

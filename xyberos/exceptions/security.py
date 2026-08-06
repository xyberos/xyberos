"""Security-related domain exceptions for Xyberos."""


class SecurityError(Exception):
    """Base exception for all security-related errors."""


class SecurityHaltError(SecurityError):
    """Raised when the kill switch is active and a request is blocked."""

    def __init__(self, reason: str = "") -> None:
        self.reason = reason
        super().__init__(f"Security halt: {reason}" if reason else "Security halt: kill switch is active")


class GuardrailTriggeredError(SecurityError):
    """Raised when a content guardrail blocks a prompt or response."""

    def __init__(self, guard_name: str, detail: str = "") -> None:
        self.guard_name = guard_name
        self.detail = detail
        msg = f"Guardrail '{guard_name}' triggered"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)

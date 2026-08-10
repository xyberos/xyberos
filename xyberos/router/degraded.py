"""Actionable degradation fallback (RFC-0017, M12/M14)."""

from __future__ import annotations

from collections.abc import Iterable

from ..contracts.responder import Responder


class DegradedResponder(Responder):
    """A last-resort fallback that offers a path forward, not a dead end.

    Designed to be passed as the :class:`~router.ResponderChain` ``fallback``
    (its confidence is 0.0, so it is never a gated tier). Returns a
    policy-controlled message that lists available capabilities and offers next
    steps — rephrase, connect to a human, or browse known topics.
    """

    POLICIES = {
        "offline": (
            "I'm currently unable to connect to my language model. "
            "Here's what I can still help with:\n{available_capabilities}\n\n"
            "You can also try rephrasing your request, or type 'agent' "
            "to connect with a human."
        ),
        "refusal": (
            "I wasn't able to find a good answer for that. "
            "Could you try asking in a different way? "
            "I can help with: {available_capabilities}."
        ),
        "human": (
            "Let me connect you with someone who can help. "
            "In the meantime, I can also point you to: {available_capabilities}."
        ),
    }

    def __init__(
        self,
        policy: str = "refusal",
        *,
        capabilities: Iterable[str] | None = None,
    ) -> None:
        if policy not in self.POLICIES:
            raise ValueError(f"unknown policy {policy!r}; choose from {sorted(self.POLICIES)}")
        self._policy = policy
        self._capabilities = tuple(capabilities or ())

    @property
    def policy(self) -> str:
        """The configured degradation policy."""
        return self._policy

    def respond(self, context: object) -> str:
        """Return the policy message with available capabilities filled in."""
        template = self.POLICIES[self._policy]
        caps = ", ".join(self._capabilities) if self._capabilities else "general assistance"
        return template.format(available_capabilities=caps)

    def confidence(self, context: object) -> float:
        """Always 0.0 — the degraded responder is the chain's fallback, not a tier."""
        return 0.0

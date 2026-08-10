"""A ready-made agent with a role and optional message handling."""

from __future__ import annotations

from collections.abc import Callable

from ..contracts.agent import Agent
from ..runtime.context import CognitiveContext
from .messages import Message


class RoleAgent(Agent):
    """A named agent with a role and optional run/message handlers.

    Lets you build role-based, collaborative agents without subclassing::

        writer = RoleAgent("writer", role="editor", run=write_step, receive=on_message)
        runtime = MultiAgentRuntime([writer])
    """

    def __init__(
        self,
        name: str,
        role: str,
        run: Callable[[CognitiveContext], CognitiveContext | None] | None = None,
        receive: Callable[[Message], None] | None = None,
    ) -> None:
        # Defensive runtime guards for untyped callers; the annotations already
        # guarantee these types for type-checked callers.
        if not isinstance(name, str) or not name.strip():  # type: ignore[unnecessary-isinstance]
            raise ValueError("agent name must be a non-empty string")
        if not isinstance(role, str) or not role.strip():  # type: ignore[unnecessary-isinstance]
            raise ValueError("agent role must be a non-empty string")
        if run is not None and not callable(run):
            raise TypeError("run must be callable")
        if receive is not None and not callable(receive):
            raise TypeError("receive must be callable")
        self._name = name
        self._role = role
        self._run = run
        self._receive = receive

    @property
    def name(self) -> str:
        """The stable agent identifier."""
        return self._name

    @property
    def role(self) -> str:
        """The agent's role within the group."""
        return self._role

    def run(self, context: object) -> object:
        """Invoke the run handler, or return the context unchanged."""
        if not isinstance(context, CognitiveContext):
            raise TypeError("context must be a CognitiveContext")
        if self._run is None:
            return context
        result = self._run(context)
        if result is None:
            return context
        # Defensive: a handler may ignore its return type at runtime.
        if not isinstance(result, CognitiveContext):  # type: ignore[unnecessary-isinstance]
            raise TypeError("run handler must return a CognitiveContext or None")
        return result

    def receive(self, message: Message) -> None:
        """Process an inbound message (no-op when no handler is configured)."""
        if self._receive is not None:
            self._receive(message)

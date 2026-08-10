"""Sequential coordination for multiple cognitive agents."""

from collections.abc import Iterable

from ..contracts.agent import Agent
from ..exceptions.agent import (
    AgentAlreadyRegisteredError,
    AgentNotFoundError,
    HandoffLoopError,
)
from ..runtime.context import CognitiveContext
from .messages import MESSAGES_KEY, Message


class MultiAgentRuntime:
    """Run named agents with messaging, handoffs, and role-based coordination.

    Agents execute in registration order (or a selected order) against one
    canonical context. An agent may queue :class:`Message` objects with
    :func:`~agents.messages.post`; the runtime records each message, delivers
    it to recipients that implement ``receive(message)``, and follows
    ``handoff`` messages by running the recipient next (chained, up to
    ``max_handoffs``). Agents without any messaging are unaffected, so the
    runtime remains a plain sequential runner for them.
    """

    def __init__(
        self,
        agents: Iterable[Agent] = (),
        *,
        max_handoffs: int = 100,
    ) -> None:
        if max_handoffs < 1:
            raise ValueError("max_handoffs must be a positive integer")
        self._max_handoffs = max_handoffs
        self._agents: dict[str, Agent] = {}
        self._messages: list[Message] = []
        for agent in agents:
            self.register(agent)

    @property
    def names(self) -> tuple[str, ...]:
        """Agent names in execution order."""
        return tuple(self._agents)

    @property
    def messages(self) -> tuple[Message, ...]:
        """All messages recorded so far, in order."""
        return tuple(self._messages)

    def register(self, agent: Agent) -> Agent:
        """Register an agent for subsequent coordinated runs."""
        # Defensive runtime guards for untyped callers; the annotations already
        # guarantee these types for type-checked callers.
        if not isinstance(agent, Agent):  # type: ignore[unnecessary-isinstance]
            raise TypeError("agent must implement the Agent contract")
        if not isinstance(agent.name, str) or not agent.name.strip():  # type: ignore[unnecessary-isinstance]
            raise ValueError("agent name must be a non-empty string")
        if agent.name in self._agents:
            raise AgentAlreadyRegisteredError(f"Agent is already registered: {agent.name}")
        self._agents[agent.name] = agent
        return agent

    def get(self, name: str) -> Agent:
        """Return a registered agent by name."""
        try:
            return self._agents[name]
        except KeyError as exc:
            raise AgentNotFoundError(f"No agent registered with name: {name}") from exc

    def remove(self, name: str) -> Agent:
        """Remove and return an agent without executing it."""
        self.get(name)
        return self._agents.pop(name)

    def role(self, name: str) -> str | None:
        """Return the optional ``role`` of a registered agent, or ``None``."""
        return getattr(self.get(name), "role", None)

    def send(self, message: Message) -> Message:
        """Record and deliver a message directly (e.g. from application code)."""
        self._record_and_deliver(message)
        return message

    def run(self, context: CognitiveContext, *, agent_names: Iterable[str] | None = None) -> CognitiveContext:
        """Run all or selected agents, following handoffs, and return the final context.

        Each agent runs at most once per call. When an agent emits a ``handoff``
        message, the recipient runs next (chained, up to ``max_handoffs``);
        handing off to an agent that already ran stops the chain.
        """
        # Runtime guard for untyped callers; type checkers treat it as redundant.
        if not isinstance(context, CognitiveContext):  # type: ignore[unnecessary-isinstance]
            raise TypeError("context must be a CognitiveContext")

        current = context
        sequence = tuple(agent_names) if agent_names is not None else self.names
        ran: set[str] = set()
        index = 0
        while index < len(sequence):
            name = sequence[index]
            index += 1
            if name in ran:
                continue
            current, handoff = self._run_agent(name, current)
            ran.add(name)

            hops = 0
            while handoff is not None:
                hops += 1
                if hops > self._max_handoffs:
                    raise HandoffLoopError(
                        f"too many handoffs while executing agent '{name}'"
                    )
                target = handoff.recipient
                if target not in self._agents:
                    raise AgentNotFoundError(f"Handoff target not registered: {target}")
                if target in ran:
                    break  # each agent runs at most once per run() call
                current, handoff = self._run_agent(target, current)
                ran.add(target)
        return current

    def _run_agent(self, name: str, context: CognitiveContext) -> tuple[CognitiveContext, Message | None]:
        """Execute one agent and route any messages it queued."""
        result = self.get(name).run(context)
        if not isinstance(result, CognitiveContext):
            raise TypeError("agents must return a CognitiveContext")
        return result, self._route(result)

    def _route(self, context: CognitiveContext) -> Message | None:
        """Record and deliver queued messages; return the last handoff, if any."""
        last_handoff: Message | None = None
        for message in context.metadata.pop(MESSAGES_KEY, []):
            self._record_and_deliver(message)
            if message.kind == "handoff":
                last_handoff = message
        return last_handoff

    def _record_and_deliver(self, message: Message) -> None:
        self._messages.append(message)
        self._deliver(message)

    def _deliver(self, message: Message) -> None:
        if message.recipient == "*":
            for agent in self._agents.values():
                self._try_receive(agent, message)
            return
        agent = self._agents.get(message.recipient)
        if agent is not None:
            self._try_receive(agent, message)

    @staticmethod
    def _try_receive(agent: Agent, message: Message) -> None:
        receive = getattr(agent, "receive", None)
        if callable(receive):
            try:
                receive(message)
            except Exception:  # noqa: BLE001 - message delivery is best-effort
                pass

"""Sequential coordination for multiple cognitive agents."""

from collections.abc import Iterable

try:
    from ..contracts.agent import Agent
    from ..exceptions.agent import AgentAlreadyRegisteredError, AgentNotFoundError
    from ..runtime.context import CognitiveContext
except ImportError:  # pragma: no cover - depends on import style
    from contracts.agent import Agent
    from exceptions.agent import AgentAlreadyRegisteredError, AgentNotFoundError
    from runtime.context import CognitiveContext


class MultiAgentRuntime:
    """Run named agents sequentially against one canonical context."""

    def __init__(self, agents: Iterable[Agent] = ()) -> None:
        self._agents: dict[str, Agent] = {}
        for agent in agents:
            self.register(agent)

    @property
    def names(self) -> tuple[str, ...]:
        """Agent names in execution order."""
        return tuple(self._agents)

    def register(self, agent: Agent) -> Agent:
        """Register an agent for subsequent coordinated runs."""
        if not isinstance(agent, Agent):
            raise TypeError("agent must implement the Agent contract")
        if not isinstance(agent.name, str) or not agent.name.strip():
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

    def run(self, context: object, *, agent_names: Iterable[str] | None = None) -> CognitiveContext:
        """Run all or selected agents in order and return the final context."""
        if not isinstance(context, CognitiveContext):
            raise TypeError("context must be a CognitiveContext")

        current = context
        names = tuple(agent_names) if agent_names is not None else self.names
        for name in names:
            result = self.get(name).run(current)
            if not isinstance(result, CognitiveContext):
                raise TypeError("agents must return a CognitiveContext")
            current = result
        return current

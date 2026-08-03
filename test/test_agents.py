import pytest

from agents import MultiAgentRuntime, RuntimeAgent
from contracts import Agent
from exceptions import AgentAlreadyRegisteredError, AgentNotFoundError
from runtime.context import CognitiveContext
from xyberos import create_app


class AnnotationAgent(Agent):
    def __init__(self, name, label):
        self._name = name
        self.label = label

    @property
    def name(self):
        return self._name

    def run(self, context):
        context.metadata.setdefault("agents", []).append(self.label)
        return context


class InvalidResultAgent(Agent):
    @property
    def name(self):
        return "invalid-result"

    def run(self, context):
        return "not a context"


def test_multi_agent_runtime_runs_agents_in_registration_order():
    first = AnnotationAgent("first", "one")
    second = AnnotationAgent("second", "two")
    runtime = MultiAgentRuntime([first, second])

    result = runtime.run(CognitiveContext("coordinate"))

    assert runtime.names == ("first", "second")
    assert result.metadata["agents"] == ["one", "two"]
    assert runtime.run(result, agent_names=["second"]).metadata["agents"] == ["one", "two", "two"]


def test_multi_agent_runtime_validates_agents_and_lookups():
    runtime = MultiAgentRuntime()
    agent = AnnotationAgent("worker", "work")
    runtime.register(agent)

    with pytest.raises(AgentAlreadyRegisteredError, match="already registered"):
        runtime.register(agent)
    with pytest.raises(AgentNotFoundError, match="No agent"):
        runtime.get("missing")
    with pytest.raises(TypeError, match="CognitiveContext"):
        runtime.run("not a context")
    assert runtime.remove("worker") is agent


def test_multi_agent_runtime_rejects_invalid_agent_results():
    runtime = MultiAgentRuntime([InvalidResultAgent()])

    with pytest.raises(TypeError, match="must return"):
        runtime.run(CognitiveContext("coordinate"))


def test_runtime_agent_and_public_app_share_existing_runtime_execution():
    app = create_app()
    agent = AnnotationAgent("audit", "audited")
    app.register_agent(agent)

    result = app.run_agents("hello", metadata={"request": "multi"})

    assert isinstance(app.agent, RuntimeAgent)
    assert app.resolve("agents") is app.agents
    assert result.response == "hello"
    assert result.metadata == {"request": "multi", "agents": ["audited"]}

    with pytest.raises(ValueError, match="non-empty"):
        RuntimeAgent("", app.runtime)
    with pytest.raises(TypeError, match="CognitiveContext"):
        app.agent.run("not a context")

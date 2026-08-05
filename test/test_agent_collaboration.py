"""Tests for multi-agent collaboration: messaging, handoffs, and roles."""

import pytest

from xyberos import create_app
from xyberos.agents import (
    MESSAGES_KEY,
    Message,
    MultiAgentRuntime,
    RoleAgent,
    handoff,
    post,
)
from xyberos.contracts import Agent
from xyberos.exceptions import AgentNotFoundError, HandoffLoopError
from xyberos.runtime.context import CognitiveContext


def test_message_contract_and_helpers():
    message = Message(sender="a", recipient="b", content="hi", kind="message")
    assert message.sender == "a"
    assert message.recipient == "b"
    assert message.content == "hi"

    off = handoff("b", "take it", sender="a")
    assert off.kind == "handoff"
    assert off.recipient == "b"

    context = CognitiveContext("go")
    post(context, message)
    assert context.metadata[MESSAGES_KEY] == [message]


def test_agents_exchange_messages():
    inbox = []

    def send_hi(context):
        post(context, Message(sender="a", recipient="b", content="hi"))
        return context

    a = RoleAgent("a", "sender", run=send_hi)
    b = RoleAgent("b", "receiver", receive=lambda message: inbox.append(message))
    runtime = MultiAgentRuntime([a, b])

    runtime.run(CognitiveContext("go"))

    assert len(runtime.messages) == 1
    assert runtime.messages[0].content == "hi"
    assert inbox == [runtime.messages[0]]


def test_broadcast_messages_deliver_to_all_agents():
    received = []

    def send_broadcast(context):
        post(context, Message(sender="a", recipient="*", content="all"))
        return context

    a = RoleAgent("a", "x", run=send_broadcast)
    b = RoleAgent("b", "y", receive=lambda message: received.append(message.content))
    c = RoleAgent("c", "z", receive=lambda message: received.append(message.content))
    runtime = MultiAgentRuntime([a, b, c])

    runtime.run(CognitiveContext("go"))

    assert sorted(received) == ["all", "all"]


def test_unknown_recipient_is_recorded_but_not_delivered():
    a = RoleAgent("a", "x", run=lambda c: (post(c, Message(sender="a", recipient="ghost", content="?")) or c))
    runtime = MultiAgentRuntime([a])

    runtime.run(CognitiveContext("go"))

    assert len(runtime.messages) == 1
    assert runtime.messages[0].recipient == "ghost"


def test_delivery_failures_do_not_break_the_run():
    def send(context):
        post(context, Message(sender="a", recipient="b", content="boom"))
        return context

    a = RoleAgent("a", "x", run=send)
    b = RoleAgent("b", "bad", receive=lambda message: (_ for _ in ()).throw(RuntimeError("nope")))
    runtime = MultiAgentRuntime([a, b])

    result = runtime.run(CognitiveContext("go"))

    assert result.prompt == "go"
    assert len(runtime.messages) == 1


def test_handoff_runs_the_recipient_without_rerunning_it():
    a = RoleAgent(
        "a",
        "starter",
        run=lambda c: (post(c, handoff("b", sender="a")), c)[1],
    )
    runs = []
    b = RoleAgent(
        "b",
        "finisher",
        run=lambda c: (runs.append("b"), setattr(c, "response", "done by b"), c)[2],
    )
    runtime = MultiAgentRuntime([a, b])

    result = runtime.run(CognitiveContext("go"))

    assert result.response == "done by b"
    assert runs == ["b"]  # b ran once via the handoff, not again from the sequence


def test_handoff_chain_follows_multiple_agents():
    order = []

    def make(name, target):
        def step(context):
            order.append(name)
            if target:
                post(context, handoff(target, sender=name))
            return context

        return RoleAgent(name, "hop", run=step)

    runtime = MultiAgentRuntime([make("a", "b"), make("b", "c"), make("c", None)])

    runtime.run(CognitiveContext("go"))

    assert order == ["a", "b", "c"]


def test_handoff_back_to_a_completed_agent_stops_the_chain():
    a = RoleAgent("a", "x", run=lambda c: (post(c, handoff("b", sender="a")), c)[1])
    b = RoleAgent("b", "y", run=lambda c: (post(c, handoff("a", sender="b")), c)[1])
    runtime = MultiAgentRuntime([a, b])

    result = runtime.run(CognitiveContext("go"))

    assert result is not None
    assert len(runtime.messages) == 2  # both handoffs were recorded


def test_handoff_loop_exceeds_max_handoffs():
    chain = {"a": "b", "b": "c", "c": "d"}

    def make(name):
        return RoleAgent(
            name,
            "hop",
            run=lambda c, n=name: (post(c, handoff(chain[n], sender=n)), c)[1],
        )

    runtime = MultiAgentRuntime([make(n) for n in ("a", "b", "c", "d")], max_handoffs=2)

    with pytest.raises(HandoffLoopError, match="too many handoffs"):
        runtime.run(CognitiveContext("go"))


def test_handoff_to_unknown_target_raises():
    a = RoleAgent("a", "x", run=lambda c: (post(c, handoff("ghost", sender="a")), c)[1])
    runtime = MultiAgentRuntime([a])

    with pytest.raises(AgentNotFoundError, match="not registered"):
        runtime.run(CognitiveContext("go"))


def test_roles_are_exposed_and_validated():
    writer = RoleAgent("writer", "author", run=lambda c: c)
    runtime = MultiAgentRuntime([writer])

    assert runtime.role("writer") == "author"
    assert runtime.names == ("writer",)

    with pytest.raises(ValueError, match="non-empty"):
        RoleAgent("", "author")
    with pytest.raises(ValueError, match="non-empty"):
        RoleAgent("writer", "")
    with pytest.raises(TypeError, match="callable"):
        RoleAgent("writer", "author", run=object())


def test_role_agent_run_and_receive_handlers():
    inbox = []
    writer = RoleAgent(
        "writer",
        "author",
        run=lambda c: (setattr(c, "response", "written"), c)[1],
        receive=lambda m: inbox.append(m.content),
    )
    runtime = MultiAgentRuntime([writer])

    runtime.send(Message(sender="boss", recipient="writer", content="draft it"))
    result = runtime.run(CognitiveContext("go"))

    assert inbox == ["draft it"]
    assert result.response == "written"


def test_agents_without_a_role_report_none():
    class PlainAgent(Agent):
        @property
        def name(self):
            return "plain"

        def run(self, context):
            return context

    runtime = MultiAgentRuntime([PlainAgent()])
    assert runtime.role("plain") is None


def test_coordination_works_through_the_facade():
    inbox = []

    def ask(context):
        post(context, Message(sender="boss", recipient="worker", content="do it"))
        return context

    app = create_app()
    app.register_agent(RoleAgent("boss", "supervisor", run=ask))
    app.register_agent(
        RoleAgent(
            "worker",
            "performer",
            run=lambda c: (setattr(c, "response", "worked"), c)[1],
            receive=lambda m: inbox.append(m.content),
        )
    )

    result = app.run_agents("task", agent_names=["boss", "worker"])

    assert inbox == ["do it"]
    assert len(app.agents.messages) == 1
    assert result.response == "worked"
    assert result.succeeded

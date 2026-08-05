"""Tests for the event bus and pipeline observability."""

import pytest

from xyberos import create_app
from xyberos.brain.brain import Brain
from xyberos.contracts import Plugin, Tool
from xyberos.events import (
    BRAIN_ERROR,
    Event,
    EventBus,
    KERNEL_STARTED,
    KERNEL_STOPPED,
    KNOWLEDGE_QUERIED,
    MEMORY_RETRIEVED,
    MEMORY_STORED,
    PLAN_CREATED,
    PLUGIN_LOADED,
    PLUGIN_UNLOADED,
    REQUEST_COMPLETED,
    REQUEST_FAILED,
    REQUEST_STARTED,
    RESPONSE_PRODUCED,
    TOOL_DISPATCHED,
    WORKFLOW_RUN,
)
from xyberos.knowledge import InMemoryKnowledge
from xyberos.llm import CallableLLM
from xyberos.memory import InMemoryMemory
from xyberos.planner import SequentialPlanner
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import ToolRunner
from xyberos.workflows import SequentialWorkflow


def recorder():
    seen = []

    def listener(event):
        seen.append(event)

    return seen, listener


class ReverseTool(Tool):
    @property
    def name(self):
        return "reverse"

    def execute(self, context, **arguments):
        return context.prompt[::-1]


class EchoPlugin(Plugin):
    @property
    def name(self):
        return "echo"

    def register(self, kernel):
        kernel.register("echo", "hello")

    def unregister(self, kernel):
        kernel.registry.unregister("echo")


class FailingLLM:
    def generate(self, prompt):
        raise RuntimeError("model exploded")


def test_event_bus_delivers_events_to_subscribers():
    bus = EventBus()
    seen, listener = recorder()
    bus.subscribe("app.started", listener)

    bus.emit("app.started", context="kernel", detail=42)

    assert len(seen) == 1
    event = seen[0]
    assert isinstance(event, Event)
    assert event.name == "app.started"
    assert event.context == "kernel"
    assert event.data == {"detail": 42}


def test_event_bus_supports_wildcard_and_unsubscribe():
    bus = EventBus()
    seen, listener = recorder()
    bus.subscribe_any(listener)

    bus.emit("one")
    bus.emit("two")
    assert [event.name for event in seen] == ["one", "two"]

    bus.unsubscribe_any(listener)
    bus.emit("three")
    assert [event.name for event in seen] == ["one", "two"]


def test_event_bus_unsubscribe_removes_a_listener():
    bus = EventBus()
    seen, listener = recorder()
    bus.subscribe("x", listener)
    bus.emit("x")

    bus.unsubscribe("x", listener)
    bus.emit("x")

    assert [event.name for event in seen] == ["x"]


def test_event_bus_logs_listener_failures_when_logger_configured():
    import logging

    from xyberos.kernel.logger import Logger

    logger = Logger("xyberos.tests.events.failures", level=logging.CRITICAL)
    bus = EventBus(logger=logger)
    seen, listener = recorder()
    bus.subscribe("x", lambda event: (_ for _ in ()).throw(RuntimeError("boom")))
    bus.subscribe("x", listener)

    bus.emit("x")

    assert [event.name for event in seen] == ["x"]


def test_event_bus_isolates_listener_failures():
    bus = EventBus()
    seen, listener = recorder()
    bus.subscribe("x", lambda event: (_ for _ in ()).throw(RuntimeError("boom")))
    bus.subscribe("x", listener)

    bus.emit("x")

    assert [event.name for event in seen] == ["x"]


def test_event_bus_validates_inputs_and_clears():
    bus = EventBus()
    with pytest.raises(ValueError, match="non-empty"):
        bus.subscribe("", lambda event: None)
    with pytest.raises(TypeError, match="callable"):
        bus.subscribe("x", object())
    with pytest.raises(TypeError, match="callable"):
        bus.subscribe_any(object())

    assert not bus.has_listeners("x")
    bus.subscribe("x", lambda event: None)
    assert bus.has_listeners("x")
    bus.clear()
    assert not bus.has_listeners("x")


def test_kernel_emits_lifecycle_events():
    app = create_app(config={"logger_name": "xyberos.tests.events.kernel"})
    seen, listener = recorder()
    app.events.subscribe(KERNEL_STARTED, listener)
    app.events.subscribe(KERNEL_STOPPED, listener)

    app.start()
    app.stop()

    assert [event.name for event in seen] == [KERNEL_STARTED, KERNEL_STOPPED]


def test_plugin_loader_emits_events():
    app = create_app()
    seen, listener = recorder()
    app.events.subscribe(PLUGIN_LOADED, listener)
    app.events.subscribe(PLUGIN_UNLOADED, listener)

    app.load_plugin(EchoPlugin())
    app.unload_plugin("echo")

    assert [event.name for event in seen] == [PLUGIN_LOADED, PLUGIN_UNLOADED]


def test_runtime_and_brain_emit_pipeline_events_in_order():
    app = create_app(
        llm=CallableLLM(lambda prompt: f"answer:{prompt}"),
        memory=InMemoryMemory(),
        knowledge=InMemoryKnowledge({"python": "a language"}),
        planner=SequentialPlanner(),
        workflow=SequentialWorkflow(),
        tool_runner=ToolRunner(),
    )
    seen, listener = recorder()
    for name in (
        REQUEST_STARTED,
        WORKFLOW_RUN,
        MEMORY_RETRIEVED,
        KNOWLEDGE_QUERIED,
        PLAN_CREATED,
        RESPONSE_PRODUCED,
        MEMORY_STORED,
        REQUEST_COMPLETED,
    ):
        app.events.subscribe(name, listener)

    context = app.run("tell me about python")

    assert context.succeeded
    assert [event.name for event in seen] == [
        REQUEST_STARTED,
        WORKFLOW_RUN,
        MEMORY_RETRIEVED,
        KNOWLEDGE_QUERIED,
        PLAN_CREATED,
        RESPONSE_PRODUCED,
        MEMORY_STORED,
        REQUEST_COMPLETED,
    ]


def test_brain_emits_tool_dispatch_event():
    bus = EventBus()
    seen, listener = recorder()
    bus.subscribe(TOOL_DISPATCHED, listener)
    brain = Brain(
        CallableLLM(lambda prompt: "never"),
        tool_runner=ToolRunner([ReverseTool()]),
        events=bus,
    )

    assert brain.chat(CognitiveContext("reverse")) == "esrever"

    assert [event.name for event in seen] == [TOOL_DISPATCHED]


def test_workflow_short_circuit_still_emits_events():
    def respond(context):
        context.response = "from workflow"

    app = create_app(workflow=SequentialWorkflow([respond]))
    seen, listener = recorder()
    app.events.subscribe(WORKFLOW_RUN, listener)
    app.events.subscribe(MEMORY_STORED, listener)
    app.events.subscribe(RESPONSE_PRODUCED, listener)

    assert app.chat("hi") == "from workflow"

    names = [event.name for event in seen]
    assert WORKFLOW_RUN in names
    assert MEMORY_STORED in names  # the completed turn is still remembered
    assert RESPONSE_PRODUCED not in names  # the workflow produced the response


def test_errors_emit_brain_and_runtime_failure_events():
    app = create_app(llm=FailingLLM())
    seen, listener = recorder()
    app.events.subscribe(BRAIN_ERROR, listener)
    app.events.subscribe(REQUEST_FAILED, listener)

    with pytest.raises(RuntimeError, match="model exploded"):
        app.run("boom")

    assert [event.name for event in seen] == [BRAIN_ERROR, REQUEST_FAILED]


def test_facade_exposes_event_bus_and_default_app_emits():
    app = create_app()
    assert app.events is app.resolve("events")

    seen, listener = recorder()
    app.events.subscribe(RESPONSE_PRODUCED, listener)

    assert app.chat("hello") == "hello"
    assert [event.name for event in seen] == [RESPONSE_PRODUCED]
    assert seen[0].data["response"] == "hello"

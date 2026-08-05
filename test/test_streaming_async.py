"""Tests for streaming LLM output and the async pipeline (achat/arun)."""

import asyncio

import pytest

from xyberos import achat as one_shot_achat
from xyberos import create_app
from xyberos.brain.brain import Brain
from xyberos.contracts import Tool
from xyberos.events import (
    BRAIN_ERROR,
    EventBus,
    EventRecorder,
    REQUEST_COMPLETED,
    REQUEST_FAILED,
    REQUEST_STARTED,
    RESPONSE_PRODUCED,
    TOKEN_STREAMED,
    TOOL_DISPATCHED,
)
from xyberos.exceptions import WorkflowPaused
from xyberos.llm import AsyncLLM, CallableLLM, StreamingLLM
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import ToolRunner
from xyberos.workflows import GraphWorkflow


class ReverseTool(Tool):
    @property
    def name(self):
        return "reverse"

    def execute(self, context, **arguments):
        return context.prompt[::-1]


class TokenLLM:
    """A sync LLM that streams tokens "a", "b", "c" and returns "abc"."""

    def generate(self, prompt):
        return "full:" + prompt

    def stream(self, prompt, on_token):
        for token in ("a", "b", "c"):
            on_token(token)
        return "abc"


class AsyncStreamingLLM:
    """An async LLM that streams tokens through ``astream``."""

    async def astream(self, prompt, on_token):
        on_token("1")
        on_token("2")
        return "12"


def test_brain_streams_tokens_through_the_event_bus():
    bus = EventBus()
    tokens = []
    bus.subscribe(TOKEN_STREAMED, lambda event: tokens.append(event.data["token"]))
    brain = Brain(TokenLLM(), events=bus)

    assert brain.chat(CognitiveContext("hi")) == "abc"
    assert tokens == ["a", "b", "c"]


def test_streaming_llm_helper_generates_and_streams():
    def stream(prompt, on_token):
        on_token("x")
        on_token("y")
        return "xy"

    llm = StreamingLLM(generate=lambda prompt: "full:" + prompt, stream=stream)
    bus = EventBus()
    tokens = []
    bus.subscribe(TOKEN_STREAMED, lambda event: tokens.append(event.data["token"]))
    brain = Brain(llm, events=bus)

    assert brain.chat(CognitiveContext("hi")) == "xy"
    assert tokens == ["x", "y"]


def test_streaming_events_are_recorded_by_the_recorder():
    app = create_app(llm=TokenLLM())
    recorder = EventRecorder().subscribe_to(app.events)

    app.chat("hi")

    assert recorder.count_for(TOKEN_STREAMED) == 3
    assert recorder.count_for(RESPONSE_PRODUCED) == 1


async def _agenerate(prompt):
    await asyncio.sleep(0)
    return f"async:{prompt}"


def test_async_chat_uses_agenerate():
    app = create_app(llm=AsyncLLM(_agenerate))

    assert asyncio.run(app.achat("hi")) == "async:hi"


def test_async_run_returns_completed_context():
    app = create_app(llm=AsyncLLM(_agenerate))

    context = asyncio.run(app.arun("question"))

    assert context.response == "async:question"
    assert context.succeeded


def test_async_chat_falls_back_to_a_sync_llm():
    app = create_app(llm=CallableLLM(lambda prompt: f"sync:{prompt}"))

    assert asyncio.run(app.achat("hi")) == "sync:hi"


def test_module_level_achat_helper():
    result = asyncio.run(one_shot_achat("hi", llm=AsyncLLM(_agenerate)))

    assert result == "async:hi"


def test_sync_chat_rejects_an_async_only_llm():
    app = create_app(llm=AsyncLLM(_agenerate))

    with pytest.raises(TypeError, match="generate"):
        app.chat("hi")


def test_async_stream_emits_tokens():
    bus = EventBus()
    tokens = []
    bus.subscribe(TOKEN_STREAMED, lambda event: tokens.append(event.data["token"]))
    brain = Brain(AsyncStreamingLLM(), events=bus)

    result = asyncio.run(brain.achat(CognitiveContext("hi")))

    assert result == "12"
    assert tokens == ["1", "2"]


def test_async_pipeline_emits_events():
    app = create_app(llm=AsyncLLM(_agenerate))
    recorder = EventRecorder().subscribe_to(app.events)

    asyncio.run(app.achat("hi"))

    assert recorder.count_for(REQUEST_STARTED) == 1
    assert recorder.count_for(RESPONSE_PRODUCED) == 1
    assert recorder.count_for(REQUEST_COMPLETED) == 1


def test_async_tool_response_path():
    app = create_app(llm=AsyncLLM(_agenerate), tool_runner=ToolRunner([ReverseTool()]))
    recorder = EventRecorder().subscribe_to(app.events)

    result = asyncio.run(app.achat("reverse"))

    assert result == "esrever"
    assert recorder.count_for(TOOL_DISPATCHED) == 1


class FailingAsyncLLM:
    async def agenerate(self, prompt):
        raise RuntimeError("async boom")


def test_async_errors_emit_failure_events():
    app = create_app(llm=FailingAsyncLLM())
    recorder = EventRecorder().subscribe_to(app.events)

    with pytest.raises(RuntimeError, match="async boom"):
        asyncio.run(app.achat("hi"))

    assert recorder.count_for(BRAIN_ERROR) == 1
    assert recorder.count_for(REQUEST_FAILED) == 1


def test_async_workflow_pause_propagates_without_failure_events():
    graph = GraphWorkflow("ask")

    def ask(context):
        if GraphWorkflow.RESUME_KEY in context.metadata:
            context.response = "yes"
            return context
        raise WorkflowPaused(prompt="Approve?")

    graph.add_node("ask", ask)
    app = create_app(llm=AsyncLLM(_agenerate), workflow=graph)
    recorder = EventRecorder().subscribe_to(app.events)

    with pytest.raises(WorkflowPaused) as excinfo:
        asyncio.run(app.achat("hi"))

    assert recorder.count_for(BRAIN_ERROR) == 0
    assert recorder.count_for(REQUEST_FAILED) == 0
    run = graph.resume(excinfo.value.run, "yes")
    assert run.status == "completed"
    assert run.context.response == "yes"


def test_async_rejects_llm_without_any_generate_method():
    class NoMethodsLLM:
        pass

    app = create_app(llm=NoMethodsLLM())

    with pytest.raises(TypeError, match="agenerate"):
        asyncio.run(app.achat("hi"))


def test_async_chat_rejects_invalid_context():
    brain = Brain(AsyncLLM(_agenerate))

    with pytest.raises(TypeError, match="CognitiveContext"):
        asyncio.run(brain.achat("not a context"))  # type: ignore[arg-type]


def test_async_workflow_short_circuit():
    graph = GraphWorkflow("finish")
    graph.add_node("finish", lambda c: (setattr(c, "response", "from graph") or c))
    app = create_app(llm=AsyncLLM(_agenerate), workflow=graph)

    assert asyncio.run(app.achat("hi")) == "from graph"

"""Integration tests for the RFC-0016 Phase 0 Brain wiring (intent + experience)."""

from xyberos import create_app
from xyberos.contracts import Intent
from xyberos.events import EPISODE_RECORDED, INTENT_CLASSIFIED
from xyberos.experience import InMemoryExperience
from xyberos.intent import HeuristicIntentEngine, IntentRule
from xyberos.llm import CallableLLM
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import FunctionTool, ToolRunner
from xyberos.tools.registry import ToolRegistry


def test_brain_classifies_intent_when_enabled():
    intent = HeuristicIntentEngine([IntentRule("greeting", ("hello",))])
    app = create_app(
        llm=CallableLLM(lambda prompt: "ok"),
        intent=intent,
        config={"brain.intent": True},
    )

    context = app.run("hello there")

    assert context.intent is not None
    assert context.intent.name == "greeting"


def test_brain_does_not_classify_intent_by_default():
    app = create_app(llm=CallableLLM(lambda prompt: "ok"))

    context = app.run("hello")

    assert context.intent is None


def test_brain_emits_intent_classified_event():
    intent = HeuristicIntentEngine([IntentRule("greeting", ("hello",))])
    app = create_app(
        llm=CallableLLM(lambda prompt: "ok"),
        intent=intent,
        config={"brain.intent": True},
    )
    seen = []
    app.events.subscribe(INTENT_CLASSIFIED, lambda event: seen.append(event.data))

    app.run("hello")

    assert seen and seen[0]["intent"] == "greeting"
    assert seen[0]["confidence"] == 1.0


def test_intent_target_routes_tool_dispatch():
    tools = ToolRegistry([FunctionTool("say_hi", lambda: "hi there", description="greet")])
    intent = HeuristicIntentEngine([IntentRule("greeting", ("hello",), target="say_hi")])
    app = create_app(
        llm=CallableLLM(lambda prompt: "fallback"),
        tools=tools,
        intent=intent,
        config={"brain.intent": True},
    )

    assert app.chat("hello") == "hi there"


def test_tool_runner_choose_honors_intent_target():
    runner = ToolRunner(ToolRegistry([FunctionTool("refund_tool", lambda: "ok")]))
    context = CognitiveContext("please help")
    context.intent = Intent(name="refund", target="refund_tool")

    assert runner.choose(context) == "refund_tool"


def test_brain_records_episode_when_experience_enabled():
    experience = InMemoryExperience()
    app = create_app(
        llm=CallableLLM(lambda prompt: "hello back"),
        experience=experience,
        config={"experience.enabled": True},
    )

    app.chat("hello")

    assert experience.stats()["total"] == 1
    episode = experience.query(limit=1)[0]
    assert episode.prompt == "hello"
    assert episode.response == "hello back"


def test_brain_does_not_record_episodes_by_default():
    experience = InMemoryExperience()
    app = create_app(llm=CallableLLM(lambda prompt: "x"), experience=experience)

    app.chat("hello")

    assert experience.stats()["total"] == 0


def test_brain_emits_episode_recorded_event():
    experience = InMemoryExperience()
    app = create_app(
        llm=CallableLLM(lambda prompt: "x"),
        experience=experience,
        config={"experience.enabled": True},
    )
    seen = []
    app.events.subscribe(EPISODE_RECORDED, lambda event: seen.append(event))

    app.chat("hello")

    assert len(seen) == 1


def test_episode_records_intent_when_both_enabled():
    experience = InMemoryExperience()
    intent = HeuristicIntentEngine([IntentRule("greeting", ("hello",))])
    app = create_app(
        llm=CallableLLM(lambda prompt: "hi"),
        intent=intent,
        experience=experience,
        config={"brain.intent": True, "experience.enabled": True},
    )

    app.chat("hello")

    episode = experience.query(limit=1)[0]
    assert episode.intent is not None
    assert episode.intent.name == "greeting"

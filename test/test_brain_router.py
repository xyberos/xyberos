from xyberos.brain.brain import Brain
from xyberos.contracts import Responder, Template
from xyberos.events import DEGRADED, ESCALATED, RESPONDER_HIT, EventBus
from xyberos.llm import CallableLLM
from xyberos.router import ResponderChain, TemplateResponder
from xyberos.runtime.context import CognitiveContext


class DeclineResponder(Responder):
    def respond(self, context):
        return None


def test_brain_without_router_uses_llm_unchanged():
    brain = Brain(CallableLLM(lambda prompt: f"answer:{prompt}"))
    assert brain.chat(CognitiveContext("question")) == "answer:question"


def test_brain_router_hit_short_circuits_before_llm():
    router = ResponderChain([("template", TemplateResponder([
        Template(pattern="hello", variants=("Hello there!",)),
    ]))])
    brain = Brain(
        CallableLLM(lambda prompt: "LLM-SHOULD-NOT-RUN"),
        router=router,
    )
    assert brain.chat(CognitiveContext("hello world")) == "Hello there!"


def test_brain_router_miss_falls_through_to_llm():
    router = ResponderChain([("template", TemplateResponder([
        Template(pattern="hello", variants=("Hello there!",)),
    ]))])
    brain = Brain(
        CallableLLM(lambda prompt: f"answer:{prompt}"),
        router=router,
    )
    assert brain.chat(CognitiveContext("what is the weather")) == "answer:what is the weather"


def test_brain_router_emits_hit_and_escalation_events():
    events = EventBus()
    seen = []
    events.subscribe_any(lambda event: seen.append(event))

    router = ResponderChain(
        [
            ("declines", DeclineResponder()),
            ("template", TemplateResponder([Template(pattern="hi", variants=("Hi!",))])),
        ],
        events=events,
    )
    brain = Brain(CallableLLM(lambda prompt: "x"), router=router)
    brain.chat(CognitiveContext("hi there"))

    names = [event.name for event in seen]
    assert ESCALATED in names
    assert RESPONDER_HIT in names


def test_brain_router_emits_degraded_when_everyone_declines_with_fallback():
    events = EventBus()
    seen = []
    events.subscribe_any(lambda event: seen.append(event))

    router = ResponderChain(
        [("declines", DeclineResponder())],
        fallback=lambda context: "degraded answer",
        events=events,
    )
    brain = Brain(CallableLLM(lambda prompt: "x"), router=router)
    assert brain.chat(CognitiveContext("anything")) == "degraded answer"

    assert DEGRADED in [event.name for event in seen]

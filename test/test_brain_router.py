from xyberos.brain.brain import Brain
from xyberos.contracts import Intent, Responder, Template
from xyberos.events import DEGRADED, ESCALATED, RESPONDER_HIT, EventBus
from xyberos.llm import CallableLLM
from xyberos.router import CacheResponder, LLMResponder, ResponderChain, TemplateResponder
from xyberos.runtime.context import CognitiveContext


class CountingIntentEngine:
    def __init__(self):
        self.calls = 0

    def classify(self, context):
        self.calls += 1
        return Intent(name="general", confidence=0.0)


class CountingPlanner:
    def __init__(self):
        self.calls = 0

    def plan(self, context):
        self.calls += 1
        return ["step"]


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


def test_brain_cheap_first_skips_intent_and_planner_on_cache_hit():
    cache = CacheResponder()
    cache.teach("hello", "Hi there!")
    router = ResponderChain([
        ("cache", cache),
        ("llm", LLMResponder(CallableLLM(lambda prompt: "llm"))),
    ])
    intent = CountingIntentEngine()
    planner = CountingPlanner()
    brain = Brain(
        CallableLLM(lambda prompt: "llm"),
        router=router,
        intent=intent,
        planner=planner,
        config={"brain.cheap_first": True, "brain.intent": True},
    )

    assert brain.chat(CognitiveContext("hello")) == "Hi there!"
    assert intent.calls == 0  # cheap tier answered before intent/planner ran
    assert planner.calls == 0


def test_brain_without_cheap_first_still_runs_intent_before_router():
    cache = CacheResponder()
    cache.teach("hello", "Hi there!")
    router = ResponderChain([("cache", cache)])
    intent = CountingIntentEngine()
    brain = Brain(
        CallableLLM(lambda prompt: "llm"),
        router=router,
        intent=intent,
        config={"brain.intent": True, "brain.cheap_first": False},
    )

    assert brain.chat(CognitiveContext("hello")) == "Hi there!"
    assert intent.calls == 1  # cheap_first disabled: intent classifies before the router


def test_brain_cheap_first_defaults_on_for_llm_free_chain():
    # No LLM tier -> the chain is LLM-free -> cheap_first defaults ON.
    cache = CacheResponder()
    cache.teach("hello", "Hi there!")
    router = ResponderChain([("cache", cache)])
    intent = CountingIntentEngine()
    brain = Brain(
        CallableLLM(lambda prompt: "llm"),
        router=router,
        intent=intent,
        config={"brain.intent": True},
    )

    assert router.is_llm_free
    assert brain.chat(CognitiveContext("hello")) == "Hi there!"
    assert intent.calls == 0  # cheap tier answered before intent ran


def test_brain_cheap_first_defaults_off_for_llm_chain():
    # An LLM tier present -> cheap_first stays OFF (intent runs first).
    router = ResponderChain([
        ("cache", CacheResponder()),
        ("llm", LLMResponder(CallableLLM(lambda prompt: "llm"))),
    ])
    intent = CountingIntentEngine()
    brain = Brain(
        CallableLLM(lambda prompt: "llm"),
        router=router,
        intent=intent,
        config={"brain.intent": True},
    )

    assert not router.is_llm_free
    brain.chat(CognitiveContext("hello"))
    assert intent.calls == 1

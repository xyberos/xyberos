from xyberos.router import CacheResponder, CacheTeacher
from xyberos.runtime.context import CognitiveContext


class FakeEvent:
    def __init__(self, context, data):
        self.context = context
        self.data = data


class FakeEventBus:
    def __init__(self):
        self.listeners = []

    def subscribe(self, name, listener):
        self.listeners.append((name, listener))
        return listener

    def emit(self, name, context=None, **data):
        for event_name, listener in self.listeners:
            if event_name == name:
                listener(FakeEvent(context, data))


def test_cache_teacher_teaches_from_response_event():
    cache = CacheResponder()
    events = FakeEventBus()
    teacher = CacheTeacher(cache, events)

    events.emit("brain.response_produced", context=CognitiveContext("what are your hours"), response="We're open 9-5.")

    assert teacher.taught == 1
    assert cache.respond(CognitiveContext("what are your hours")) == "We're open 9-5."


def test_cache_teacher_ignores_events_without_response():
    cache = CacheResponder()
    events = FakeEventBus()
    teacher = CacheTeacher(cache, events)

    events.emit("brain.response_produced", context=CognitiveContext("hello"), response=None)

    assert teacher.taught == 0


def test_cache_teacher_ignores_other_events():
    cache = CacheResponder()
    events = FakeEventBus()
    CacheTeacher(cache, events)

    events.emit("brain.responder_hit", context=CognitiveContext("hello"), response="hi")

    assert cache.respond(CognitiveContext("hello")) is None


def test_cache_teacher_without_events_does_not_crash():
    teacher = CacheTeacher(CacheResponder())
    assert teacher.taught == 0


def test_cache_teacher_teaches_from_llm_responder_hit():
    cache = CacheResponder()
    events = FakeEventBus()
    teacher = CacheTeacher(cache, events)

    events.emit("brain.responder_hit", context=CognitiveContext("hello"), tier="llm", response="hi there")

    assert teacher.taught == 1
    assert cache.respond(CognitiveContext("hello")) == "hi there"


def test_cache_teacher_ignores_non_llm_responder_hits():
    cache = CacheResponder()
    events = FakeEventBus()
    CacheTeacher(cache, events)

    events.emit("brain.responder_hit", context=CognitiveContext("hello"), tier="template", response="hi")

    assert cache.respond(CognitiveContext("hello")) is None
    assert CacheTeacher(cache).taught == 0

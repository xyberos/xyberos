import time

from xyberos.contracts import Episode, Responder
from xyberos.events import ESCALATED, RESPONDER_HIT, EventBus
from xyberos.experience import InMemoryExperience
from xyberos.router import EscalationTuner, ResponderChain, TierMonitor, TuningLoop


class AlwaysResponder(Responder):
    def respond(self, context):
        return "answer"

    def confidence(self, context):
        return 1.0


def _chain(*names):
    return ResponderChain([(name, AlwaysResponder()) for name in names])


def test_monitor_tracks_hits_and_escalations():
    events = EventBus()
    monitor = TierMonitor(events, window=10)

    events.emit(RESPONDER_HIT, tier="cache", confidence=0.9, response="x")
    events.emit(RESPONDER_HIT, tier="cache", confidence=0.9, response="y")
    events.emit(RESPONDER_HIT, tier="llm", confidence=1.0, response="z")
    events.emit(ESCALATED, tier="knowledge", confidence=0.4, reason="declined")

    assert monitor.hit_count("cache") == 2
    assert monitor.hit_count("llm") == 1
    assert monitor.escalation_count("knowledge") == 1
    assert monitor.total_hits() == 3


def test_monitor_cheap_hit_rate():
    events = EventBus()
    monitor = TierMonitor(events, window=10)
    for _ in range(8):
        events.emit(RESPONDER_HIT, tier="cache", response="x")
    for _ in range(2):
        events.emit(RESPONDER_HIT, tier="llm", response="z")

    assert monitor.cheap_hit_rate() == 0.8


def test_monitor_summary_has_per_tier_dashboard():
    events = EventBus()
    monitor = TierMonitor(events)
    events.emit(RESPONDER_HIT, tier="cache", response="x")
    events.emit(ESCALATED, tier="knowledge", reason="declined")

    summary = monitor.summary()
    assert summary["cache"]["hits"] == 1
    assert summary["knowledge"]["escalations"] == 1
    assert summary["_total"]["hits"] == 1


def test_monitor_tune_forwards_to_tuner():
    chain = _chain("template")
    chain.set_threshold("template", 0.9)
    tuner = EscalationTuner(chain, learning_rate=0.1)
    monitor = TierMonitor(tuner=tuner)

    experience = InMemoryExperience()
    episode = experience.record(Episode(prompt="p", response="r", metadata={"responder": "template"}))
    experience.feedback(episode.id, -1.0)

    assert monitor.tune(experience) == 1
    assert chain.get_threshold("template") > 0.9  # negative feedback raised the gate


def test_tuning_loop_step_runs_one_iteration():
    chain = _chain("template")
    tuner = EscalationTuner(chain, learning_rate=0.1)
    monitor = TierMonitor(tuner=tuner)
    loop = TuningLoop(monitor, InMemoryExperience())

    assert loop.step() == 0  # no rated episodes -> no adjustments


def test_tuning_loop_start_stop():
    chain = _chain("template")
    tuner = EscalationTuner(chain, learning_rate=0.1)
    monitor = TierMonitor(tuner=tuner)
    experience = InMemoryExperience()
    episode = experience.record(Episode(prompt="p", response="r", metadata={"responder": "template"}))
    experience.feedback(episode.id, -1.0)

    loop = TuningLoop(monitor, experience, interval=0.05)
    loop.start()
    time.sleep(0.2)  # let a few iterations run
    loop.stop()

    # The loop ran at least once and raised the gate.
    assert chain.get_threshold("template") > 0.0

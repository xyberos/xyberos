from xyberos.contracts import Episode, Responder
from xyberos.experience import InMemoryExperience
from xyberos.router import EscalationTuner, ResponderChain
from xyberos.runtime.context import CognitiveContext


class AlwaysResponder(Responder):
    def respond(self, context):
        return "answer"

    def confidence(self, context):
        return 1.0


def _chain(*names):
    return ResponderChain([(name, AlwaysResponder()) for name in names])


def _episode(prompt, feedback, tier=None):
    metadata = {"responder": tier} if tier else {}
    return Episode(prompt=prompt, response="r", feedback=feedback, metadata=metadata)


def test_negative_feedback_raises_tier_gate():
    chain = _chain("template", "cache")
    tuner = EscalationTuner(chain, learning_rate=0.05)

    tuner.tune([_episode("bad template answer", feedback=-1.0, tier="template")])

    assert chain.get_threshold("template") == 0.05
    assert chain.get_threshold("cache") == 0.0  # untouched


def test_positive_feedback_relaxes_tier_gate():
    chain = _chain("cache")
    chain.set_threshold("cache", 0.5)
    tuner = EscalationTuner(chain, learning_rate=0.05)

    tuner.tune([_episode("good cache answer", feedback=1.0, tier="cache")])

    assert chain.get_threshold("cache") == 0.5 - 0.05 * 0.5


def test_escalated_but_well_rated_relaxes_cheap_tiers():
    chain = _chain("template", "cache")
    chain.set_threshold("template", 0.9)
    chain.set_threshold("cache", 0.9)
    tuner = EscalationTuner(chain, learning_rate=0.05)

    # No tier answered (metadata has no responder) yet the LLM was rated well.
    tuner.tune([_episode("escalated", feedback=1.0, tier=None)])

    assert chain.get_threshold("template") < 0.9
    assert chain.get_threshold("cache") < 0.9


def test_gate_is_clamped_to_max():
    chain = _chain("template")
    chain.set_threshold("template", 0.9)
    tuner = EscalationTuner(chain, learning_rate=0.1, max_gate=0.95)

    tuner.tune([_episode("x", feedback=-1.0, tier="template")])

    assert chain.get_threshold("template") <= 0.95


def test_tune_skips_unrated_episodes():
    chain = _chain("template")
    tuner = EscalationTuner(chain)

    assert tuner.tune([Episode(prompt="p", response="r")]) == 0
    assert chain.get_threshold("template") == 0.0


def test_tune_from_experience_pulls_rated_episodes():
    experience = InMemoryExperience()
    episode = experience.record(Episode(prompt="p", response="r", metadata={"responder": "template"}))
    experience.feedback(episode.id, -1.0)

    chain = _chain("template")
    tuner = EscalationTuner(chain, learning_rate=0.05)

    assert tuner.tune_from_experience(experience) == 1
    assert chain.get_threshold("template") == 0.05


def test_hit_rate_and_detach():
    tuner = EscalationTuner(_chain(), window=10)
    for _ in range(8):
        tuner.record_hit("cache")
    for _ in range(2):
        tuner.record_hit("llm")

    assert tuner.cheap_tier_hit_rate() == 0.8
    assert tuner.is_detached()  # >= 0.8 default


def test_hit_rate_empty_is_zero():
    tuner = EscalationTuner(_chain())
    assert tuner.cheap_tier_hit_rate() == 0.0
    assert not tuner.is_detached()

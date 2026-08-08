"""Contract tests for the ExperienceStore extension (RFC-0016)."""

import pytest

from xyberos.contracts import Episode, ExperienceStore, ExperienceStoreProvider


class StaticExperienceStore(ExperienceStore):
    def record(self, episode):
        return episode

    def query(self, *, intent=None, outcome=None, limit=20):
        return []

    def feedback(self, episode_id, rating, note=None):  # noqa: A002
        pass

    def stats(self):
        return {"total": 0}


def test_experience_store_contract_requires_all_methods():
    with pytest.raises(TypeError):
        ExperienceStore()


def test_experience_store_contract_works_without_core_dependencies():
    store = StaticExperienceStore()
    episode = store.record(Episode(prompt="hi"))
    assert episode.prompt == "hi"
    assert store.query() == []
    store.feedback("id", 1.0)
    assert store.stats() == {"total": 0}


def test_experience_store_contract_has_compatibility_alias():
    assert ExperienceStoreProvider is ExperienceStore


def test_episode_auto_generates_id_and_defaults():
    episode = Episode(prompt="hi")
    assert episode.id
    assert episode.tool_calls == []
    assert episode.metadata == {}
    assert episode.intent is None
    assert episode.outcome is None
    assert episode.feedback is None

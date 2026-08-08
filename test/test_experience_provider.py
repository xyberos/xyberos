"""Provider tests for the ExperienceStore contract (RFC-0016)."""

import pytest

from xyberos.contracts import Episode, Intent
from xyberos.experience import InMemoryExperience, SqliteExperience


def test_in_memory_experience_records_queries_and_feedback():
    store = InMemoryExperience()
    chat = store.record(Episode(prompt="hello", intent=Intent(name="chat")))
    store.record(Episode(prompt="refund please", intent=Intent(name="refund"), outcome="success"))
    store.record(Episode(prompt="closed", intent=Intent(name="faq"), outcome="failure"))

    assert store.stats()["total"] == 3
    assert [e.prompt for e in store.query(intent="refund")] == ["refund please"]
    assert [e.prompt for e in store.query(outcome="success")] == ["refund please"]
    assert len(store.query(limit=2)) == 2

    store.feedback(chat.id, 1.0)
    assert chat.feedback == 1.0


def test_in_memory_experience_feedback_unknown_id_raises():
    store = InMemoryExperience()

    with pytest.raises(KeyError):
        store.feedback("missing", 0.5)


def test_in_memory_experience_clear():
    store = InMemoryExperience()
    store.record(Episode(prompt="x"))
    store.clear()

    assert store.stats()["total"] == 0


def test_sqlite_experience_persists_across_reopen(tmp_path):
    path = str(tmp_path / "exp.db")
    first = SqliteExperience(path)
    stored = first.record(Episode(prompt="hello", response="hi there", outcome="success"))
    first.close()

    second = SqliteExperience(path)
    episodes = second.query()

    assert len(episodes) == 1
    assert episodes[0].id == stored.id
    assert episodes[0].prompt == "hello"
    assert episodes[0].response == "hi there"
    assert episodes[0].outcome == "success"
    second.close()


def test_sqlite_experience_feedback_updates_episode(tmp_path):
    path = str(tmp_path / "exp.db")
    store = SqliteExperience(path)
    stored = store.record(Episode(prompt="hello"))

    store.feedback(stored.id, -0.5, note="bad answer")

    reloaded = store.query(limit=1)[0]
    assert reloaded.feedback == -0.5
    assert reloaded.metadata.get("feedback_note") == "bad answer"
    store.close()


def test_sqlite_experience_round_trips_intent_and_plan(tmp_path):
    path = str(tmp_path / "exp.db")
    store = SqliteExperience(path)
    store.record(
        Episode(
            prompt="refund",
            intent=Intent(name="refund", confidence=0.9),
            plan=["analyze", "refund"],
            metadata={"user": "alice"},
        )
    )

    episode = store.query(limit=1)[0]
    assert episode.intent is not None
    assert episode.intent.name == "refund"
    assert episode.intent.confidence == 0.9
    assert episode.plan == ["analyze", "refund"]
    assert episode.metadata == {"user": "alice"}
    store.close()

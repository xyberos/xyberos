"""Tests for the SQLite-backed persistent memory and knowledge providers."""

import os

from xyberos import create_app
from xyberos.knowledge import SqliteKnowledge
from xyberos.llm import CallableLLM
from xyberos.memory import MemoryEntry, SqliteMemory
from xyberos.runtime.context import CognitiveContext


# --- SqliteMemory -------------------------------------------------------------


def test_sqlite_memory_stores_and_retrieves_entries_in_order():
    memory = SqliteMemory()
    first = CognitiveContext("first")
    first.response = "one"
    second = CognitiveContext("second")
    second.response = "two"

    memory.store(first)
    memory.store(second)

    entries = memory.retrieve(None)
    assert len(entries) == 2
    assert entries[0].prompt == "first"
    assert entries[0].response == "one"
    assert entries[1].prompt == "second"
    assert entries[1].response == "two"


def test_sqlite_memory_round_trips_metadata_plan_and_error():
    memory = SqliteMemory()
    context = CognitiveContext("hello", metadata={"request_id": "abc"})
    context.plan = ["analyze", "execute"]
    context.response = "hi"
    memory.store(context)

    entry = memory.retrieve(None)[0]
    assert isinstance(entry, MemoryEntry)
    assert entry.metadata == {"request_id": "abc"}
    assert entry.plan == ["analyze", "execute"]


def test_sqlite_memory_clear_removes_all_entries():
    memory = SqliteMemory()
    memory.store(CognitiveContext("entry"))

    memory.clear()

    assert memory.retrieve(None) == []


def test_sqlite_memory_persists_across_connections(tmp_path):
    path = str(tmp_path / "memory.db")
    first = SqliteMemory(path)
    first.store(CognitiveContext("persisted"))
    first.close()

    second = SqliteMemory(path)
    entries = second.retrieve(None)
    assert len(entries) == 1
    assert entries[0].prompt == "persisted"
    second.close()


def test_sqlite_memory_lifecycle_start_stop_preserves_file_data(tmp_path):
    memory = SqliteMemory(str(tmp_path / "lifecycle.db"))
    memory.store(CognitiveContext("before"))
    memory.stop()

    memory.start()
    memory.store(CognitiveContext("after"))

    assert len(memory.retrieve(None)) == 2
    memory.close()


def test_sqlite_memory_creates_missing_parent_dirs(tmp_path):
    path = str(tmp_path / "nested" / "memory" / "chat.db")
    memory = SqliteMemory(path)

    assert os.path.exists(path)

    memory.store(CognitiveContext("hello"))
    assert len(memory.retrieve(None)) == 1
    memory.close()


def test_sqlite_memory_stores_non_context_objects():
    memory = SqliteMemory()
    memory.store("a plain note")

    entries = memory.retrieve(None)
    assert len(entries) == 1
    assert entries[0].prompt is None


# --- SqliteKnowledge ----------------------------------------------------------


def test_sqlite_knowledge_queries_facts_by_keyword():
    knowledge = SqliteKnowledge()
    knowledge.add("kernel", "composition root")
    knowledge.add("brain", "cognition")

    context = CognitiveContext("tell me about the kernel")

    assert knowledge.query(context) == {"kernel": "composition root"}


def test_sqlite_knowledge_round_trips_non_string_values():
    knowledge = SqliteKnowledge()
    knowledge.add("count", 42)
    knowledge.add("meta", {"a": 1})

    assert knowledge.query(CognitiveContext("count the meta")) == {"count": 42, "meta": {"a": 1}}


def test_sqlite_knowledge_add_replaces_existing_fact():
    knowledge = SqliteKnowledge()
    knowledge.add("hours", "9am")
    knowledge.add("hours", "10am")

    assert knowledge.query(CognitiveContext("hours")) == {"hours": "10am"}


def test_sqlite_knowledge_persists_across_connections(tmp_path):
    path = str(tmp_path / "facts.db")
    first = SqliteKnowledge(path)
    first.add("hours", "9am-6pm")
    first.close()

    second = SqliteKnowledge(path)
    assert second.query(CognitiveContext("hours")) == {"hours": "9am-6pm"}
    second.close()


def test_sqlite_knowledge_lifecycle_start_stop(tmp_path):
    knowledge = SqliteKnowledge(str(tmp_path / "lifecycle.db"))
    knowledge.add("a", 1)
    knowledge.stop()

    knowledge.start()
    assert knowledge.query(CognitiveContext("a")) == {"a": 1}
    knowledge.close()


def test_sqlite_knowledge_creates_missing_parent_dirs(tmp_path):
    path = str(tmp_path / "deep" / "facts.db")
    knowledge = SqliteKnowledge(path)

    assert os.path.exists(path)

    knowledge.add("hours", "9am")
    assert knowledge.query(CognitiveContext("hours")) == {"hours": "9am"}
    knowledge.close()


# --- Integration with the app -------------------------------------------------


def test_sqlite_providers_work_with_the_brain(tmp_path):
    app = create_app(
        llm=CallableLLM(lambda prompt: f"answer:{prompt}"),
        memory=SqliteMemory(str(tmp_path / "chat.db")),
        knowledge=SqliteKnowledge(str(tmp_path / "facts.db")),
    )
    app.knowledge.add("hello", "a greeting")

    app.chat("hello")
    second = app.chat("what did I just say?")

    assert "hello" in second
    entries = app.memory.retrieve(None)
    assert len(entries) == 2

    app.stop()  # closes the sqlite connections via the kernel lifecycle

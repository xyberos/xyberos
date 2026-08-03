from xyberos.memory import InMemoryMemory
from xyberos.runtime.context import CognitiveContext


def test_in_memory_memory_stores_and_retrieves_entries():
    memory = InMemoryMemory()
    first = CognitiveContext("first")
    second = CognitiveContext("second")

    memory.store(first)
    memory.store(second)

    assert memory.retrieve(first) == [first, second]


def test_in_memory_memory_clear_removes_all_entries():
    memory = InMemoryMemory()
    memory.store(CognitiveContext("entry"))

    memory.clear()

    assert memory.retrieve(CognitiveContext("entry")) == []

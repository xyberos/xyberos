import pytest

from xyberos.contracts import Memory, MemoryProvider
from xyberos.runtime.context import CognitiveContext


class RecordingMemory(Memory):
    def __init__(self):
        self.stored = []

    def retrieve(self, context):
        return self.stored[-1] if self.stored else None

    def store(self, context):
        self.stored.append(context)


def test_memory_contract_requires_retrieve_and_store_methods():
    with pytest.raises(TypeError):
        Memory()


def test_memory_contract_can_be_implemented_without_runtime_coupling():
    memory = RecordingMemory()
    context = CognitiveContext("remember this")

    memory.store(context)

    assert isinstance(memory, MemoryProvider)
    assert memory.retrieve(context) is context

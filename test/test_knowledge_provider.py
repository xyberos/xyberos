from xyberos.knowledge import InMemoryKnowledge
from xyberos.runtime.context import CognitiveContext


def test_in_memory_knowledge_queries_facts_by_keyword():
    knowledge = InMemoryKnowledge({"kernel": "composition root", "brain": "cognition"})
    context = CognitiveContext("tell me about the kernel")

    assert knowledge.query(context) == {"kernel": "composition root"}


def test_in_memory_knowledge_add_registers_new_facts():
    knowledge = InMemoryKnowledge()
    knowledge.add("runtime", "execution")

    assert knowledge.query(CognitiveContext("runtime layer")) == {"runtime": "execution"}

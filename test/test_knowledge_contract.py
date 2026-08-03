import pytest

from contracts import Knowledge, KnowledgeProvider
from runtime.context import CognitiveContext


class StaticKnowledge(Knowledge):
    def query(self, context):
        return [{"source": "test", "content": context.prompt}]


def test_knowledge_contract_requires_a_query_method():
    with pytest.raises(TypeError):
        Knowledge()


def test_knowledge_contract_supports_provider_specific_results():
    context = CognitiveContext("find architecture guidance")
    knowledge = StaticKnowledge()

    assert isinstance(knowledge, KnowledgeProvider)
    assert knowledge.query(context) == [{"source": "test", "content": "find architecture guidance"}]

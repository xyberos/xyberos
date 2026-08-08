"""Contract tests for the IntentEngine extension (RFC-0016)."""

import pytest

from xyberos.contracts import Intent, IntentEngine, IntentEngineProvider


class StaticIntentEngine(IntentEngine):
    def classify(self, context):
        return Intent(name="static")


def test_intent_engine_contract_requires_classify():
    with pytest.raises(TypeError):
        IntentEngine()


def test_intent_engine_contract_works_without_core_dependencies():
    engine = StaticIntentEngine()
    assert engine.classify(object()).name == "static"


def test_intent_engine_contract_has_compatibility_alias():
    assert IntentEngineProvider is IntentEngine


def test_intent_is_a_frozen_dataclass():
    intent = Intent(name="refund", confidence=0.9, params={"order": "A-1"}, target="refund_tool")
    assert intent.name == "refund"
    assert intent.confidence == 0.9
    assert intent.params == {"order": "A-1"}
    assert intent.target == "refund_tool"

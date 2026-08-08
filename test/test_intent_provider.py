"""Provider tests for the IntentEngine contract (RFC-0016)."""

from xyberos.intent import HeuristicIntentEngine, IntentRule
from xyberos.runtime.context import CognitiveContext


def test_heuristic_intent_matches_first_rule_case_insensitively():
    engine = HeuristicIntentEngine(
        [
            IntentRule("refund", ("refund", "money back")),
            IntentRule("faq", ("hours", "open")),
        ]
    )

    assert engine.classify(CognitiveContext("I want a refund")).name == "refund"
    assert engine.classify(CognitiveContext("REFUND please")).name == "refund"
    assert engine.classify(CognitiveContext("What are your hours?")).name == "faq"


def test_heuristic_intent_returns_fallback_with_zero_confidence():
    engine = HeuristicIntentEngine(fallback="general")

    intent = engine.classify(CognitiveContext("hello world"))

    assert intent.name == "general"
    assert intent.confidence == 0.0


def test_heuristic_intent_carries_routing_target():
    engine = HeuristicIntentEngine([IntentRule("refund", ("refund",), target="refund_tool")])

    assert engine.classify(CognitiveContext("please refund my order")).target == "refund_tool"


def test_heuristic_intent_add_rule_appends_to_priority():
    engine = HeuristicIntentEngine([IntentRule("refund", ("refund",))])
    engine.add_rule(IntentRule("chat", ("hello",)))

    assert engine.classify(CognitiveContext("hello")).name == "chat"
    assert engine.classify(CognitiveContext("hello refund")).name == "refund"


def test_heuristic_intent_ignores_non_string_contexts():
    engine = HeuristicIntentEngine([IntentRule("refund", ("refund",))])

    assert engine.classify(object()).name == "general"

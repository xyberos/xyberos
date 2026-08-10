import pytest

from xyberos.contracts import Responder, Router, Template


class StaticResponder(Responder):
    def respond(self, context):
        return "handled"


def test_responder_contract_requires_a_respond_method():
    with pytest.raises(TypeError):
        Responder()


def test_responder_contract_defaults_to_full_confidence():
    assert StaticResponder().confidence(None) == 1.0


def test_responder_contract_can_handle_without_brain_or_runtime_dependencies():
    context = object()
    assert StaticResponder().respond(context) == "handled"


def test_router_contract_requires_a_respond_method():
    with pytest.raises(TypeError):
        Router()


def test_template_dataclass_holds_pattern_variants_and_confidence():
    template = Template(pattern="greeting", variants=("Hello!", "Hi!"), confidence=0.9)
    assert template.pattern == "greeting"
    assert template.variants == ("Hello!", "Hi!")
    assert template.confidence == 0.9
    assert template.requires_context == ()

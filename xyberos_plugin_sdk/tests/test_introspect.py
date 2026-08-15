"""Tests for the shared contract introspection layer."""

from xyberos.contracts import LLMProvider, Tool
from xyberos_plugin_sdk import introspect as it


def test_abstract_members_of_abc_contract():
    assert it.abstract_members(Tool) == {"name": "property", "execute": "method"}


def test_abstract_members_of_protocol_contract():
    assert it.abstract_members(LLMProvider) == {"generate": "method"}


def test_contract_for_and_plugin_types():
    assert it.contract_for("tool") is Tool
    assert "tool" in it.plugin_types()
    assert "other" in it.plugin_types()


def test_contract_for_unknown_type_raises():
    try:
        it.contract_for("nope")
    except ValueError as exc:
        assert "unknown plugin type" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_is_concrete_and_missing_abstracts():
    class Full(Tool):
        @property
        def name(self):
            return "x"

        def execute(self, context, **args):
            return None

    class Partial(Tool):
        @property
        def name(self):
            return "x"

    assert it.is_concrete(Full)
    assert not it.is_concrete(Partial)
    assert set(it.missing_abstracts(Partial)) == {"execute"}


def test_signature_compatible():
    class Good(Tool):
        @property
        def name(self):
            return "x"

        def execute(self, context, **args):
            return None

    class Bad(Tool):
        @property
        def name(self):
            return "x"

        def execute(self):  # drops required `context`
            return None

    assert it.signature_compatible(Good, Tool, "execute")
    assert not it.signature_compatible(Bad, Tool, "execute")


def test_render_stub_property_and_method():
    property_stub = it.render_stub(Tool, "name", name_value="demo")
    assert "@property" in property_stub
    assert "return 'demo'" in property_stub

    method_stub = it.render_stub(Tool, "execute")
    assert "def execute" in method_stub
    assert "raise NotImplementedError" in method_stub
    compile("class X:\n" + property_stub + method_stub, "<stub>", "exec")

import pytest

from xyberos.contracts import Tool
from xyberos.exceptions import ToolAlreadyRegisteredError, ToolNotFoundError
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import ToolRegistry


class UppercaseTool(Tool):
    @property
    def name(self):
        return "uppercase"

    def execute(self, context, **arguments):
        suffix = arguments.get("suffix", "")
        return f"{context.prompt.upper()}{suffix}"


def test_tool_registry_registers_and_executes_tools():
    registry = ToolRegistry([UppercaseTool()])
    context = CognitiveContext("hello")

    assert registry.names == ("uppercase",)
    assert registry.execute("uppercase", context, suffix="!") == "HELLO!"


def test_tool_registry_validates_and_looks_up_tools():
    registry = ToolRegistry()
    tool = UppercaseTool()

    assert registry.register(tool) is tool
    with pytest.raises(ToolAlreadyRegisteredError, match="already registered"):
        registry.register(tool)
    with pytest.raises(ToolNotFoundError, match="No tool"):
        registry.get("missing")
    with pytest.raises(TypeError, match="Tool contract"):
        registry.register(object())
    assert registry.get("uppercase") is tool

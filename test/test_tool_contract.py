import pytest

from xyberos.contracts import Tool
from xyberos.runtime.context import CognitiveContext


class UppercaseTool(Tool):
    @property
    def name(self):
        return "uppercase"

    def execute(self, context, **arguments):
        suffix = arguments.get("suffix", "")
        return f"{context.prompt.upper()}{suffix}"


def test_tool_contract_requires_name_and_execute():
    with pytest.raises(TypeError):
        Tool()


def test_tool_contract_is_context_agnostic_and_executable():
    tool = UppercaseTool()
    context = CognitiveContext("tool contract")

    assert tool.name == "uppercase"
    assert tool.execute(context, suffix="!") == "TOOL CONTRACT!"

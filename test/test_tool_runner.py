import pytest

from xyberos.contracts import Tool
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import ToolRunner


class PrefixTool(Tool):
    @property
    def name(self):
        return "prefix"

    def execute(self, context, **arguments):
        return f"{arguments.get('prefix', '')}{context.prompt}"


def test_tool_runner_dispatches_and_chooses_tools():
    runner = ToolRunner([PrefixTool()])
    context = CognitiveContext("hello")

    assert runner.names == ("prefix",)
    assert runner.choose(context) == "prefix"
    assert runner.dispatch(context, prefix="pre-") == "pre-hello"


def test_tool_runner_validates_context_and_registration():
    runner = ToolRunner()

    with pytest.raises(ValueError, match="no tools"):
        runner.choose(CognitiveContext("hello"))
    with pytest.raises(TypeError, match="CognitiveContext"):
        runner.dispatch("not a context")  # type: ignore[arg-type]

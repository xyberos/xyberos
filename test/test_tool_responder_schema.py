import json

from xyberos.llm import CallableLLM
from xyberos.router import ResponderChain, ToolResponder
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import FunctionTool, SchemaToolCaller, ToolRunner


def reverse_text(text: str) -> str:
    return text[::-1]


class JsonLLM:
    def __init__(self, payload):
        self._payload = payload

    def generate(self, prompt):
        return json.dumps(self._payload)


def test_tool_responder_schema_mode_runs_chosen_tool():
    runner = ToolRunner([FunctionTool("reverse_text", reverse_text, description="Reverse text")])
    caller = SchemaToolCaller(JsonLLM({"tool": "reverse_text", "arguments": {"text": "hello"}}), runner)
    responder = ToolResponder(runner, caller=caller)

    assert responder.respond(CognitiveContext("please reverse hello")) == "olleh"


def test_tool_responder_schema_mode_escalates_when_no_tool():
    runner = ToolRunner([FunctionTool("reverse_text", reverse_text, description="Reverse text")])
    caller = SchemaToolCaller(JsonLLM({"tool": None, "arguments": {}}), runner)
    chain = ResponderChain([("tool", ToolResponder(runner, caller=caller))], fallback=lambda c: "llm")

    assert chain.respond(CognitiveContext("hello there")) == "llm"


def test_tool_responder_schema_mode_confidence_with_tools():
    runner = ToolRunner([FunctionTool("reverse_text", reverse_text, description="Reverse text")])
    caller = SchemaToolCaller(JsonLLM({"tool": None}), runner)
    responder = ToolResponder(runner, caller=caller)

    assert responder.confidence(CognitiveContext("anything")) == 1.0


def test_tool_responder_schema_mode_confidence_without_tools():
    runner = ToolRunner()
    caller = SchemaToolCaller(JsonLLM({"tool": None}), runner)
    responder = ToolResponder(runner, caller=caller)

    assert responder.confidence(CognitiveContext("anything")) == 0.0

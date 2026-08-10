from xyberos.contracts import Tool
from xyberos.router import ResponderChain, ToolResponder
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import ToolRunner


class ReverseTool(Tool):
    @property
    def name(self):
        return "reverse"

    def execute(self, context, **arguments):
        return context.prompt[::-1]


class UppercaseTool(Tool):
    @property
    def name(self):
        return "uppercase"

    def execute(self, context, **arguments):
        return context.prompt.upper()


class Intent:
    def __init__(self, name, target=None):
        self.name = name
        self.target = target


def test_tool_responder_runs_tool_when_name_appears_in_prompt():
    responder = ToolResponder(ToolRunner([ReverseTool()]))
    assert responder.respond(CognitiveContext("please reverse this")) == "siht esrever esaelp"


def test_tool_responder_returns_none_when_no_tool_matches():
    responder = ToolResponder(ToolRunner([ReverseTool()]))
    assert responder.respond(CognitiveContext("hello there")) is None


def test_tool_responder_runs_tool_via_intent_target():
    responder = ToolResponder(ToolRunner([ReverseTool()]))
    context = CognitiveContext("transform this")
    context.intent = Intent("transform", target="reverse")
    assert responder.respond(context) == "siht mrofsnart"


def test_tool_responder_returns_none_when_no_tools_registered():
    responder = ToolResponder(ToolRunner())
    assert responder.respond(CognitiveContext("anything")) is None


def test_tool_responder_confidence_reflects_match():
    responder = ToolResponder(ToolRunner([ReverseTool()]))
    assert responder.confidence(CognitiveContext("please reverse this")) == 1.0
    assert responder.confidence(CognitiveContext("hello there")) == 0.0


def test_tool_responder_does_not_run_first_tool_by_default():
    # The fallback in ToolRunner.choose (first registered tool) must NOT fire:
    # with no prompt mention and no intent target, the responder escalates.
    responder = ToolResponder(ToolRunner([ReverseTool(), UppercaseTool()]))
    assert responder.respond(CognitiveContext("nothing matches here")) is None


def test_tool_responder_in_chain_answers_before_llm_when_tool_matches():
    chain = ResponderChain([("tool", ToolResponder(ToolRunner([ReverseTool()])))], fallback=lambda c: "llm")
    assert chain.respond(CognitiveContext("please reverse this")) == "siht esrever esaelp"


def test_tool_responder_in_chain_escalates_when_no_tool_matches():
    chain = ResponderChain([("tool", ToolResponder(ToolRunner([ReverseTool()])))], fallback=lambda c: "llm")
    assert chain.respond(CognitiveContext("hello there")) == "llm"

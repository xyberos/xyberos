import pytest

from xyberos.brain.brain import Brain
from xyberos.runtime.context import CognitiveContext
from xyberos.llm import CallableLLM
from xyberos.contracts import Tool
from xyberos.tools import ToolRunner


class RecordingLogger:
    def __init__(self):
        self.messages = []

    def debug(self, message):
        self.messages.append(message)


class InvalidResponseModel:
    def generate(self, prompt):
        return 1


class ReverseTool(Tool):
    @property
    def name(self):
        return "reverse"

    def execute(self, context, **arguments):
        return context.prompt[::-1]


def test_brain_sends_prompt_to_llm_and_logs_generation():
    logger = RecordingLogger()
    brain = Brain(CallableLLM(lambda prompt: f"answer:{prompt}"), logger)

    assert brain.chat(CognitiveContext("question")) == "answer:question"
    assert logger.messages == ["Generating response"]


def test_brain_uses_tool_runner_before_llm_when_a_tool_matches():
    brain = Brain(CallableLLM(lambda prompt: f"answer:{prompt}"), tool_runner=ToolRunner([ReverseTool()]))

    assert brain.chat(CognitiveContext("reverse")) == "esrever"


def test_brain_rejects_invalid_context_and_non_text_response():
    with pytest.raises(TypeError, match="CognitiveContext"):
        Brain().chat("not a context")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="LLM must return a string"):
        Brain(InvalidResponseModel()).chat(CognitiveContext("question"))

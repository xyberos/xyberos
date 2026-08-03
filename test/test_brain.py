import pytest

from brain.brain import Brain
from brain.llm import CallableLLM
from runtime.context import CognitiveContext


class RecordingLogger:
    def __init__(self):
        self.messages = []

    def debug(self, message):
        self.messages.append(message)


class InvalidResponseModel:
    def generate(self, prompt):
        return 1


def test_brain_sends_prompt_to_llm_and_logs_generation():
    logger = RecordingLogger()
    brain = Brain(CallableLLM(lambda prompt: f"answer:{prompt}"), logger)

    assert brain.chat(CognitiveContext("question")) == "answer:question"
    assert logger.messages == ["Generating response"]


def test_brain_rejects_invalid_context_and_non_text_response():
    with pytest.raises(TypeError, match="CognitiveContext"):
        Brain().chat("not a context")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="LLM must return a string"):
        Brain(InvalidResponseModel()).chat(CognitiveContext("question"))

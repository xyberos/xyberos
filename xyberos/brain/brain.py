"""Cognitive orchestration layer."""

from .llm import EchoLLM, LLMProvider


class Brain:
    """Validates requests and delegates response generation to a chat model."""

    def __init__(self, llm: LLMProvider | None = None, logger: object | None = None) -> None:
        self.llm = llm or EchoLLM()
        self.logger = logger

    def chat(self, context: object) -> str:
        prompt = getattr(context, "prompt", None)
        if not isinstance(prompt, str):
            raise TypeError("context must be a CognitiveContext")
        if self.logger is not None:
            self.logger.debug("Generating response")
        response = self.llm.generate(prompt)
        if not isinstance(response, str):
            raise TypeError("LLM must return a string")
        return response

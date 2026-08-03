"""Cognitive orchestration layer."""

try:
    from ..runtime.context import CognitiveContext
except ImportError:  # pragma: no cover - depends on import style
    from runtime.context import CognitiveContext

from .llm import EchoLLM, LLMProvider


class Brain:
    """Validates requests and delegates response generation to a chat model."""

    def __init__(self, llm: LLMProvider | None = None, logger: object | None = None) -> None:
        self.llm = llm or EchoLLM()
        self.logger = logger

    def chat(self, context: CognitiveContext) -> str:
        if not isinstance(context, CognitiveContext):
            raise TypeError("context must be a CognitiveContext")
        if self.logger is not None:
            self.logger.debug("Generating response")
        response = self.llm.generate(context.prompt)
        if not isinstance(response, str):
            raise TypeError("LLM must return a string")
        return response

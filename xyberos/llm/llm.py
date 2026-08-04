"""Language model service implementations."""

from collections.abc import Callable

from ..contracts.llm import LLMProvider


class CallableLLM:
    """Adapt a callable (SDK function, local model, or test double) to LLMProvider."""

    def __init__(self, generate: Callable[[str], str]) -> None:
        if not callable(generate):
            raise TypeError("generate must be callable")
        self._generate = generate

    def generate(self, prompt: str) -> str:
        response = self._generate(prompt)
        if not isinstance(response, str):
            raise TypeError("LLM generator must return a string")
        return response


class EchoLLM:
    """A dependency-free default model useful for local development and tests."""

    def generate(self, prompt: str) -> str:
        return prompt


# Compatibility alias for older provider naming.
ChatModel = LLMProvider

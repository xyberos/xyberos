"""Language model service implementations."""

from collections.abc import Awaitable, Callable

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


class StreamingLLM:
    """Adapt a ``(generate, stream)`` pair to an LLM provider with streaming.

    ``stream(prompt, on_token)`` must call ``on_token`` for each chunk and
    return the fully assembled response string.
    """

    def __init__(
        self,
        generate: Callable[[str], str],
        stream: Callable[[str, Callable[[str], None]], str],
    ) -> None:
        if not callable(generate):
            raise TypeError("generate must be callable")
        if not callable(stream):
            raise TypeError("stream must be callable")
        self._generate = generate
        self._stream = stream

    def generate(self, prompt: str) -> str:
        return self._generate(prompt)

    def stream(self, prompt: str, on_token: Callable[[str], None]) -> str:
        return self._stream(prompt, on_token)


class AsyncLLM:
    """Adapt an async ``agenerate`` coroutine function to an async LLM provider.

    Implements only ``agenerate``; use it with the async pipeline
    (``app.achat`` / ``app.arun``). It is not usable from the synchronous API.
    """

    def __init__(self, agenerate: Callable[[str], Awaitable[str]]) -> None:
        if not callable(agenerate):
            raise TypeError("agenerate must be callable")
        self._agenerate = agenerate

    async def agenerate(self, prompt: str) -> str:
        response = await self._agenerate(prompt)
        if not isinstance(response, str):
            raise TypeError("LLM generator must return a string")
        return response


class EchoLLM:
    """A dependency-free default model useful for local development and tests."""

    def generate(self, prompt: str) -> str:
        return prompt


# Compatibility alias for older provider naming.
ChatModel = LLMProvider

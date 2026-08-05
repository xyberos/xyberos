"""Tests for the model provider adapters."""

import importlib.util
from types import SimpleNamespace

import pytest

from xyberos import create_app
from xyberos.exceptions import ProviderError
from xyberos.llm import (
    AnthropicLLM,
    GeminiLLM,
    OllamaLLM,
    OpenAICompatibleLLM,
    OpenAILLM,
)


def test_openai_compatible_llm_builds_request_and_parses():
    calls = []

    def post(url, payload, headers):
        calls.append((url, payload, headers))
        return {"choices": [{"message": {"content": "compatible"}}]}

    llm = OpenAICompatibleLLM(
        "gpt-x", base_url="https://api.example.com/v1/", api_key="secret", post=post
    )

    assert llm.generate("hello") == "compatible"
    url, payload, headers = calls[0]
    assert url == "https://api.example.com/v1/chat/completions"
    assert payload == {"model": "gpt-x", "messages": [{"role": "user", "content": "hello"}]}
    assert headers["Authorization"] == "Bearer secret"


def test_ollama_llm_builds_request_and_parses():
    calls = []

    def post(url, payload, headers):
        calls.append((url, payload))
        return {"response": "from ollama"}

    llm = OllamaLLM("llama3", base_url="http://localhost:11434", post=post)

    assert llm.generate("hi") == "from ollama"
    url, payload = calls[0]
    assert url == "http://localhost:11434/api/generate"
    assert payload == {"model": "llama3", "prompt": "hi", "stream": False}


def test_ollama_llm_parses_streaming_tokens():
    class FakeResponse:
        def __iter__(self):
            return iter(
                [
                    b'{"response": "hel"}\n',
                    b'{"response": "lo"}\n',
                    b"not json\n",
                    b'{"done": true}\n',
                ]
            )

    llm = OllamaLLM("llama3")

    assert list(llm._iter_tokens(FakeResponse())) == ["hel", "lo"]
    assert callable(llm.stream)


def test_openai_llm_uses_an_injected_client():
    class FakeCompletions:
        def __init__(self, content):
            self._content = content
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=self._content))]
            )

    client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions("hi there")))
    llm = OpenAILLM("gpt-x", client=client)

    assert llm.generate("hi") == "hi there"
    call = client.chat.completions.calls[0]
    assert call["model"] == "gpt-x"
    assert call["messages"] == [{"role": "user", "content": "hi"}]


def test_adapters_validate_constructor_inputs():
    with pytest.raises(ValueError, match="model"):
        OpenAILLM("")
    with pytest.raises(ValueError, match="base_url"):
        OpenAICompatibleLLM("gpt-x", base_url="")
    with pytest.raises(ValueError, match="model"):
        OllamaLLM("")


def test_adapter_works_as_an_llm_provider_in_create_app():
    def post(url, payload, headers):
        return {"response": "ollama answer"}

    app = create_app(llm=OllamaLLM("llama3", post=post))

    assert app.chat("hi") == "ollama answer"


def test_openai_llm_requires_the_sdk_when_missing():
    if importlib.util.find_spec("openai") is not None:
        pytest.skip("openai is installed; cannot test the missing-SDK path")

    with pytest.raises(ProviderError, match="openai"):
        OpenAILLM("gpt-x").generate("hi")


def test_anthropic_llm_requires_the_sdk_when_missing():
    if importlib.util.find_spec("anthropic") is not None:
        pytest.skip("anthropic is installed; cannot test the missing-SDK path")

    with pytest.raises(ProviderError, match="anthropic"):
        AnthropicLLM().generate("hi")


def test_gemini_llm_requires_the_sdk_when_missing():
    if importlib.util.find_spec("google.generativeai") is not None:
        pytest.skip("google-generativeai is installed; cannot test the missing-SDK path")

    with pytest.raises(ProviderError, match="google"):
        GeminiLLM().generate("hi")

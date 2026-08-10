"""LLM adapters for common model providers.

All adapters are dependency-light: the HTTP-based ones (``OllamaLLM``,
``OllamaEmbeddingLLM``, ``OpenAICompatibleLLM``, ``OpenAIEmbeddingLLM``) use
only the standard library, while the SDK-based ones (``OpenAILLM``,
``AnthropicLLM``, ``GeminiLLM``) import their SDK lazily on first use and raise
a clear :class:`~exceptions.provider.ProviderError` when it is not installed.
This keeps the core package free of runtime dependencies.
"""

from __future__ import annotations

import importlib
import json
import urllib.request
from collections.abc import Callable
from typing import Any

from ..exceptions.provider import ProviderError


def require(package: str, pip_name: str | None = None) -> Any:
    """Import ``package`` or raise a clear :class:`ProviderError`."""
    try:
        return importlib.import_module(package)
    except ImportError as exc:
        name = pip_name or package
        raise ProviderError(
            f"the '{name}' package is required; install it with 'pip install {name}'"
        ) from exc


def _default_post(url: str, payload: dict[str, Any], headers: dict[str, Any]) -> dict[str, Any]:
    """POST ``payload`` as JSON and return the parsed JSON response."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


# A callable that POSTs JSON and returns the parsed response; injectable for tests.
PostCallable = Callable[[str, dict[str, Any], dict[str, Any]], dict[str, Any]]


class OpenAICompatibleLLM:
    """Talk to any OpenAI-compatible ``/chat/completions`` endpoint.

    Works with the OpenAI API and local servers such as llama.cpp, vLLM, and LM
    Studio. Uses only the standard library; pass ``post`` to inject a transport.
    """

    def __init__(
        self,
        model: str,
        *,
        base_url: str,
        api_key: str | None = None,
        post: PostCallable | None = None,
    ) -> None:
        if not isinstance(model, str) or not model.strip():  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
            raise ValueError("model must be a non-empty string")
        if not base_url:
            raise ValueError("base_url must be provided")
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._post = post or _default_post

    def generate(self, prompt: str) -> str:
        """Generate a chat completion for ``prompt``."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
        }
        data = self._post(f"{self._base_url}/chat/completions", payload, headers)
        return data["choices"][0]["message"]["content"]


class OllamaLLM:
    """Call a local Ollama server over stdlib HTTP (no dependencies)."""

    def __init__(
        self,
        model: str = "llama3.2",
        *,
        base_url: str = "http://localhost:11434",
        post: PostCallable | None = None,
    ) -> None:
        if not isinstance(model, str) or not model.strip():  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
            raise ValueError("model must be a non-empty string")
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._post = post or _default_post

    def generate(self, prompt: str) -> str:
        """Generate text from the local Ollama server."""
        payload: dict[str, Any] = {"model": self._model, "prompt": prompt, "stream": False}
        data = self._post(
            f"{self._base_url}/api/generate",
            payload,
            {"Content-Type": "application/json"},
        )
        return data["response"]

    def stream(self, prompt: str, on_token: Callable[[str], None]) -> str:
        """Stream tokens from the local Ollama server (NDJSON ``/api/generate``)."""
        payload: dict[str, Any] = {"model": self._model, "prompt": prompt, "stream": True}
        request = urllib.request.Request(
            self._base_url + "/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        parts: list[str] = []
        with urllib.request.urlopen(request) as response:
            for token in self._iter_tokens(response):
                on_token(token)
                parts.append(token)
        return "".join(parts)

    @staticmethod
    def _iter_tokens(response: Any):
        """Yield text tokens from Ollama's streaming newline-delimited JSON."""
        for raw in response:
            line = raw.decode("utf-8").strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            token = data.get("response", "")
            if token:
                yield token


class OpenAILLM:
    """Official OpenAI chat-completions adapter (lazy SDK import)."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
        client: Any | None = None,
    ) -> None:
        if not isinstance(model, str) or not model.strip():  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
            raise ValueError("model must be a non-empty string")
        self._model = model
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout
        self._client = client  # injectable for tests; otherwise built lazily

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        openai = require("openai")
        kwargs: dict[str, Any] = {"timeout": self._timeout}
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._base_url:
            kwargs["base_url"] = self._base_url
        self._client = openai.OpenAI(**kwargs)
        return self._client

    def generate(self, prompt: str) -> str:
        """Generate a chat completion using the OpenAI SDK."""
        client = self._get_client()
        response = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content


class AnthropicLLM:
    """Official Anthropic messages adapter (lazy SDK import)."""

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-latest",
        *,
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        if not isinstance(model, str) or not model.strip():  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
            raise ValueError("model must be a non-empty string")
        self._model = model
        self._api_key = api_key
        self._client = client  # injectable for tests; otherwise built lazily

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        anthropic = require("anthropic")
        kwargs: dict[str, Any] = {}
        if self._api_key:
            kwargs["api_key"] = self._api_key
        self._client = anthropic.Anthropic(**kwargs)
        return self._client

    def generate(self, prompt: str) -> str:
        """Generate a message using the Anthropic SDK."""
        client = self._get_client()
        response = client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")


class GeminiLLM:
    """Official Google Gemini adapter (lazy SDK import)."""

    def __init__(
        self,
        model: str = "gemini-1.5-flash",
        *,
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        if not isinstance(model, str) or not model.strip():  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
            raise ValueError("model must be a non-empty string")
        self._model = model
        self._api_key = api_key
        self._client = client  # injectable for tests; otherwise built lazily

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        google = require("google.generativeai", pip_name="google-generativeai")
        if self._api_key:
            google.configure(api_key=self._api_key)
        self._client = google.GenerativeModel(self._model)
        return self._client

    def generate(self, prompt: str) -> str:
        """Generate content using the Google Gemini SDK."""
        client = self._get_client()
        response = client.generate_content(prompt)
        return response.text


class OpenAIEmbeddingLLM:
    """OpenAI-compatible ``/embeddings`` adapter (stdlib HTTP, no dependencies).

    Exposes the duck-typed ``embed(text) -> list[float]`` capability against any
    OpenAI-compatible embeddings endpoint (OpenAI, local servers, etc.). Pass
    ``post`` to inject a transport for tests.
    """

    def __init__(
        self,
        model: str,
        *,
        base_url: str,
        api_key: str | None = None,
        post: PostCallable | None = None,
    ) -> None:
        if not isinstance(model, str) or not model.strip():  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
            raise ValueError("model must be a non-empty string")
        if not base_url:
            raise ValueError("base_url must be provided")
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._post = post or _default_post

    def embed(self, text: str) -> list[float]:
        """Embed ``text`` into a float vector using the configured endpoint."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload: dict[str, Any] = {"model": self._model, "input": text}
        data = self._post(f"{self._base_url}/embeddings", payload, headers)
        return [float(value) for value in data["data"][0]["embedding"]]


class OllamaEmbeddingLLM:
    """Embed text with a local Ollama server over stdlib HTTP (no dependencies).

    Exposes the duck-typed ``embed(text) -> list[float]`` capability against
    Ollama's ``/api/embed`` endpoint, so a single local server can provide both
    chat (via :class:`OllamaLLM`) and real semantic embeddings — a fully-local,
    no-cloud semantic stack for the hybrid router. Uses only the standard
    library; pass ``post`` to inject a transport for tests.
    """

    def __init__(
        self,
        model: str = "nomic-embed-text",
        *,
        base_url: str = "http://localhost:11434",
        post: PostCallable | None = None,
    ) -> None:
        if not isinstance(model, str) or not model.strip():  # type: ignore[unnecessary-isinstance]  # defensive runtime guard
            raise ValueError("model must be a non-empty string")
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._post = post or _default_post

    def embed(self, text: str) -> list[float]:
        """Embed ``text`` into a float vector using the local Ollama server."""
        payload: dict[str, Any] = {"model": self._model, "input": text}
        data = self._post(
            f"{self._base_url}/api/embed",
            payload,
            {"Content-Type": "application/json"},
        )
        return [float(value) for value in data["embeddings"][0]]

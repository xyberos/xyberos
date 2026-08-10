RFC-0006 — LLM Provider Interface

Defines the provider abstraction.

Every model backend must implement:

class LLMProvider:

    def generate(self, prompt: str) -> str:
        ...

Optional capabilities (detected at runtime):

- ``stream(prompt, on_token)`` / ``astream(...)`` — incremental output
- ``agenerate(prompt)`` — async generation

Bundled adapters (``xyberos/llm/adapters.py``): ``OpenAILLM``, ``AnthropicLLM``,
and ``GeminiLLM`` (lazy SDK imports), plus ``OllamaLLM``, ``OllamaEmbeddingLLM``
and ``OpenAICompatibleLLM`` (stdlib HTTP). ``OllamaEmbeddingLLM`` exposes the
duck-typed ``embed(text)`` capability against Ollama's ``/api/embed`` endpoint,
so a local server can power real semantic embeddings with no SDK.

The Brain depends only on this interface.
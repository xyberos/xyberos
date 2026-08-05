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
and ``GeminiLLM`` (lazy SDK imports), plus ``OllamaLLM`` and
``OpenAICompatibleLLM`` (stdlib HTTP).

The Brain depends only on this interface.
RFC-0006 — LLM Provider Interface

Defines the provider abstraction.

Every model backend must implement:

class LLMProvider:

    def generate(self, prompt: str) -> str:
        ...

Possible implementations:

OpenAI
Ollama
Anthropic
Gemini
Local models

The Brain depends only on this interface.
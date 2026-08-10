"""Tests for the duck-typed embedding capability (RFC-0016, Phase 0)."""

import pytest

from xyberos.exceptions import ProviderError
from xyberos.llm import CallableLLM, EmbeddingLLM, HashEmbedder, OllamaEmbeddingLLM, OpenAIEmbeddingLLM


def test_embedding_llm_delegates_generate_and_embed():
    llm = EmbeddingLLM(
        CallableLLM(lambda prompt: f"echo:{prompt}"),
        embedder=lambda text: [1.0, 0.0],
    )

    assert llm.generate("hi") == "echo:hi"
    assert llm.embed("hi") == [1.0, 0.0]


def test_embedding_llm_raises_without_an_embedder():
    llm = EmbeddingLLM()

    with pytest.raises(ProviderError):
        llm.embed("hi")


def test_embedding_llm_rejects_non_callable_embedder():
    with pytest.raises(TypeError):
        EmbeddingLLM(embedder=42)


def test_hash_embedder_is_deterministic_and_unit_norm():
    embedder = HashEmbedder(dim=32)

    first = embedder("hello")
    second = embedder("hello")
    other = embedder("world")

    assert first == second
    assert first != other
    assert len(first) == 32
    assert abs(sum(value * value for value in first) ** 0.5 - 1.0) < 1e-6


def test_hash_embedder_rejects_invalid_dimension():
    with pytest.raises(ValueError):
        HashEmbedder(dim=0)


def test_openai_embedding_llm_posts_to_embeddings_endpoint():
    captured = {}

    def fake_post(url, payload, headers):
        captured["url"] = url
        captured["payload"] = payload
        return {"data": [{"embedding": [1.0, 2.0, 3.0]}]}

    adapter = OpenAIEmbeddingLLM(
        "text-embedding-3-small",
        base_url="https://api.example.com/v1",
        api_key="secret",
        post=fake_post,
    )

    assert adapter.embed("hi") == [1.0, 2.0, 3.0]
    assert captured["url"] == "https://api.example.com/v1/embeddings"
    assert captured["payload"] == {"model": "text-embedding-3-small", "input": "hi"}


def test_openai_embedding_llm_validates_constructor_inputs():
    with pytest.raises(ValueError, match="model"):
        OpenAIEmbeddingLLM("", base_url="https://api.example.com/v1")
    with pytest.raises(ValueError, match="base_url"):
        OpenAIEmbeddingLLM("model", base_url="")


def test_ollama_embedding_llm_posts_to_embed_endpoint():
    captured = {}

    def fake_post(url, payload, headers):
        captured["url"] = url
        captured["payload"] = payload
        return {"embeddings": [[1.0, 2.0, 3.0]]}

    adapter = OllamaEmbeddingLLM("nomic-embed-text", post=fake_post)

    assert adapter.embed("hi") == [1.0, 2.0, 3.0]
    assert captured["url"] == "http://localhost:11434/api/embed"
    assert captured["payload"] == {"model": "nomic-embed-text", "input": "hi"}


def test_ollama_embedding_llm_uses_custom_base_url_and_validates_model():
    captured = {}

    def fake_post(url, payload, headers):
        captured["url"] = url
        return {"embeddings": [[0.5, 0.25]]}

    adapter = OllamaEmbeddingLLM("mxbai-embed-large", base_url="http://ollama:11434/", post=fake_post)

    assert adapter.embed("hello") == [0.5, 0.25]
    assert captured["url"] == "http://ollama:11434/api/embed"
    with pytest.raises(ValueError, match="model"):
        OllamaEmbeddingLLM("", post=fake_post)

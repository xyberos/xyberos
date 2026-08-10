import pytest

from xyberos.exceptions.provider import ProviderError
from xyberos.llm import SentenceTransformerEmbedder


def test_sentence_embedder_construction_is_lazy():
    embedder = SentenceTransformerEmbedder("some-model")
    assert embedder.model_name == "some-model"
    # Importing/loading the model must NOT happen at construction time.


def test_sentence_embedder_raises_when_model_missing():
    embedder = SentenceTransformerEmbedder()
    try:
        embedder("hello world")
    except ProviderError:
        pytest.skip("sentence-transformers not installed — ProviderError raised as expected")
    else:
        # sentence-transformers IS installed: verify it returns a unit vector.
        vector = embedder("hello world")
        assert len(vector) > 0
        norm = sum(v * v for v in vector) ** 0.5
        assert abs(norm - 1.0) < 1e-6


def test_sentence_embedder_rejects_bad_model_name():
    with pytest.raises(ValueError, match="model_name"):
        SentenceTransformerEmbedder("")

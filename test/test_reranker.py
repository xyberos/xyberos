import pytest

from xyberos.contracts.vector import ScoredHit
from xyberos.exceptions.provider import ProviderError
from xyberos.vector import LexicalReranker, ScoreReranker


def _hits():
    return [
        ScoredHit(id="low", score=0.5, payload={"value": "alpha beta gamma"}),
        ScoredHit(id="high", score=0.9, payload={"value": "query term here"}),
    ]


def test_score_reranker_preserves_similarity_order():
    hits = _hits()
    reranked = ScoreReranker().rerank("query", hits)
    assert [hit.id for hit in reranked] == ["high", "low"]


def test_score_reranker_empty_input():
    assert ScoreReranker().rerank("query", []) == []


def test_lexical_reranker_requires_sklearn():
    reranker = LexicalReranker()
    try:
        result = reranker.rerank("query term", _hits())
    except ProviderError:
        pytest.skip("scikit-learn not installed — ProviderError raised as expected")
    else:
        # scikit-learn IS installed: verify it actually re-orders.
        assert result
        assert result[0].id == "high"


def test_lexical_reranker_rejects_bad_top_k():
    with pytest.raises(ValueError, match="top_k"):
        LexicalReranker(top_k=0)

import pytest

from runtime.context import CognitiveContext


def test_context_tracks_success_and_has_independent_metadata():
    first = CognitiveContext("hello")
    second = CognitiveContext("world")

    assert not first.succeeded
    first.response = "hi"
    assert first.succeeded

    first.metadata["request_id"] = "one"
    assert second.metadata == {}


@pytest.mark.parametrize("prompt, exception", [(None, TypeError), ("  ", ValueError)])
def test_context_rejects_invalid_prompts(prompt, exception):
    with pytest.raises(exception):
        CognitiveContext(prompt)  # type: ignore[arg-type]

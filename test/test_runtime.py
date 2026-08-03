import pytest

from xyberos.runtime.context import CognitiveContext
from xyberos.runtime.runtime import Runtime


class SuccessfulBrain:
    def chat(self, context):
        return f"response:{context.prompt}"


class FailingBrain:
    def chat(self, context):
        raise RuntimeError("provider unavailable")


def test_runtime_populates_and_returns_the_same_context():
    context = CognitiveContext("hello")

    result = Runtime(SuccessfulBrain()).run(context)

    assert result is context
    assert result.response == "response:hello"
    assert result.error is None


def test_runtime_records_errors_before_reraising_them():
    context = CognitiveContext("hello")

    with pytest.raises(RuntimeError, match="provider unavailable"):
        Runtime(FailingBrain()).run(context)

    assert isinstance(context.error, RuntimeError)


def test_runtime_rejects_non_context_values():
    with pytest.raises(TypeError, match="CognitiveContext"):
        Runtime(SuccessfulBrain()).run("hello")  # type: ignore[arg-type]

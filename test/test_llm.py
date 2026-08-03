import pytest

from xyberos.brain.llm import CallableLLM, EchoLLM, LLMProvider


def test_echo_llm_and_callable_llm_generate_text():
    assert EchoLLM().generate("hello") == "hello"
    assert CallableLLM(lambda prompt: prompt.upper()).generate("hello") == "HELLO"
    assert isinstance(EchoLLM(), LLMProvider)


def test_callable_llm_validates_callable_and_response_type():
    with pytest.raises(TypeError, match="generate must be callable"):
        CallableLLM(None)  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="must return a string"):
        CallableLLM(lambda _: 42).generate("hello")

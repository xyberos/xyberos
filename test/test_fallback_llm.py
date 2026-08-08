"""Tests for the FallbackLLM model cascade (RFC-0017)."""

import pytest

from xyberos import create_app
from xyberos.exceptions import ProviderError
from xyberos.llm import CallableLLM, FallbackLLM


def _raise(exc):
    def call(prompt):
        raise exc

    return call


def test_fallback_llm_uses_primary_when_it_works():
    primary = CallableLLM(lambda prompt: "primary")
    backup = CallableLLM(lambda prompt: "backup")
    llm = FallbackLLM(primary, backup)

    assert llm.generate("hi") == "primary"
    assert len(llm.models) == 2


def test_fallback_llm_falls_back_on_provider_error():
    primary = CallableLLM(_raise(ProviderError("down")))
    backup = CallableLLM(lambda prompt: "backup answer")

    llm = FallbackLLM(primary, backup)

    assert llm.generate("hi") == "backup answer"


def test_fallback_llm_raises_when_all_fail():
    primary = CallableLLM(_raise(ProviderError("primary down")))
    backup = CallableLLM(_raise(ProviderError("backup down")))

    llm = FallbackLLM(primary, backup)

    with pytest.raises(ProviderError, match="backup down"):
        llm.generate("hi")


def test_fallback_llm_does_not_catch_unrelated_errors():
    primary = CallableLLM(_raise(ValueError("bad input")))

    llm = FallbackLLM(primary, CallableLLM(lambda prompt: "backup"))

    with pytest.raises(ValueError):
        llm.generate("hi")


def test_fallback_llm_respects_custom_retry_on():
    primary = CallableLLM(_raise(TimeoutError("slow")))
    backup = CallableLLM(lambda prompt: "recovered")

    llm = FallbackLLM(primary, backup, retry_on=(TimeoutError,))

    assert llm.generate("hi") == "recovered"


def test_fallback_llm_validates_models():
    with pytest.raises(TypeError):
        FallbackLLM(object())  # no generate method


def test_fallback_llm_works_in_create_app():
    primary = CallableLLM(_raise(ProviderError("down")))
    backup = CallableLLM(lambda prompt: f"handled: {prompt}")

    app = create_app(llm=FallbackLLM(primary, backup))

    assert app.chat("hi") == "handled: hi"

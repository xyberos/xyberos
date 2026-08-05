"""Tests for config-driven production hardening in the Brain."""

import time

import pytest

from xyberos import create_app
from xyberos.llm import CallableLLM
from xyberos.utils import RetryError


def test_brain_retries_llm_calls_via_config():
    attempts = []

    def flaky(prompt):
        attempts.append(1)
        if len(attempts) < 3:
            raise RuntimeError("transient")
        return "ok"

    app = create_app(
        config={"brain.max_attempts": 3, "brain.retry_backoff": 0},
        llm=CallableLLM(flaky),
    )

    assert app.chat("hi") == "ok"
    assert len(attempts) == 3


def test_brain_raises_retry_error_when_attempts_exhausted():
    def always_fail(prompt):
        raise RuntimeError("boom")

    app = create_app(
        config={"brain.max_attempts": 2, "brain.retry_backoff": 0},
        llm=CallableLLM(always_fail),
    )

    with pytest.raises(RetryError, match="2 attempts"):
        app.chat("hi")


def test_brain_timeout_via_config():
    def slow(prompt):
        time.sleep(5)
        return "late"

    app = create_app(config={"brain.timeout": 0.05}, llm=CallableLLM(slow))

    with pytest.raises(TimeoutError, match="timed out"):
        app.chat("hi")


def test_default_brain_has_no_hardening():
    app = create_app()

    assert app.chat("hello") == "hello"

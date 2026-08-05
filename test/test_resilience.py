"""Tests for the resilience helpers: retries, rate limiting, and timeouts."""

import time

import pytest

from xyberos.utils import RateLimiter, RetryError, retry, with_timeout


def test_retry_succeeds_after_transient_failures():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("transient")
        return "done"

    assert retry(flaky, max_attempts=3, backoff=0) == "done"
    assert len(calls) == 3


def test_retry_raises_retry_error_when_exhausted():
    def always_fail():
        raise RuntimeError("boom")

    with pytest.raises(RetryError, match="3 attempts"):
        retry(always_fail, max_attempts=3, backoff=0)


def test_retry_only_retries_matching_exceptions():
    calls = []

    def fail_once():
        calls.append(1)
        raise KeyError("not retried")

    with pytest.raises(KeyError):
        retry(fail_once, max_attempts=3, retry_on=ValueError)
    assert len(calls) == 1  # KeyError propagated immediately


def test_retry_invokes_on_retry_callback():
    attempts = []

    def flaky():
        raise ValueError("x")

    with pytest.raises(RetryError):
        retry(flaky, max_attempts=3, backoff=0, on_retry=lambda attempt, exc: attempts.append(attempt))
    assert attempts == [1, 2]


def test_retry_validates_arguments():
    with pytest.raises(ValueError, match="positive"):
        retry(lambda: None, max_attempts=0)
    with pytest.raises(ValueError, match="non-negative"):
        retry(lambda: None, backoff=-1)


def test_rate_limiter_enforces_burst():
    limiter = RateLimiter(calls_per_second=1, burst=2)

    assert limiter.try_acquire()
    assert limiter.try_acquire()
    assert not limiter.try_acquire()  # burst exhausted


def test_rate_limiter_validates_arguments():
    with pytest.raises(ValueError, match="positive"):
        RateLimiter(calls_per_second=0)
    with pytest.raises(ValueError, match="positive"):
        RateLimiter(calls_per_second=1, burst=0)


def test_with_timeout_returns_value_and_reraises_errors():
    assert with_timeout(0.1, lambda: 42) == 42

    def boom():
        raise ValueError("inner")

    with pytest.raises(ValueError, match="inner"):
        with_timeout(0.1, boom)


def test_with_timeout_raises_when_slow():
    def slow():
        time.sleep(0.2)
        return "late"

    with pytest.raises(TimeoutError, match="timed out"):
        with_timeout(0.01, slow)


def test_with_timeout_disabled_when_non_positive():
    assert with_timeout(0, lambda: "now") == "now"

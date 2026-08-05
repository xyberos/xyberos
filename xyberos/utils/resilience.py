"""Resilience helpers: retries, rate limiting, and timeouts."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class RetryError(Exception):
    """Raised when a retried callable exhausts all attempts."""


def retry(
    func: Callable[[], T],
    *,
    max_attempts: int = 3,
    backoff: float = 0.1,
    retry_on: type[Exception] | tuple[type[Exception], ...] = Exception,
    on_retry: Callable[[int, Exception], None] | None = None,
) -> T:
    """Call ``func`` with retries and exponential backoff.

    ``max_attempts`` bounds the number of calls (1 means no retry). After each
    failure, ``backoff * 2 ** attempt`` seconds are waited (capped at
    ``backoff * 8``; ``backoff=0`` disables sleeping). Only exceptions matching
    ``retry_on`` are retried — anything else propagates immediately. When
    attempts are exhausted, :class:`RetryError` is raised with the last
    exception attached as the cause.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be a positive integer")
    if backoff < 0:
        raise ValueError("backoff must be non-negative")

    last: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return func()
        except retry_on as exc:  # type: ignore[misc]
            last = exc
            if attempt + 1 >= max_attempts:
                break
            if on_retry is not None:
                on_retry(attempt + 1, exc)
            time.sleep(min(backoff * (2**attempt), backoff * 8 or 1))
    assert last is not None
    raise RetryError(f"call failed after {max_attempts} attempts") from last


class RateLimiter:
    """A token-bucket rate limiter.

    ``calls_per_second`` refills the bucket continuously and ``burst`` sets the
    maximum burst size. ``acquire`` blocks until a token is available;
    ``try_acquire`` returns ``False`` immediately when no token is available.
    Thread-safe.
    """

    def __init__(self, *, calls_per_second: float, burst: int = 1) -> None:
        if calls_per_second <= 0:
            raise ValueError("calls_per_second must be positive")
        if burst < 1:
            raise ValueError("burst must be a positive integer")
        self._rate = calls_per_second
        self._capacity = float(burst)
        self._tokens = self._capacity
        self._updated = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        self._tokens = min(self._capacity, self._tokens + (now - self._updated) * self._rate)
        self._updated = now

    def try_acquire(self) -> bool:
        """Consume one token if available; return whether it was acquired."""
        with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    def acquire(self) -> None:
        """Block until a token is available, then consume it."""
        while not self.try_acquire():
            time.sleep(1.0 / self._rate)


def with_timeout(seconds: float, func: Callable[[], T]) -> T:
    """Run ``func`` with a best-effort timeout.

    Runs ``func`` in a daemon thread; if it does not complete within ``seconds``,
    raises ``TimeoutError`` (the worker keeps running in the background).
    ``seconds <= 0`` invokes ``func`` directly with no timeout.
    """
    if seconds <= 0:
        return func()

    result: dict[str, Any] = {}

    def worker() -> None:
        try:
            result["value"] = func()
        except BaseException as exc:  # noqa: BLE001 - re-raised in the caller
            result["error"] = exc

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join(timeout=seconds)
    if thread.is_alive():
        raise TimeoutError(f"call timed out after {seconds}s")
    if "error" in result:
        raise result["error"]  # type: ignore[misc]
    return result["value"]

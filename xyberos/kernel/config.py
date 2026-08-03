"""Configuration storage for the Xyberos kernel."""

from collections.abc import Mapping
from typing import Any


class Config:
    """A small mutable configuration object with a mapping-like API."""

    def __init__(self, values: Mapping[str, Any] | None = None, **kwargs: Any) -> None:
        self._values = dict(values or {})
        self._values.update(kwargs)

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, default)

    def require(self, key: str) -> Any:
        try:
            return self._values[key]
        except KeyError as exc:
            raise KeyError(f"Required configuration key is missing: {key}") from exc

    def set(self, key: str, value: Any) -> None:
        self._values[key] = value

    def update(self, values: Mapping[str, Any] | None = None, **kwargs: Any) -> None:
        if values:
            self._values.update(values)
        self._values.update(kwargs)

    def as_dict(self) -> dict[str, Any]:
        """Return a copy, preventing accidental mutation of internal config."""
        return self._values.copy()

    def __contains__(self, key: object) -> bool:
        return key in self._values

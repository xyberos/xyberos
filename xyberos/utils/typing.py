"""Shared type aliases that have no owning subsystem."""

from typing import TypeAlias

JSONValue: TypeAlias = str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]

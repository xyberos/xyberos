"""Tools backed by typed callables with JSON-schema signatures."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from typing import Any, get_args, get_origin

from ..contracts.tool import Tool
from ..exceptions.tool import ToolArgumentError


_TYPE_MAP = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
    list: {"type": "array"},
    dict: {"type": "object"},
}


def build_json_schema(
    func: Callable[..., Any],
    *,
    name: str | None = None,
    description: str = "",
) -> dict[str, Any]:
    """Build a JSON-schema description of ``func``'s signature.

    Annotated parameters become typed ``properties``; parameters without a
    default are listed in ``required``. Unannotated parameters get no ``type``.
    """
    signature = inspect.signature(func, eval_str=True)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for parameter in signature.parameters.values():
        if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
            continue
        properties[parameter.name] = _schema_for(parameter.annotation)
        if parameter.default is inspect.Parameter.empty:
            required.append(parameter.name)
    return {
        "name": name or func.__name__,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


def _schema_for(annotation: Any) -> dict[str, Any]:
    if annotation is inspect.Parameter.empty or annotation is Any:
        return {}
    origin = get_origin(annotation)
    if origin is not None:
        if origin is list:
            return {"type": "array"}
        if origin is dict:
            return {"type": "object"}
        non_none = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(non_none) == 1:
            return _schema_for(non_none[0])
        return {}
    return dict(_TYPE_MAP.get(annotation, {}))


def coerce_arguments(
    func: Callable[..., Any],
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and coerce ``arguments`` against ``func``'s signature.

    Raises :class:`~exceptions.tool.ToolArgumentError` for missing required
    parameters, unknown parameters, or values that cannot be coerced to the
    annotated type.
    """
    signature = inspect.signature(func, eval_str=True)
    coerced: dict[str, Any] = {}
    for name, parameter in signature.parameters.items():
        if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
            continue
        if name in arguments:
            coerced[name] = _coerce(arguments[name], parameter.annotation, name)
        elif parameter.default is inspect.Parameter.empty:
            raise ToolArgumentError(f"missing required argument: {name}")
    for name in arguments:
        if name not in signature.parameters:
            raise ToolArgumentError(f"unknown argument: {name}")
    return coerced


def _coerce(value: Any, annotation: Any, name: str) -> Any:
    if annotation in (inspect.Parameter.empty, Any):
        return value
    target = annotation
    origin = get_origin(annotation)
    if origin is not None:
        non_none = [arg for arg in get_args(annotation) if arg is not type(None)]
        target = non_none[0] if len(non_none) == 1 else origin

    if target is bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.lower()
            if lowered in ("true", "1", "yes"):
                return True
            if lowered in ("false", "0", "no"):
                return False
        raise ToolArgumentError(f"argument '{name}' must be a boolean")
    if target in (int, float):
        try:
            return target(value)
        except (TypeError, ValueError) as exc:
            label = "an integer" if target is int else "a number"
            raise ToolArgumentError(f"argument '{name}' must be {label}") from exc
    if target in (list, dict):
        if not isinstance(value, target):
            raise ToolArgumentError(f"argument '{name}' must be a {target.__name__}")
    return value


class FunctionTool(Tool):
    """A :class:`~contracts.tool.Tool` backed by a plain typed callable.

    The callable's signature defines the tool's JSON ``schema`` and is used to
    validate/coerce incoming arguments before invocation::

        def search(query: str, limit: int = 10) -> str: ...

        tool = FunctionTool("search", search, description="Search the catalog")
        tool.schema                 # JSON schema with typed properties
        tool.execute(ctx, query="books", limit="5")  # limit coerced to 5
    """

    def __init__(
        self,
        name: str,
        func: Callable[..., Any],
        *,
        description: str = "",
    ) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("tool name must be a non-empty string")
        if not callable(func):
            raise TypeError("func must be callable")
        self._name = name
        self._func = func
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def schema(self) -> dict[str, Any]:
        """A JSON-schema description of the tool's parameters."""
        return build_json_schema(self._func, name=self._name, description=self._description)

    def execute(self, context: object, **arguments: Any) -> Any:
        """Validate/coerce ``arguments`` and invoke the wrapped callable."""
        return self._func(**coerce_arguments(self._func, arguments))

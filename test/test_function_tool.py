"""Tests for typed function tools with JSON-schema signatures."""

import pytest

from xyberos.exceptions import ToolArgumentError
from xyberos.tools import FunctionTool, ToolRegistry, build_json_schema, coerce_arguments


def search(query: str, limit: int = 10) -> str:
    return f"search({query}, limit={limit})"


def test_build_json_schema_describes_signature():
    schema = build_json_schema(search, name="search", description="Search the catalog")

    assert schema["name"] == "search"
    assert schema["description"] == "Search the catalog"
    assert schema["parameters"]["type"] == "object"
    assert schema["parameters"]["properties"]["query"] == {"type": "string"}
    assert schema["parameters"]["properties"]["limit"] == {"type": "integer"}
    assert schema["parameters"]["required"] == ["query"]


def test_function_tool_coerces_arguments():
    tool = FunctionTool("search", search, description="Search the catalog")

    assert tool.name == "search"
    assert tool.description == "Search the catalog"
    assert tool.execute(object(), query="books", limit="5") == "search(books, limit=5)"
    assert tool.schema["parameters"]["required"] == ["query"]


def test_function_tool_rejects_bad_arguments():
    tool = FunctionTool("search", search)

    with pytest.raises(ToolArgumentError, match="missing required"):
        tool.execute(object())
    with pytest.raises(ToolArgumentError, match="unknown argument"):
        tool.execute(object(), query="x", bogus=1)
    with pytest.raises(ToolArgumentError, match="integer"):
        tool.execute(object(), query="x", limit="nope")


def test_optional_annotations_and_validation():
    def greet(name: str, nickname: str | None = None) -> str:
        return f"hi {name}"

    schema = build_json_schema(greet)
    assert schema["parameters"]["properties"]["nickname"] == {"type": "string"}
    assert schema["parameters"]["required"] == ["name"]

    tool = FunctionTool("greet", greet)
    assert tool.execute(object(), name="bob") == "hi bob"

    with pytest.raises(ValueError, match="non-empty"):
        FunctionTool("", greet)
    with pytest.raises(TypeError, match="callable"):
        FunctionTool("bad", object())


def test_function_tool_works_with_the_tool_registry():
    tool = FunctionTool("search", search)
    registry = ToolRegistry([tool])

    assert registry.execute("search", object(), query="x") == "search(x, limit=10)"
    assert registry.get("search").schema["parameters"]["type"] == "object"


def test_coerce_arguments_reports_missing_and_unknown():
    with pytest.raises(ToolArgumentError, match="missing required"):
        coerce_arguments(search, {})
    with pytest.raises(ToolArgumentError, match="unknown argument"):
        coerce_arguments(search, {"query": "x", "nope": 1})


def test_build_json_schema_handles_collections():
    def collect(items: list, lookup: dict) -> str:
        return ""

    schema = build_json_schema(collect)

    assert schema["parameters"]["properties"]["items"] == {"type": "array"}
    assert schema["parameters"]["properties"]["lookup"] == {"type": "object"}


def test_typed_tool_coerces_bools_floats_and_collections():
    def record(active: bool, score: float = 1.5, tags: list = []) -> str:
        return f"{active}:{score}:{len(tags)}"

    tool = FunctionTool("record", record)

    assert tool.execute(object(), active="yes") == "True:1.5:0"
    assert tool.execute(object(), active=True, score="2.5", tags=[1, 2]) == "True:2.5:2"

    with pytest.raises(ToolArgumentError, match="boolean"):
        tool.execute(object(), active="maybe")
    with pytest.raises(ToolArgumentError, match="a number"):
        tool.execute(object(), active=True, score="nope")

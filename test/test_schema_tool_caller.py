import json

from xyberos.llm import CallableLLM
from xyberos.runtime.context import CognitiveContext
from xyberos.tools import FunctionTool, SchemaToolCaller, ToolRunner


def search(query: str, limit: int = 10) -> str:
    return f"results for {query} limit {limit}"


def book(book_id: int) -> str:
    return f"book {book_id}"


class JsonLLM:
    """An LLM stub that returns a canned JSON payload."""

    def __init__(self, payload):
        self._payload = payload

    def generate(self, prompt):
        return json.dumps(self._payload)


def _runner():
    return ToolRunner([
        FunctionTool("search", search, description="Search the catalog"),
        FunctionTool("book", book, description="Fetch a book by id"),
    ])


def test_schema_caller_selects_tool_and_arguments():
    caller = SchemaToolCaller(
        JsonLLM({"tool": "search", "arguments": {"query": "books", "limit": 5}}),
        _runner(),
    )

    assert caller.select(CognitiveContext("find books")) == ("search", {"query": "books", "limit": 5})


def test_schema_caller_runs_with_coerced_arguments():
    caller = SchemaToolCaller(
        JsonLLM({"tool": "search", "arguments": {"query": "books", "limit": "5"}}),
        _runner(),
    )

    assert caller.run(CognitiveContext("find books")) == "results for books limit 5"


def test_schema_caller_returns_none_when_no_tool_applies():
    caller = SchemaToolCaller(JsonLLM({"tool": None, "arguments": {}}), _runner())
    assert caller.run(CognitiveContext("hello there")) is None


def test_schema_caller_returns_none_on_unparseable_output():
    caller = SchemaToolCaller(CallableLLM(lambda prompt: "not json at all"), _runner())
    assert caller.run(CognitiveContext("find books")) is None


def test_schema_caller_returns_none_for_unknown_tool():
    caller = SchemaToolCaller(JsonLLM({"tool": "nope", "arguments": {}}), _runner())
    assert caller.run(CognitiveContext("find books")) is None


def test_schema_caller_returns_none_when_no_tools_registered():
    caller = SchemaToolCaller(JsonLLM({"tool": "search", "arguments": {}}), ToolRunner())
    assert caller.run(CognitiveContext("find books")) is None


def test_schema_caller_returns_none_on_argument_error():
    caller = SchemaToolCaller(
        JsonLLM({"tool": "search", "arguments": {"query": "x", "limit": "abc"}}),
        _runner(),
    )
    assert caller.run(CognitiveContext("find")) is None


def test_schema_caller_merges_defaults():
    caller = SchemaToolCaller(JsonLLM({"tool": "search", "arguments": {"query": "books"}}), _runner())
    assert caller.run(CognitiveContext("find"), limit=3) == "results for books limit 3"


def test_schema_caller_instruction_includes_schemas():
    caller = SchemaToolCaller(JsonLLM({"tool": None}), _runner())
    # Building the instruction must not raise and must mention both tool names.
    instruction = caller._instruction("find books")  # type: ignore[attr-defined]
    assert "search" in instruction
    assert "book" in instruction
    assert '"query"' in instruction

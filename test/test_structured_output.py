"""Tests for structured LLM output parsing."""

import json

import pytest

from xyberos.exceptions import StructuredOutputError
from xyberos.llm import CallableLLM, StructuredLLM, extract_json, structured


def test_extract_json_parses_object_from_prose():
    text = 'Here is the result:\n{"answer": 42, "tags": ["a", "b"]}\nHope that helps.'
    assert extract_json(text) == {"answer": 42, "tags": ["a", "b"]}


def test_extract_json_parses_code_fenced_json():
    text = '```json\n{"name": "x", "nested": {"k": "v"}}\n```'
    assert extract_json(text) == {"name": "x", "nested": {"k": "v"}}


def test_extract_json_parses_arrays_and_escaped_strings():
    assert extract_json("[1, 2, 3] trailing") == [1, 2, 3]
    assert extract_json('{"msg": "say \\"hi\\""}') == {"msg": 'say "hi"'}


def test_extract_json_raises_on_invalid_input():
    with pytest.raises(json.JSONDecodeError):
        extract_json("no json here")


def test_structured_llm_parses_json_output():
    model = CallableLLM(lambda prompt: '{"city": "Paris"}')
    wrapper = StructuredLLM(model)

    assert wrapper.parse("Where?") == {"city": "Paris"}
    assert wrapper.generate("Where?") == '{"city": "Paris"}'


def test_structured_llm_raises_typed_error_on_bad_output():
    wrapper = StructuredLLM(CallableLLM(lambda prompt: "not json"))

    with pytest.raises(StructuredOutputError, match="could not parse"):
        wrapper.parse("Where?")


def test_structured_llm_supports_a_custom_parser():
    wrapper = StructuredLLM(CallableLLM(lambda prompt: "1,2,3"), parser=lambda t: t.split(","))

    assert wrapper.parse("x") == ["1", "2", "3"]

    with pytest.raises(TypeError, match="callable"):
        StructuredLLM(CallableLLM(lambda p: p), parser=object())


def test_structured_one_shot_helper():
    assert structured(CallableLLM(lambda prompt: '{"ok": true}'), "x") == {"ok": True}

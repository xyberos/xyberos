"""Shared utilities used across the package."""

from xyberos.utils import JSONValue


def test_json_value_type_alias_supports_recursive_json_shapes():
    sample: JSONValue = {"items": [1, 2.5, "three", None, True]}

    assert sample["items"][2] == "three"

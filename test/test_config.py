import pytest

from xyberos.kernel.config import Config


def test_config_reads_mutates_and_copies_values():
    config = Config({"host": "localhost"}, port=8000)

    assert config.get("host") == "localhost"
    assert config.get("missing", "fallback") == "fallback"
    assert "port" in config

    config.set("debug", True)
    config.update({"host": "example.test"}, port=9000)
    values = config.as_dict()
    values["host"] = "mutated-copy"

    assert config.get("host") == "example.test"
    assert config.get("port") == 9000
    assert config.get("debug") is True


def test_config_require_returns_value_or_identifies_missing_key():
    config = Config({"token": "secret"})

    assert config.require("token") == "secret"
    with pytest.raises(KeyError, match="Required configuration key is missing: region"):
        config.require("region")

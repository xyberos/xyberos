"""Tests for the declarative plugin loader."""

from xyberos import create_app
from xyberos.contracts import Tool

from xyberos_plugin_sdk.declarative import DeclarativePlugin, load_declarative

_PYPROJECT = """
[tool.xyberos.plugins.demo]
type = "tool"
auth = "token"
capabilities = ["repositories", "issues"]
"""


def _write_pyproject(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text(_PYPROJECT, encoding="utf-8")
    return path


class Demo(Tool):
    @property
    def name(self):
        return "demo"

    def execute(self, context, **arguments):
        return 42


def test_load_declarative_parses_tables(tmp_path):
    plugins = load_declarative(_write_pyproject(tmp_path))
    assert len(plugins) == 1
    plugin = plugins[0]
    assert plugin.name == "demo"
    assert plugin.plugin_type == "tool"
    assert plugin.config["capabilities"] == ["repositories", "issues"]


def test_declarative_plugin_registers_and_unregisters():
    plugin = DeclarativePlugin("demo", {"type": "tool"}).with_tool(Demo())
    app = create_app()
    app.load_plugin(plugin)
    assert "demo" in app.tools.names
    assert app.tools.execute("demo", None) == 42
    assert app.resolve("plugin.demo") is plugin
    app.unload_plugin("demo")
    assert "demo" not in app.tools.names

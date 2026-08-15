"""Tests for the plugin scaffold generator."""

import ast
import sys

from xyberos import create_app
from xyberos_cli.create import generate_plugin
from xyberos_cli.main import main

ANSWERS = {
    "name": "demo",
    "type": "tool",
    "description": "A demo tool",
    "integrate_with": "Demo API",
    "auth": "none",
    "async_support": False,
    "streaming": False,
}


def test_generate_plugin_files(tmp_path):
    target = tmp_path / "demo"
    files = generate_plugin(target, ANSWERS)
    assert len(files) == 8
    assert (target / "pyproject.toml").is_file()
    assert (target / "README.md").is_file()
    for module in ("service.py", "plugin.py", "config.py", "__init__.py"):
        ast.parse((target / "demo" / module).read_text())
    pyproject = (target / "pyproject.toml").read_text()
    assert '[project.entry-points."xyberos.plugins"]' in pyproject
    assert 'demo = "demo.plugin:plugin"' in pyproject


def test_generated_plugin_is_loadable(tmp_path):
    target = tmp_path / "demo"
    generate_plugin(target, ANSWERS)
    sys.path.insert(0, str(target))
    try:
        from demo.plugin import plugin  # type: ignore[import-not-found]

        app = create_app()
        assert app.load_plugin(plugin) is plugin
        assert plugin.name == "demo"
        assert "demo" in app.tools.names
        app.unload_plugin("demo")
    finally:
        sys.path.remove(str(target))
        for name in list(sys.modules):
            if name == "demo" or name.startswith("demo."):
                del sys.modules[name]


def test_cli_create_non_interactive(tmp_path):
    code = main(
        [
            "plugin",
            "create",
            "--name",
            "demo",
            "--type",
            "tool",
            "--description",
            "d",
            "--dir",
            str(tmp_path),
            "--non-interactive",
        ]
    )
    assert code == 0
    assert (tmp_path / "demo" / "demo" / "plugin.py").is_file()


def test_cli_create_non_interactive_requires_name(tmp_path):
    code = main(
        [
            "plugin",
            "create",
            "--type",
            "tool",
            "--description",
            "d",
            "--dir",
            str(tmp_path),
            "--non-interactive",
        ]
    )
    assert code == 1

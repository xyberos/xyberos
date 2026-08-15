"""Shared fixtures for validator tests: build a valid plugin package in tmp_path."""

import textwrap

import pytest


@pytest.fixture
def valid_plugin(tmp_path):
    """A minimal, fully working Tool plugin package."""
    root = tmp_path / "proj"
    (root / "demo").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)

    (root / "pyproject.toml").write_text(
        textwrap.dedent(
            """
            [project]
            name = "demo"
            version = "0.1.0"
            dependencies = ["xyberos>=1.0"]

            [project.entry-points."xyberos.plugins"]
            demo = "demo.plugin:plugin"

            [tool.setuptools]
            packages = ["demo"]
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text("# demo\n", encoding="utf-8")
    (root / "demo" / "__init__.py").write_text("from .plugin import plugin\n", encoding="utf-8")
    (root / "demo" / "plugin.py").write_text(
        textwrap.dedent(
            """
            from xyberos.contracts import Plugin, Tool


            class Demo(Tool):
                @property
                def name(self):
                    return "demo"

                def execute(self, context, **arguments):
                    return "ok"


            class DemoPlugin(Plugin):
                @property
                def name(self):
                    return "demo"

                def register(self, kernel):
                    kernel.resolve("tools").register(Demo())

                def unregister(self, kernel):
                    kernel.resolve("tools")._tools.pop("demo", None)


            plugin = DemoPlugin()
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_plugin.py").write_text(
        "def test_demo():\n    assert True\n", encoding="utf-8"
    )
    return root

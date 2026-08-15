"""Tests for the live-kernel (subprocess) compatibility check."""

import textwrap

from xyberos_plugin_validator import validate_plugin
from xyberos_plugin_validator.live import live_validate


def test_live_validate_ok(valid_plugin):
    ok, detail = live_validate(valid_plugin, "demo.plugin", "plugin")
    assert ok, detail
    assert "loaded + unloaded" in detail


def test_live_validate_reports_register_failure(tmp_path):
    root = tmp_path / "proj"
    (root / "boom").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        textwrap.dedent(
            """
            [project]
            name = "boom"

            [project.entry-points."xyberos.plugins"]
            boom = "boom.plugin:plugin"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text("# boom\n", encoding="utf-8")
    (root / "boom" / "__init__.py").write_text("", encoding="utf-8")
    (root / "boom" / "plugin.py").write_text(
        textwrap.dedent(
            """
            from xyberos.contracts import Plugin


            class Boom(Plugin):
                @property
                def name(self):
                    return "boom"

                def register(self, kernel):
                    raise RuntimeError("boom in register")

                def unregister(self, kernel):
                    pass


            plugin = Boom()
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    report = validate_plugin(root, run_live=True)
    assert not report.passed
    compatibility = [check for check in report.checks if check.name == "compatibility"]
    assert compatibility and not compatibility[0].passed
    assert "RuntimeError" in compatibility[0].detail

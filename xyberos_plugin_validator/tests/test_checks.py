"""Tests for the static validation checks."""

from xyberos_plugin_validator import validate_plugin
from xyberos_plugin_validator.checks import discover_entry_points


def test_valid_plugin_passes(valid_plugin):
    report = validate_plugin(valid_plugin)
    assert report.passed, report.render()
    assert "Result: PASS" in report.render()


def test_discover_entry_points(valid_plugin):
    entry_points = discover_entry_points(valid_plugin / "pyproject.toml")
    assert entry_points == {"demo": "demo.plugin:plugin"}


def test_missing_pyproject_fails(tmp_path):
    report = validate_plugin(tmp_path, run_live=False)
    assert not report.passed
    assert any(check.name == "structure" and not check.passed for check in report.checks)


def test_missing_entry_point_fails(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    report = validate_plugin(tmp_path, run_live=False)
    assert not report.passed
    assert any(check.name == "configuration" and not check.passed for check in report.checks)


def test_missing_readme_warns(valid_plugin):
    (valid_plugin / "README.md").unlink()
    report = validate_plugin(valid_plugin, run_live=False)
    assert not report.passed
    assert any(check.name == "documentation" and not check.passed for check in report.checks)


def test_missing_tests_fails(valid_plugin):
    for path in list(valid_plugin.glob("test_*.py")) + list(
        (valid_plugin / "tests").glob("test_*.py")
    ):
        path.unlink()
    report = validate_plugin(valid_plugin, run_live=False)
    assert any(check.name == "testing" and not check.passed for check in report.checks)

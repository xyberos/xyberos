"""Tests for the CLI parser and dispatch."""

from xyberos_cli.main import build_parser, main


def test_parser_builds_and_parses():
    parser = build_parser()
    args = parser.parse_args(["plugin", "validate", "."])
    assert args.command == "plugin"
    assert args.plugin_command == "validate"
    assert args.path == "."


def test_cli_validate_missing_dir_fails(tmp_path, capsys):
    code = main(["plugin", "validate", str(tmp_path / "nope")])
    assert code == 1
    output = capsys.readouterr().out
    assert "Result: FAIL" in output

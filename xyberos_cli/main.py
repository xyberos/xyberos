"""``xyberos`` command-line entry point — plugin create / validate / repair."""

from __future__ import annotations

import argparse
import sys

from xyberos_plugin_sdk.introspect import plugin_types

from . import create, repair, validate

__all__ = ["build_parser", "main"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xyberos",
        description="Xyberos plugin developer toolkit (SDK + validator + generator).",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    plugin = sub.add_parser("plugin", help="develop and validate Xyberos plugins")
    psub = plugin.add_subparsers(dest="plugin_command", required=True)

    create_p = psub.add_parser("create", help="scaffold a new Xyberos plugin")
    create_p.add_argument("--name", help="plugin name (e.g. github)")
    create_p.add_argument("--type", choices=plugin_types(), help="plugin type")
    create_p.add_argument("--description", help="one-line description")
    create_p.add_argument("--integrate-with", help="what the plugin integrates with")
    create_p.add_argument(
        "--auth", choices=["none", "api-key", "oauth", "token", "custom"], default="none"
    )
    create_p.add_argument("--async", dest="async_support", action="store_true", help="generate async-friendly scaffolding")
    create_p.add_argument("--streaming", action="store_true", help="generate streaming-friendly scaffolding")
    create_p.add_argument("--dir", default=".", help="output directory (default: current directory)")
    create_p.add_argument(
        "--non-interactive",
        action="store_true",
        help="fail instead of prompting when --name/--type/--description are missing",
    )
    create_p.set_defaults(func=create.run_create)

    validate_p = psub.add_parser("validate", help="validate a plugin package")
    validate_p.add_argument("path", nargs="?", default=".", help="plugin package directory")
    validate_p.add_argument("--fix", action="store_true", help="repair missing contract stubs before validating")
    validate_p.add_argument("--run-tests", action="store_true", help="also run the plugin's tests")
    validate_p.set_defaults(func=validate.run_validate)

    repair_p = psub.add_parser("repair", help="insert missing contract stubs via AST")
    repair_p.add_argument("path", nargs="?", default=".", help="plugin package directory")
    repair_p.add_argument("--check", action="store_true", help="only report what would change")
    repair_p.set_defaults(func=repair.run_repair)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        if exc.code:
            print(exc.code, file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

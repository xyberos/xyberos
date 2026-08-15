"""``xyberos plugin validate`` — run the validator and print the report."""

from __future__ import annotations

import argparse
from pathlib import Path

from xyberos_plugin_validator import validate_plugin

from . import repair

__all__ = ["run_validate"]


def run_validate(args: argparse.Namespace) -> int:
    if args.fix:
        repair.repair_package(Path(args.path), check=False)
    report = validate_plugin(args.path, run_tests=args.run_tests)
    print(report.render())
    if not report.passed:
        print()
        print("suggestion: run 'xyberos plugin repair <path>' to insert missing contract stubs")
        return 1
    return 0

"""AST-based repair for Xyberos plugins (``plugin-contribution.md`` approach #6).

``xyberos plugin repair`` finds classes in the plugin's source that extend a
known Xyberos contract (e.g. ``Tool``, ``Memory``, ``VectorStore``) and are
missing abstract members, then textually inserts implementable stubs — without
reformatting the rest of the file. ``--check`` only reports what would change.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

from xyberos_plugin_sdk.introspect import CONTRACTS, abstract_members, render_stub

__all__ = ["repair_file", "repair_package", "repair_source", "run_repair"]

_CONTRACTS_BY_NAME = {contract.__name__: contract for contract in CONTRACTS.values()}


def _base_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _base_name(node.value)
    return ""


def _imported_contract_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "xyberos.contracts":
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def _defined_members(node: ast.ClassDef) -> set[str]:
    return {
        member.name
        for member in node.body
        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def repair_source(source: str) -> tuple[str, list[str]]:
    """Insert missing contract stubs. Returns ``(updated_source, changes)``."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source, []
    contract_names = _imported_contract_names(tree)
    if not contract_names:
        return source, []

    insertions: dict[int, list[str]] = {}
    changes: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            contract = _CONTRACTS_BY_NAME.get(_base_name(base))
            if contract is None:
                continue
            existing = _defined_members(node)
            stubs: list[str] = []
            for member in abstract_members(contract):
                if member in existing:
                    continue
                stubs.append(render_stub(contract, member, indent=node.col_offset + 4))
                existing.add(member)
            if stubs:
                # Insert just after the class body's last line (still inside the class).
                end_line = node.end_lineno or node.lineno
                insertions.setdefault(end_line - 1, []).extend(stubs)
                changes.append(
                    f"{node.name} (+{len(stubs)} member{'s' if len(stubs) != 1 else ''})"
                )

    if not changes:
        return source, []

    lines = source.splitlines(keepends=True)
    for line_index in sorted(insertions, reverse=True):
        lines.insert(line_index, "".join(insertions[line_index]))
    return "".join(lines), changes


def repair_file(path: str | Path, *, check: bool = False) -> tuple[bool, list[str]]:
    """Repair one ``.py`` file in place. Returns ``(changed, changes)``."""
    path = Path(path)
    source = path.read_text(encoding="utf-8")
    updated, changes = repair_source(source)
    if changes and not check:
        path.write_text(updated, encoding="utf-8")
    return bool(changes), changes


def repair_package(root: str | Path, *, check: bool = False) -> list[str]:
    """Repair every ``.py`` file under a plugin package. Returns all changes."""
    root = Path(root)
    all_changes: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if "site-packages" in path.parts or path.name.startswith("."):
            continue
        changed, changes = repair_file(path, check=check)
        if changed:
            all_changes.append(f"{path.relative_to(root)}: {', '.join(changes)}")
    return all_changes


def run_repair(args: argparse.Namespace) -> int:
    changes = repair_package(args.path, check=args.check)
    verb = "Would repair" if args.check else "Repaired"
    if not changes:
        print("No missing contract stubs found — nothing to do.")
        return 0
    print(f"{verb} {len(changes)} file(s):")
    for change in changes:
        print(f"  - {change}")
    if args.check:
        print("Re-run without --check to apply these changes.")
    return 0

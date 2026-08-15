"""Static validation checks for a Xyberos plugin package.

Checks reported (matching ``plugin-contribution.md``): ``structure``, ``contract``,
``configuration``, ``testing``, ``documentation``, and (via :mod:`.live`)
``compatibility`` (the live-kernel register/unregister check).
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any, cast

from xyberos_plugin_sdk.introspect import (
    CONTRACTS,
    is_concrete,
    missing_abstracts,
    signature_compatible,
)

from .report import Report

__all__ = ["discover_entry_points", "validate_plugin", "validate_plugin_checks"]

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]

_CONTRACT_MEMBERS: dict[str, tuple[str, ...]] = {
    "tool": ("name", "execute"),
    "llm": ("generate",),
    "memory": ("retrieve", "store"),
    "knowledge": ("query",),
    "vector": ("upsert", "query", "delete", "clear"),
    "workflow": ("run",),
    "planner": ("plan",),
    "agent": ("name", "run"),
    "service": ("start", "stop"),
    "other": (),
}


def _read_toml(path: str | Path) -> dict[str, Any]:
    with open(path, "rb") as handle:
        return tomllib.load(handle)


def _as_dict(value: Any) -> dict[str, Any]:
    """Return ``value`` as a ``dict[str, Any]`` when it is one, else ``{}``."""
    if isinstance(value, dict):
        return cast(dict[str, Any], value)
    return {}


def discover_entry_points(pyproject_path: str | Path) -> dict[str, str]:
    """Return ``{name: 'module:attr'}`` from ``[project.entry-points."xyberos.plugins"]``."""
    if not Path(pyproject_path).is_file():
        return {}
    data = _read_toml(pyproject_path)
    project = _as_dict(data.get("project"))
    entry_points = _as_dict(project.get("entry-points"))
    group = _as_dict(entry_points.get("xyberos.plugins"))
    return {str(name): str(value) for name, value in group.items() if isinstance(value, str)}


def _entry_module(entry_value: str) -> tuple[str, str]:
    """Split ``'pkg.plugin:plugin'`` into ``('pkg.plugin', 'plugin')``."""
    module, _, attr = entry_value.partition(":")
    return module, attr or "plugin"


def _top_level_package(module: str) -> str:
    return module.split(".")[0]


def _import_plugin(root: Path, module: str, attr: str) -> tuple[Any | None, str | None]:
    """Import the plugin object from ``root``. Returns ``(plugin, error)``."""
    sys.path.insert(0, str(root))
    try:
        mod = importlib.import_module(module)
    except Exception as exc:  # noqa: BLE001 - surfaced to the report
        return None, f"import failed: {type(exc).__name__}: {exc}"
    finally:
        try:
            sys.path.remove(str(root))
        except ValueError:
            pass
    candidate = getattr(mod, attr, None)
    if candidate is None:
        return None, f"module {module!r} exposes no {attr!r} attribute"
    if isinstance(candidate, type):
        try:
            candidate = candidate()
        except Exception as exc:  # noqa: BLE001
            return None, f"instantiating {attr!r} failed: {type(exc).__name__}: {exc}"
    return candidate, None


def _contribution_issues(plugin: Any, plugin_type: str) -> list[str]:
    """Verify the contributed service(s) implement the underlying contract."""
    if plugin_type == "other" or plugin_type not in CONTRACTS:
        return []
    contribute = _contribute_method(plugin, plugin_type)
    if contribute is None:
        return [f"plugin does not expose a '{_method_name(plugin_type)}' contribution"]
    issues: list[str] = []
    try:
        value = contribute()
    except Exception as exc:  # noqa: BLE001
        return [f"{_method_name(plugin_type)}() raised {type(exc).__name__}: {exc}"]

    contract = CONTRACTS[plugin_type]
    services: list[Any] = value if plugin_type == "tool" else [value]
    for index, service in enumerate(services):
        label = f"tool #{index}" if plugin_type == "tool" else "service"
        missing = [m for m in _CONTRACT_MEMBERS[plugin_type] if not hasattr(service, m)]
        if missing:
            issues.append(f"{label} is missing {', '.join(missing)}")
            continue
        for member in _CONTRACT_MEMBERS[plugin_type]:
            if member == "name":
                name_value = getattr(service, "name", None)
                if not isinstance(name_value, str) or not name_value.strip():
                    issues.append(f"{label}.name must be a non-empty string")
                continue
            impl_method = getattr(service, member, None)
            if not callable(impl_method):
                issues.append(f"{label}.{member} is not callable")
                continue
            if not signature_compatible(cast(type[Any], type(service)), contract, member):
                issues.append(
                    f"{label}.{member} signature is not compatible with "
                    f"the {contract.__name__} contract"
                )
    return issues


def _contribute_method(plugin: Any, plugin_type: str) -> Any | None:
    method_name = _method_name(plugin_type)
    method = getattr(plugin, method_name, None)
    return method if callable(method) else None


def _method_name(plugin_type: str) -> str:
    return {
        "tool": "tools",
        "llm": "llm",
        "memory": "memory",
        "knowledge": "knowledge",
        "vector": "vector_store",
        "workflow": "workflow",
        "planner": "planner",
        "agent": "agent",
        "service": "service",
    }.get(plugin_type, "plugin")


def _plugin_type_of(plugin: Any) -> str:
    return getattr(plugin, "plugin_type", None) or "other"


def validate_plugin_checks(
    root: str | Path,
    *,
    run_live: bool = True,
    run_tests: bool = False,
) -> Report:
    """Run the static (+ optional live) checks against a plugin package."""
    from . import live  # local import keeps subprocess module import-light

    root = Path(root)
    report = Report()
    pyproject = root / "pyproject.toml"

    # --- structure ---------------------------------------------------------
    if not pyproject.is_file():
        report.fail("structure", f"missing {pyproject.name}")
        return report
    entry_points = discover_entry_points(pyproject)
    if not entry_points:
        report.fail("configuration", "no [project.entry-points.\"xyberos.plugins\"] declared")
        return report
    entry_name, entry_value = next(iter(entry_points.items()))
    module, attr = _entry_module(entry_value)
    pkg_dir = root / _top_level_package(module)
    if not pkg_dir.is_dir():
        report.fail(
            "structure",
            f"expected package directory {pkg_dir.name}/ for entry point {entry_name!r}",
        )
        return report
    report.pass_("structure", f"found {pyproject.name} and package {pkg_dir.name}/")

    # --- configuration -----------------------------------------------------
    report.pass_(
        "configuration",
        f"entry point {entry_name!r} -> {entry_value!r} (group xyberos.plugins)",
    )

    # --- documentation -----------------------------------------------------
    readme = root / "README.md"
    report.pass_("documentation", "README.md present") if readme.is_file() else report.fail(
        "documentation", "README.md missing"
    )

    # --- testing -----------------------------------------------------------
    test_files = sorted(root.glob("test_*.py"))
    if (root / "tests").is_dir():
        test_files += sorted((root / "tests").glob("test_*.py"))
    if test_files:
        if run_tests:
            passed, detail = _run_pytest(root)
            report.pass_("testing", detail) if passed else report.fail("testing", detail)
        else:
            report.pass_(
                "testing", f"{len(test_files)} test file(s) present (run with --run-tests)"
            )
    else:
        report.fail("testing", "no test_*.py files found")

    # --- contract (static import + conformance) ----------------------------
    plugin, error = _import_plugin(root, module, attr)
    if error is not None:
        report.fail("contract", error)
    else:
        issues = _contract_issues(plugin)
        if issues:
            report.fail("contract", "; ".join(issues))
        else:
            report.pass_(
                "contract",
                f"{type(plugin).__name__} is a valid {_plugin_type_of(plugin)} plugin",
            )

    # --- compatibility (live kernel, isolated subprocess) ------------------
    if run_live:
        ok, detail = live.live_validate(root, module, attr)
        report.pass_("compatibility", detail) if ok else report.fail("compatibility", detail)

    return report


def _contract_issues(plugin: Any) -> list[str]:
    """Static conformance of the plugin object itself."""
    issues: list[str] = []
    if not hasattr(plugin, "name") or not isinstance(plugin.name, str) or not plugin.name.strip():
        issues.append("plugin.name must be a non-empty string")
    for required in ("register", "unregister"):
        if not callable(getattr(plugin, required, None)):
            issues.append(f"plugin.{required} must be callable")
    cls = cast(type[Any], type(plugin))
    if not is_concrete(cls):
        issues.append(f"{cls.__name__} is abstract; missing: {', '.join(missing_abstracts(cls))}")
    plugin_type = _plugin_type_of(plugin)
    issues.extend(_contribution_issues(plugin, plugin_type))
    return issues


def _run_pytest(root: Path) -> tuple[bool, str]:
    """Best-effort run of the plugin's tests. Returns (passed, detail)."""
    import subprocess
    import sys

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(root / "tests"), "-q", "-o", "addopts="],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"could not run tests: {type(exc).__name__}: {exc}"
    if proc.returncode == 0:
        return True, "pytest passed"
    tail = "\n".join((proc.stdout or "").strip().splitlines()[-5:])
    return False, f"pytest failed ({proc.returncode}): {tail}"


def validate_plugin(root: str | Path, *, run_live: bool = True, run_tests: bool = False) -> Report:
    """Validate a plugin package directory. See :func:`validate_plugin_checks`."""
    return validate_plugin_checks(root, run_live=run_live, run_tests=run_tests)

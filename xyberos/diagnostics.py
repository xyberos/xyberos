"""Developer-facing diagnostics for Xyberos."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from importlib import metadata
from typing import Any

from .xyberos import create_app


@dataclass(frozen=True)
class DiagnosticReport:
    """Snapshot of the local Xyberos runtime and package state."""

    package_version: str
    python_version: str
    app_created: bool
    kernel_started: bool
    kernel_services: tuple[str, ...]
    plugin_names: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the report."""
        return asdict(self)


def doctor() -> DiagnosticReport:
    """Build a lightweight environment report for quick developer checks."""
    app = create_app()
    try:
        package_version = metadata.version("xyberos")
    except metadata.PackageNotFoundError:
        from .version import __version__

        package_version = __version__

    import sys

    return DiagnosticReport(
        package_version=package_version,
        python_version=sys.version.split()[0],
        app_created=True,
        kernel_started=app.started,
        kernel_services=app.registry.names,
        plugin_names=app.plugins.names,
    )

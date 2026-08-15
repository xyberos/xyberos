"""Live-kernel validation in an isolated subprocess (``EXTRA.md`` approach #3).

``xyberos plugin validate`` builds a real ``create_app()``, ``load_plugin()``s
the target, and runs register/unregister — inside a ``subprocess`` harness so it
never depends on or mutates the caller's core/process state. This catches
failures static checks miss, e.g. "the signature is right but ``register()``
actually raises".
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

__all__ = ["live_validate"]


def live_validate(root: str | Path, module: str, attr: str) -> tuple[bool, str]:
    """Run the subprocess harness. Returns ``(ok, detail)``."""
    root = Path(root)
    command = [
        sys.executable,
        "-m",
        "xyberos_plugin_validator._runner",
        str(root),
        module,
        attr,
    ]
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return False, "live-kernel check timed out after 120s"
    payload = _last_json_line(proc.stdout)
    if payload is None:
        return False, f"live-kernel check crashed: {_tail(proc.stderr)}"
    if payload.get("ok"):
        name = payload.get("name", "?")
        return True, f"loaded + unloaded '{name}' against a real create_app()"
    return False, payload.get("error", "unknown live-kernel failure")


def _last_json_line(text: str) -> dict | None:
    for line in reversed((text or "").strip().splitlines()):
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    return None


def _tail(text: str, lines: int = 6) -> str:
    return "\n".join((text or "").strip().splitlines()[-lines:])

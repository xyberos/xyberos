"""Subprocess harness for live-kernel plugin validation.

Run via ``python -m xyberos_plugin_validator._runner <root> <module> <attr>``.

It is intentionally isolated: it adds only ``<root>`` to ``sys.path``, builds a
fresh ``create_app()``, loads the plugin, checks it registers and unregisters,
and prints a single JSON line to stdout.
"""

from __future__ import annotations

import importlib
import json
import sys


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root, module, attr = argv[0], argv[1], argv[2]
    sys.path.insert(0, root)
    try:
        from xyberos import create_app

        mod = importlib.import_module(module)
        candidate = getattr(mod, attr) if attr else getattr(mod, "plugin", None)
        if candidate is None:
            raise RuntimeError(f"module {module!r} exposes no {attr or 'plugin'!r}")
        if isinstance(candidate, type):
            candidate = candidate()
        if not hasattr(candidate, "name"):
            raise RuntimeError("plugin exposes no 'name'")
        app = create_app()
        app.load_plugin(candidate)
        name = candidate.name
        app.unload_plugin(name)
        print(json.dumps({"ok": True, "name": name}))
        return 0
    except BaseException as exc:  # noqa: BLE001 - report anything to the parent
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

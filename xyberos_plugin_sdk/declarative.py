"""Declarative plugins via ``[tool.xyberos.plugins.*]`` (``EXTRA.md`` approach #5).

A package can declare plugins in its ``pyproject.toml``::

    [tool.xyberos.plugins.github]
    type = "tool"
    auth = "token"
    capabilities = ["repositories", "issues", "pull_requests"]

The SDK reads that table and turns each entry into a
:class:`DeclarativePlugin` that registers itself (and any attached tools /
services) through the public kernel API. The author binds real implementations
with :meth:`DeclarativePlugin.with_tool` / :meth:`DeclarativePlugin.with_service`
before loading.

The app's existing ``xyberos.plugins`` entry-point group is reused as-is: a
package points its entry point at a tiny module that builds the declarative
plugin(s) and exposes them as ``plugin``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from xyberos.contracts import Plugin, Tool

__all__ = ["DeclarativePlugin", "load_declarative", "register_declarative"]

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]


def _read_toml(path: str | Path) -> dict[str, Any]:
    with open(path, "rb") as handle:
        return tomllib.load(handle)


class DeclarativePlugin(Plugin):
    """A plugin declared in ``[tool.xyberos.plugins.<name>]``.

    ``config`` carries the table's values (``type``, ``auth``, ``capabilities``,
    ...). The author attaches concrete implementations with ``with_tool`` /
    ``with_service``; those are registered on ``register()``.
    """

    def __init__(self, name: str, config: dict[str, Any] | None = None) -> None:
        self._name = str(name)
        self.config: dict[str, Any] = dict(config or {})
        self._tools: dict[str, Tool] = {}
        self._services: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def plugin_type(self) -> str | None:
        return self.config.get("type")

    def with_tool(self, tool: Tool) -> "DeclarativePlugin":
        """Attach a tool implementation; registered on ``register()``."""
        self._tools[tool.name] = tool
        return self

    def with_service(self, name: str, service: Any) -> "DeclarativePlugin":
        """Attach a named service; registered as ``<plugin>.<name>``."""
        self._services[name] = service
        return self

    def register(self, kernel: Any) -> None:
        kernel.register(f"plugin.{self._name}", self)
        for tool in self._tools.values():
            kernel.resolve("tools").register(tool)
        for name, service in self._services.items():
            kernel.register(f"{self._name}.{name}", service, replace=True)

    def unregister(self, kernel: Any) -> None:
        registry = kernel.registry
        if hasattr(registry, "unregister"):
            registry.unregister(f"plugin.{self._name}")
        for tool in self._tools.values():
            unregister = getattr(kernel.resolve("tools"), "unregister", None)
            if callable(unregister):
                unregister(tool.name)
            else:
                store = getattr(kernel.resolve("tools"), "_tools", None)
                if isinstance(store, dict):
                    store.pop(tool.name, None)


def load_declarative(pyproject_path: str | Path) -> list[DeclarativePlugin]:
    """Parse ``[tool.xyberos.plugins.*]`` from ``pyproject.toml`` into plugins."""
    data = _read_toml(pyproject_path)
    table = data.get("tool", {})
    if not isinstance(table, dict):
        return []
    xyberos = table.get("xyberos", {})
    plugins = xyberos.get("plugins", {}) if isinstance(xyberos, dict) else {}
    result: list[DeclarativePlugin] = []
    for name, cfg in plugins.items():
        if isinstance(cfg, dict):
            result.append(DeclarativePlugin(name, cfg))
    return result


def register_declarative(kernel: Any, pyproject_path: str | Path) -> list[DeclarativePlugin]:
    """Load declarative plugins from ``pyproject.toml`` and register them."""
    loaded = [plugin for plugin in load_declarative(pyproject_path) if _looks_unloaded(kernel, plugin)]
    for plugin in loaded:
        kernel.plugins.load(plugin) if hasattr(kernel, "plugins") else plugin.register(kernel)
    return loaded


def _looks_unloaded(kernel: Any, plugin: Plugin) -> bool:
    loader = getattr(kernel, "plugins", None)
    if loader is None or not hasattr(loader, "names"):
        return True
    return plugin.name not in loader.names

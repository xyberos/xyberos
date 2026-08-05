"""Plugin discovery and lifecycle management."""

from __future__ import annotations

import importlib.metadata
import inspect
import pkgutil
from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING

from ..contracts.plugin import Plugin
from ..events.names import PLUGIN_LOADED, PLUGIN_UNLOADED
from ..exceptions.plugin import PluginAlreadyLoadedError, PluginLoadError, PluginNotFoundError

if TYPE_CHECKING:
    from ..kernel.kernel import Kernel

# Entry-point group auto-discovered by ``PluginLoader.load_entry_points``.
# Third-party packages opt in by declaring, e.g.::
#
#     [project.entry-points."xyberos.plugins"]
#     my_chat = "my_chat.plugins:plugin"
DEFAULT_ENTRY_POINT_GROUP = "xyberos.plugins"


class PluginLoader:
    """Loads plugins and gives them controlled access to the platform kernel."""

    def __init__(self, kernel: "Kernel") -> None:
        self._kernel = kernel
        self._plugins: dict[str, Plugin] = {}

    @property
    def names(self) -> tuple[str, ...]:
        """Names of all loaded plugins, in load order."""
        return tuple(self._plugins)

    def load(self, plugin: Plugin) -> Plugin:
        """Register and retain one plugin instance."""
        if not isinstance(plugin, Plugin):
            raise TypeError("plugin must implement the Plugin contract")
        if not isinstance(plugin.name, str) or not plugin.name.strip():
            raise PluginLoadError("plugin name must be a non-empty string")
        if plugin.name in self._plugins:
            raise PluginAlreadyLoadedError(f"Plugin is already loaded: {plugin.name}")

        plugin.register(self._kernel)
        self._plugins[plugin.name] = plugin
        self._kernel.events.emit(PLUGIN_LOADED, context=plugin)
        return plugin

    def load_from_module(self, module_name: str, attribute: str = "plugin") -> Plugin:
        """Import and load a plugin instance or zero-argument plugin class."""
        module = import_module(module_name)
        try:
            candidate = getattr(module, attribute)
        except AttributeError as exc:
            raise PluginLoadError(f"Module '{module_name}' has no '{attribute}' plugin") from exc
        if isinstance(candidate, type):
            candidate = candidate()
        return self.load(candidate)

    def load_entry_points(
        self, group: str = DEFAULT_ENTRY_POINT_GROUP, *, skip_existing: bool = True
    ) -> tuple[Plugin, ...]:
        """Auto-discover and load every plugin declared under ``group``.

        Uses ``importlib.metadata.entry_points`` — the same mechanism pytest,
        flake8, and uvicorn use — so installing a package that declares an
        ``xyberos.plugins`` entry point is enough to register its plugin; no
        manual ``load()`` call or app wiring is needed.

        An entry point value is ``module:attribute`` (or a bare module name, in
        which case the module's ``plugin`` export is used). Duplicate names are
        skipped when ``skip_existing`` is true so repeated discovery is
        idempotent.
        """
        loaded: list[Plugin] = []
        for entry_point in importlib.metadata.entry_points(group=group):
            try:
                candidate = entry_point.load()
            except Exception as exc:  # noqa: BLE001 - wrap import/runtime failures
                raise PluginLoadError(
                    f"Entry point '{entry_point.name}' in group '{group}' failed to load: {exc}"
                ) from exc
            if isinstance(candidate, ModuleType):
                candidate = getattr(candidate, "plugin", None)
                if candidate is None:
                    message = f"Entry point '{entry_point.name}' exports no 'plugin' value"
                    raise PluginLoadError(message)
            if isinstance(candidate, type):
                candidate = candidate()
            plugin = self._load_or_skip(candidate, skip_existing=skip_existing)
            if plugin is not None:
                loaded.append(plugin)
        return tuple(loaded)

    def load_from_package(
        self, package: str, *, skip_existing: bool = True
    ) -> tuple[Plugin, ...]:
        """Convention-based auto-discovery: scan a package for Plugin classes.

        Walks ``package`` and every submodule, loading each concrete ``Plugin``
        subclass found. Adding a new module to the package is enough to wire it
        up — no entry-point declaration or manual load. Example::

            # app/plugins/chat.py
            class ChatPersistencePlugin(Plugin): ...

            app.load_plugins_from("app.plugins")
        """
        package_module = import_module(package)
        if not hasattr(package_module, "__path__"):
            raise PluginLoadError(f"'{package}' is not a package")

        candidates: list[Plugin] = self._plugin_types_in_module(package_module)
        for module_info in pkgutil.walk_packages(package_module.__path__, prefix=package + "."):
            try:
                module = import_module(module_info.name)
            except Exception as exc:  # noqa: BLE001 - surface as a PluginLoadError
                raise PluginLoadError(
                    f"Failed to import plugin module '{module_info.name}': {exc}"
                ) from exc
            candidates.extend(self._plugin_types_in_module(module))
        plugins: list[Plugin] = []
        for candidate in candidates:
            plugin = self._load_or_skip(candidate, skip_existing=skip_existing)
            if plugin is not None:
                plugins.append(plugin)
        return tuple(plugins)

    def _load_or_skip(self, plugin: object, *, skip_existing: bool) -> Plugin | None:
        """Load a plugin, or return None when it should be skipped."""
        if not isinstance(plugin, Plugin):
            raise PluginLoadError(
                "auto-discovered value must be a Plugin instance or zero-argument class"
            )
        if skip_existing and plugin.name in self._plugins:
            return None
        return self.load(plugin)

    @staticmethod
    def _plugin_types_in_module(module: ModuleType) -> list[Plugin]:
        """Instantiate every concrete (non-abstract) Plugin subclass in a module."""
        plugins: list[Plugin] = []
        for value in vars(module).values():
            if (
                isinstance(value, type)
                and issubclass(value, Plugin)
                and value is not Plugin
                and not inspect.isabstract(value)
            ):
                plugins.append(value())
        return plugins

    def get(self, name: str) -> Plugin:
        """Return a loaded plugin by name."""
        try:
            return self._plugins[name]
        except KeyError as exc:
            raise PluginNotFoundError(f"No plugin loaded with name: {name}") from exc

    def unload(self, name: str) -> Plugin:
        """Unregister a plugin and remove it from the loader."""
        plugin = self.get(name)
        plugin.unregister(self._kernel)
        del self._plugins[name]
        self._kernel.events.emit(PLUGIN_UNLOADED, context=plugin)
        return plugin

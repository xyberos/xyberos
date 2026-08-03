"""Plugin discovery and lifecycle management."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from ..contracts.plugin import Plugin
from ..exceptions.plugin import PluginAlreadyLoadedError, PluginLoadError, PluginNotFoundError

if TYPE_CHECKING:
    from ..kernel.kernel import Kernel


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
        return plugin

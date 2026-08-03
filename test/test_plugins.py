import sys
from types import ModuleType

import pytest

from xyberos import create_app
from xyberos.contracts import Plugin
from xyberos.exceptions import PluginAlreadyLoadedError, PluginLoadError, PluginNotFoundError


class GreetingPlugin(Plugin):
    @property
    def name(self):
        return "greeting"

    def register(self, kernel):
        kernel.register("greeting", "hello")

    def unregister(self, kernel):
        kernel.registry.unregister("greeting")


def test_plugin_loader_registers_and_unloads_platform_services():
    app = create_app()
    plugin = GreetingPlugin()

    assert app.load_plugin(plugin) is plugin
    assert app.plugins.names == ("greeting",)
    assert app.resolve("greeting") == "hello"
    assert app.unload_plugin("greeting") is plugin
    assert app.plugins.names == ()

    with pytest.raises(PluginNotFoundError, match="No plugin"):
        app.plugins.get("greeting")


def test_plugin_loader_rejects_invalid_or_duplicate_plugins():
    app = create_app()
    app.load_plugin(GreetingPlugin())

    with pytest.raises(PluginAlreadyLoadedError, match="already loaded"):
        app.load_plugin(GreetingPlugin())
    with pytest.raises(TypeError, match="Plugin contract"):
        app.load_plugin(object())


def test_plugin_loader_loads_plugins_from_modules_and_reports_invalid_exports():
    module_name = "xyberos_test_plugin"
    module = ModuleType(module_name)
    module.plugin = GreetingPlugin
    sys.modules[module_name] = module
    app = create_app()

    try:
        plugin = app.plugins.load_from_module(module_name)
    finally:
        del sys.modules[module_name]

    assert plugin.name == "greeting"
    with pytest.raises(PluginLoadError, match="has no"):
        app.plugins.load_from_module("types", "missing_plugin")

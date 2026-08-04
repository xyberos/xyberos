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


class _FakeEntryPoint:
    """Minimal stand-in for ``importlib.metadata.EntryPoint`` in tests."""

    def __init__(self, name, factory):
        self.name = name
        self._factory = factory

    def load(self):
        return self._factory()


def test_plugin_loader_auto_discovers_entry_points(monkeypatch):
    app = create_app()
    monkeypatch.setattr(
        "xyberos.plugins.loader.importlib.metadata.entry_points",
        lambda group: [_FakeEntryPoint("greeting", GreetingPlugin)],
    )

    loaded = app.load_entry_points(group="xyberos.plugins")

    assert [p.name for p in loaded] == ["greeting"]
    assert app.resolve("greeting") == "hello"


def test_plugin_loader_entry_point_discovery_is_idempotent_and_accepts_modules(monkeypatch):
    module = ModuleType("xyberos_test_ep_module")
    module.plugin = GreetingPlugin
    sys.modules["xyberos_test_ep_module"] = module
    app = create_app()
    try:
        monkeypatch.setattr(
            "xyberos.plugins.loader.importlib.metadata.entry_points",
            lambda group: [_FakeEntryPoint("greeting", lambda: module)],
        )
        first = app.load_entry_points()
        second = app.load_entry_points()
    finally:
        del sys.modules["xyberos_test_ep_module"]

    assert [p.name for p in first] == ["greeting"]
    assert second == ()


def test_plugin_loader_auto_discovers_plugins_in_a_package(tmp_path, monkeypatch):
    pkg_dir = tmp_path / "disco_pkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "chat.py").write_text(
        "from xyberos.contracts import Plugin\n"
        "class LocalGreetingPlugin(Plugin):\n"
        "    @property\n"
        "    def name(self):\n"
        "        return 'local_greeting'\n"
        "    def register(self, kernel):\n"
        "        kernel.register('local_greeting', 'hi')\n"
        "    def unregister(self, kernel):\n"
        "        kernel.registry.unregister('local_greeting')\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    app = create_app()
    try:
        loaded = app.load_plugins_from("disco_pkg")
    finally:
        for name in list(sys.modules):
            if name == "disco_pkg" or name.startswith("disco_pkg."):
                del sys.modules[name]

    assert [p.name for p in loaded] == ["local_greeting"]
    assert app.resolve("local_greeting") == "hi"


def test_plugin_loader_rejects_non_package_in_convention_discovery():
    app = create_app()
    with pytest.raises(PluginLoadError, match="not a package"):
        app.plugins.load_from_package("types")  # a module, not a package

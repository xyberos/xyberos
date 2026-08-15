"""Tests for the typed plugin base classes."""

from xyberos import create_app
from xyberos.contracts import Service, Tool
from xyberos_plugin_sdk.base import CONTRIBUTE_METHODS, TYPED_BASES, ServicePlugin, ToolPlugin


class HelloTool(Tool):
    @property
    def name(self):
        return "hello"

    def execute(self, context, **arguments):
        return f"hi {arguments.get('who', 'world')}"


class HelloPlugin(ToolPlugin):
    @property
    def name(self):
        return "hello"

    def tools(self):
        return [HelloTool()]


def test_tool_plugin_registers_and_unregisters():
    app = create_app()
    plugin = HelloPlugin()
    assert app.load_plugin(plugin) is plugin
    assert "hello" in app.tools.names
    assert app.tools.execute("hello", None, who="you") == "hi you"
    assert app.unload_plugin("hello") is plugin
    assert "hello" not in app.tools.names


def test_typed_plugin_metadata():
    assert HelloPlugin.plugin_type == "tool"
    assert HelloPlugin.description == ""


def test_registry_consistency():
    assert TYPED_BASES["tool"] is ToolPlugin
    assert CONTRIBUTE_METHODS["tool"] == "tools"
    assert CONTRIBUTE_METHODS["service"] == "service"
    assert CONTRIBUTE_METHODS["other"] is None


class PingService(Service):
    def __init__(self):
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


class PingPlugin(ServicePlugin):
    @property
    def name(self):
        return "ping"

    def service(self):
        return PingService()


def test_service_plugin_registers_named_service():
    app = create_app()
    app.load_plugin(PingPlugin())
    service = app.resolve("ping")
    assert isinstance(service, PingService)
    service.start()
    assert service.started
    app.unload_plugin("ping")

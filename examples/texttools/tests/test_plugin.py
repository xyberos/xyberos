"""Contract, load, and functional tests for the texttools plugin."""

from xyberos import create_app

from texttools.plugin import TexttoolsPlugin
from texttools.service import CountWordsTool, EchoTool, SlugifyTool


def test_plugin_is_loadable():
    app = create_app()
    plugin = TexttoolsPlugin()
    assert app.load_plugin(plugin) is plugin
    assert plugin.name == "texttools"
    app.unload_plugin(plugin.name)


def test_plugin_conforms_to_contract():
    plugin = TexttoolsPlugin()
    assert isinstance(plugin.name, str) and plugin.name.strip()
    assert callable(plugin.register) and callable(plugin.unregister)


def test_plugin_registers_all_tools():
    plugin = TexttoolsPlugin()
    names = {tool.name for tool in plugin.tools()}
    assert names == {"count_words", "slugify", "echo"}


def test_count_words():
    result = CountWordsTool().execute(None, text="Hello world, this is xyberos!")
    assert result["words"] == 5


def test_count_words_empty():
    assert CountWordsTool().execute(None, text="")["words"] == 0


def test_slugify():
    result = SlugifyTool().execute(None, text="  Hello, World!  42  ")
    assert result["slug"] == "hello-world-42"


def test_slugify_handles_unicode():
    result = SlugifyTool().execute(None, text="café naïvely — déjà vu")
    assert result["slug"] == "cafe-naively-deja-vu"


def test_echo():
    assert EchoTool().execute(None, text="ping") == {"echo": "ping"}

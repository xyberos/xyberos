"""Tests for the AST-based repair."""

from xyberos_cli.repair import repair_source


def test_repair_inserts_missing_tool_stubs():
    source = "from xyberos.contracts import Tool\n\n\nclass MyTool(Tool):\n    pass\n"
    updated, changes = repair_source(source)
    assert changes
    assert "def name" in updated
    assert "def execute" in updated
    compile(updated, "<repaired>", "exec")


def test_repair_noop_when_complete():
    source = (
        "from xyberos.contracts import Tool\n\n\n"
        "class MyTool(Tool):\n"
        "    @property\n"
        "    def name(self):\n"
        "        return 'x'\n\n"
        "    def execute(self, context, **a):\n"
        "        return None\n"
    )
    updated, changes = repair_source(source)
    assert changes == []
    assert updated == source


def test_repair_ignores_unknown_contracts():
    source = "class NotAContract:\n    pass\n"
    updated, changes = repair_source(source)
    assert changes == []
    assert updated == source

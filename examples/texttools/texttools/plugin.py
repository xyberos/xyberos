"""Plugin entry point for the texttools integration."""

from __future__ import annotations

from xyberos.contracts import Tool

from xyberos_plugin_sdk.base import ToolPlugin

from .service import CountWordsTool, EchoTool, SlugifyTool


class TexttoolsPlugin(ToolPlugin):
    """A Tool plugin that contributes three text utility tools."""

    @property
    def name(self) -> str:
        return "texttools"

    def tools(self) -> list[Tool]:
        return [CountWordsTool(), SlugifyTool(), EchoTool()]


plugin = TexttoolsPlugin()

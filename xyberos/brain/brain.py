"""Cognitive orchestration layer."""

from __future__ import annotations

from ..kernel.logger import Logger
from ..llm import EchoLLM, LLMProvider
from ..runtime.context import CognitiveContext
from ..tools import ToolRunner


class Brain:
    """Validate requests, optionally orchestrate tools, and generate responses."""

    def __init__(
        self,
        llm: LLMProvider | None = None,
        logger: Logger | None = None,
        tool_runner: ToolRunner | None = None,
    ) -> None:
        self.llm = llm or EchoLLM()
        self.logger = logger
        self.tool_runner = tool_runner

    def chat(self, context: CognitiveContext) -> str:
        prompt = getattr(context, "prompt", None)
        if not isinstance(prompt, str):
            raise TypeError("context must be a CognitiveContext")

        if self.logger is not None:
            self.logger.debug("Generating response")

        if self.tool_runner is not None:
            try:
                tool_result = self.tool_runner.dispatch(context)
            except ValueError:
                tool_result = None
            else:
                if tool_result is not None:
                    return tool_result if isinstance(tool_result, str) else str(tool_result)

        response = self.llm.generate(prompt)
        if not isinstance(response, str):
            raise TypeError("LLM must return a string")
        return response

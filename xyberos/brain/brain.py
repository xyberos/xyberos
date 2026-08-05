"""Cognitive orchestration layer."""

from __future__ import annotations

from typing import Any

from ..contracts.knowledge import KnowledgeProvider
from ..contracts.memory import MemoryProvider
from ..contracts.planner import Planner
from ..contracts.workflow import Workflow
from ..events import EventBus
from ..events.names import (
    BRAIN_ERROR,
    KNOWLEDGE_QUERIED,
    MEMORY_RETRIEVED,
    MEMORY_STORED,
    PLAN_CREATED,
    RESPONSE_PRODUCED,
    TOOL_DISPATCHED,
    WORKFLOW_RUN,
)
from ..exceptions.workflow import WorkflowPaused
from ..kernel.logger import Logger
from ..llm import EchoLLM, LLMProvider
from ..runtime.context import CognitiveContext
from ..tools import ToolRunner


class Brain:
    """Validate requests, optionally orchestrate tools, and generate responses.

    The built-in single-pass pipeline runs each configured subsystem in order:

    1. Run a :class:`~contracts.workflow.Workflow` first; if it produces a
       response the brain honors it, otherwise processing continues.
    2. Retrieve conversation history from :class:`~contracts.memory.Memory`
       and inject it into the prompt.
    3. Query :class:`~contracts.knowledge.Knowledge` and inject any facts.
    4. Run the :class:`~contracts.planner.Planner` and record its plan on the
       context (the plan is not forced into the model prompt).
    5. Dispatch a matching tool if a :class:`~tools.ToolRunner` is configured.
    6. Ask the LLM, then persist the completed turn back to memory.

    Every subsystem is optional; omitting one leaves its step inactive, so a
    bare ``Brain`` behaves like a plain LLM wrapper.
    """

    def __init__(
        self,
        llm: LLMProvider | None = None,
        logger: Logger | None = None,
        tool_runner: ToolRunner | None = None,
        memory: MemoryProvider | None = None,
        knowledge: KnowledgeProvider | None = None,
        planner: Planner | None = None,
        workflow: Workflow | None = None,
        events: EventBus | None = None,
    ) -> None:
        self.llm = llm or EchoLLM()
        self.logger = logger
        self.tool_runner = tool_runner
        self.memory = memory
        self.knowledge = knowledge
        self.planner = planner
        self.workflow = workflow
        self.events = events

    def chat(self, context: CognitiveContext) -> str:
        prompt = getattr(context, "prompt", None)
        if not isinstance(prompt, str):
            raise TypeError("context must be a CognitiveContext")

        if self.logger is not None:
            self.logger.debug("Generating response")

        try:
            return self._chat(context, prompt)
        except WorkflowPaused:
            raise  # a workflow pause, not an error — let the caller resume it
        except Exception:
            self._emit(BRAIN_ERROR, context=context)
            raise

    def _chat(self, context: CognitiveContext, prompt: str) -> str:
        """Run the configured pipeline and return the generated response."""
        # A configured workflow gets first crack at producing the response.
        # A step-less workflow passes the context through unchanged, so the
        # built-in pipeline below still runs.
        if self.workflow is not None:
            result = self.workflow.run(context)
            self._emit(WORKFLOW_RUN, context=context)
            if not isinstance(result, CognitiveContext):
                raise TypeError("workflow must return a CognitiveContext")
            if result.response is not None:
                self._remember(result, result.response)
                return result.response
            context = result

        enriched = self._enrich_prompt(context, prompt)

        if self.tool_runner is not None:
            try:
                tool_result = self.tool_runner.dispatch(context)
            except ValueError:
                tool_result = None
            else:
                if tool_result is not None:
                    response = tool_result if isinstance(tool_result, str) else str(tool_result)
                    self._emit(TOOL_DISPATCHED, context=context)
                    self._remember(context, response)
                    return response

        response = self.llm.generate(enriched)
        if not isinstance(response, str):
            raise TypeError("LLM must return a string")
        self._emit(RESPONSE_PRODUCED, context=context, response=response)
        self._remember(context, response)
        return response

    def _enrich_prompt(self, context: CognitiveContext, prompt: str) -> str:
        """Compose memory and knowledge context around the original prompt."""
        sections = [prompt]

        if self.memory is not None:
            entries = self.memory.retrieve(context)
            self._emit(MEMORY_RETRIEVED, context=context, count=_size(entries))
            history = self._format_history(entries)
            if history:
                sections.append(f"Conversation history:\n{history}")

        if self.knowledge is not None:
            facts = self.knowledge.query(context)
            self._emit(KNOWLEDGE_QUERIED, context=context)
            if facts:
                sections.append(f"Relevant knowledge:\n{facts}")

        if self.planner is not None:
            plan = self.planner.plan(context)
            context.plan = plan
            self._emit(PLAN_CREATED, context=context)

        return "\n\n".join(sections)

    def _remember(self, context: CognitiveContext, response: str) -> None:
        """Persist a completed turn so future requests can recall it."""
        if self.memory is None:
            return
        context.response = response
        self.memory.store(context)
        self._emit(MEMORY_STORED, context=context)

    def _emit(self, name: str, *, context: object | None = None, **data: Any) -> None:
        """Publish ``name`` on the event bus when one is configured."""
        if self.events is not None:
            self.events.emit(name, context=context, **data)

    @staticmethod
    def _format_history(entries: Any) -> str:
        """Render stored entries as a readable user/assistant transcript."""
        lines = []
        for entry in entries or []:
            user = getattr(entry, "prompt", None)
            assistant = getattr(entry, "response", None)
            if user is None and assistant is None:
                lines.append(str(entry))
                continue
            line = f"user: {user}" if user is not None else ""
            if assistant is not None:
                line = f"{line}\nassistant: {assistant}" if line else f"assistant: {assistant}"
            lines.append(line)
        return "\n\n".join(lines)


def _size(value: Any) -> int | None:
    """Best-effort length for provider-defined retrieval results."""
    if hasattr(value, "__len__"):
        try:
            return len(value)
        except TypeError:
            return None
    return None

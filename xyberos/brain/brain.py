"""Cognitive orchestration layer."""

from __future__ import annotations

from dataclasses import dataclass
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
    TOKEN_STREAMED,
    TOOL_DISPATCHED,
    WORKFLOW_RUN,
)
from ..exceptions.workflow import WorkflowPaused
from ..kernel.config import Config
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
        config: Config | None = None,
    ) -> None:
        self.llm = llm or EchoLLM()
        self.logger = logger
        self.tool_runner = tool_runner
        self.memory = memory
        self.knowledge = knowledge
        self.planner = planner
        self.workflow = workflow
        self.events = events
        self.config = config
        self._inject_plan = bool(config.get("brain.inject_plan", False)) if config is not None else False

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

    async def achat(self, context: CognitiveContext) -> str:
        """Async variant of :meth:`chat`, awaiting an async LLM when available."""
        prompt = getattr(context, "prompt", None)
        if not isinstance(prompt, str):
            raise TypeError("context must be a CognitiveContext")

        if self.logger is not None:
            self.logger.debug("Generating response")

        try:
            return await self._achat(context, prompt)
        except WorkflowPaused:
            raise  # a workflow pause, not an error — let the caller resume it
        except Exception:
            self._emit(BRAIN_ERROR, context=context)
            raise

    def _chat(self, context: CognitiveContext, prompt: str) -> str:
        """Run the configured pipeline synchronously and return the response."""
        prepared = self._prepare(context, prompt)
        if prepared.short_response is not None:
            self._remember(prepared.context, prepared.short_response)
            return prepared.short_response
        if prepared.tool_response is not None:
            return self._handle_tool(prepared)
        response = self._generate(prepared.context, prepared.prompt)
        self._emit(RESPONSE_PRODUCED, context=prepared.context, response=response)
        self._remember(prepared.context, response)
        return response

    async def _achat(self, context: CognitiveContext, prompt: str) -> str:
        """Run the configured pipeline asynchronously and return the response."""
        prepared = self._prepare(context, prompt)
        if prepared.short_response is not None:
            self._remember(prepared.context, prepared.short_response)
            return prepared.short_response
        if prepared.tool_response is not None:
            return self._handle_tool(prepared)
        response = await self._agenerate(prepared.context, prepared.prompt)
        self._emit(RESPONSE_PRODUCED, context=prepared.context, response=response)
        self._remember(prepared.context, response)
        return response

    def _prepare(self, context: CognitiveContext, prompt: str) -> _Prepared:
        """Run workflow, memory, knowledge, planner, and tools; return what to send."""
        # A configured workflow gets first crack at producing the response.
        # A step-less workflow passes the context through unchanged, so the
        # built-in pipeline below still runs.
        if self.workflow is not None:
            result = self.workflow.run(context)
            self._emit(WORKFLOW_RUN, context=context)
            if not isinstance(result, CognitiveContext):
                raise TypeError("workflow must return a CognitiveContext")
            if result.response is not None:
                return _Prepared(context=result, prompt=prompt, short_response=result.response)
            context = result

        enriched = self._enrich_prompt(context, prompt)

        if self.tool_runner is not None:
            try:
                tool_result = self.tool_runner.dispatch(context)
            except ValueError:
                tool_result = None
            else:
                if tool_result is not None:
                    return _Prepared(context=context, prompt=enriched, tool_response=tool_result)

        return _Prepared(context=context, prompt=enriched)

    def _handle_tool(self, prepared: _Prepared) -> str:
        """Finalize a tool-produced response."""
        tool = prepared.tool_response
        response = tool if isinstance(tool, str) else str(tool)
        self._emit(TOOL_DISPATCHED, context=prepared.context)
        self._remember(prepared.context, response)
        return response

    def _generate(self, context: CognitiveContext, prompt: str) -> str:
        """Generate text synchronously, streaming tokens when the LLM supports it."""
        stream = getattr(self.llm, "stream", None)
        if callable(stream):
            response = stream(prompt, self._token_sink(context))
        else:
            generate = getattr(self.llm, "generate", None)
            if not callable(generate):
                raise TypeError("LLM must implement generate() for synchronous use")
            response = generate(prompt)
        if not isinstance(response, str):
            raise TypeError("LLM must return a string")
        return response

    async def _agenerate(self, context: CognitiveContext, prompt: str) -> str:
        """Generate text asynchronously, preferring astream/agenerate when present."""
        astream = getattr(self.llm, "astream", None)
        if callable(astream):
            response = await astream(prompt, self._token_sink(context))
        else:
            agenerate = getattr(self.llm, "agenerate", None)
            if callable(agenerate):
                response = await agenerate(prompt)
            else:
                generate = getattr(self.llm, "generate", None)
                if not callable(generate):
                    raise TypeError("LLM must implement agenerate() for asynchronous use")
                response = generate(prompt)
        if not isinstance(response, str):
            raise TypeError("LLM must return a string")
        return response

    def _token_sink(self, context: CognitiveContext) -> Any:
        """Return a callback that publishes each streamed token as an event."""

        def sink(token: str) -> None:
            self._emit(TOKEN_STREAMED, context=context, token=token)

        return sink

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
            if self._inject_plan:
                formatted = self._format_plan(plan)
                if formatted:
                    sections.append(f"Plan:\n{formatted}")

        return "\n\n".join(sections)

    @staticmethod
    def _format_plan(plan: Any) -> str:
        """Render a provider-defined plan as readable text."""
        if isinstance(plan, str):
            return plan
        if isinstance(plan, (list, tuple)):
            return "\n".join(f"- {item}" for item in plan)
        return str(plan)

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


@dataclass
class _Prepared:
    """The outcome of preparing a request up to the LLM call."""

    context: CognitiveContext
    prompt: str
    short_response: str | None = None
    tool_response: Any | None = None

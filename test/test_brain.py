import pytest

from xyberos.brain.brain import Brain
from xyberos.runtime.context import CognitiveContext
from xyberos.llm import CallableLLM
from xyberos.contracts import Tool
from xyberos.knowledge import InMemoryKnowledge
from xyberos.memory import InMemoryMemory
from xyberos.planner import SequentialPlanner
from xyberos.tools import ToolRunner
from xyberos.workflows import SequentialWorkflow


class RecordingLogger:
    def __init__(self):
        self.messages = []

    def debug(self, message):
        self.messages.append(message)


class InvalidResponseModel:
    def generate(self, prompt):
        return 1


class ReverseTool(Tool):
    @property
    def name(self):
        return "reverse"

    def execute(self, context, **arguments):
        return context.prompt[::-1]


def test_brain_sends_prompt_to_llm_and_logs_generation():
    logger = RecordingLogger()
    brain = Brain(CallableLLM(lambda prompt: f"answer:{prompt}"), logger)

    assert brain.chat(CognitiveContext("question")) == "answer:question"
    assert logger.messages == ["Generating response"]


def test_brain_uses_tool_runner_before_llm_when_a_tool_matches():
    brain = Brain(CallableLLM(lambda prompt: f"answer:{prompt}"), tool_runner=ToolRunner([ReverseTool()]))

    assert brain.chat(CognitiveContext("reverse")) == "esrever"


def test_brain_rejects_invalid_context_and_non_text_response():
    with pytest.raises(TypeError, match="CognitiveContext"):
        Brain().chat("not a context")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="LLM must return a string"):
        Brain(InvalidResponseModel()).chat(CognitiveContext("question"))


def test_brain_recalls_stored_turns_in_conversation_history():
    memory = InMemoryMemory()
    seen = []
    brain = Brain(
        CallableLLM(lambda prompt: (seen.append(prompt) or f"answer:{prompt}")),
        memory=memory,
    )

    brain.chat(CognitiveContext("first"))
    brain.chat(CognitiveContext("second"))

    assert len(memory.retrieve(None)) == 2
    assert "user: first" not in seen[0]  # first turn has no history yet
    assert "user: first" in seen[1]
    assert "assistant: answer:first" in seen[1]
    assert "user: second" not in seen[1]  # current turn is not its own history


def test_brain_injects_matching_knowledge_facts_into_prompt():
    knowledge = InMemoryKnowledge({"python": "Xyberos is a cognitive framework"})
    seen = []
    brain = Brain(CallableLLM(lambda prompt: (seen.append(prompt) or "ok")), knowledge=knowledge)

    brain.chat(CognitiveContext("tell me about python"))

    assert "Relevant knowledge:" in seen[0]
    assert "Xyberos is a cognitive framework" in seen[0]


def test_brain_runs_planner_and_records_plan_on_context():
    planner = SequentialPlanner()
    context = CognitiveContext("build a widget")
    brain = Brain(CallableLLM(lambda prompt: "done"), planner=planner)

    brain.chat(context)

    assert context.plan == [
        "analyze: build a widget",
        "execute: build a widget",
        "review: build a widget",
    ]


def test_brain_honors_response_produced_by_a_workflow():
    def step(context: CognitiveContext) -> None:
        context.response = "from workflow"

    workflow = SequentialWorkflow([step])
    brain = Brain(CallableLLM(lambda prompt: "from llm"), workflow=workflow)

    assert brain.chat(CognitiveContext("hi")) == "from workflow"


def test_brain_step_less_workflow_falls_through_to_llm():
    workflow = SequentialWorkflow()
    brain = Brain(CallableLLM(lambda prompt: f"answer:{prompt}"), workflow=workflow)

    assert brain.chat(CognitiveContext("question")) == "answer:question"


def test_brain_rejects_workflow_that_returns_a_non_context():
    class BadWorkflow:
        def run(self, context):
            return "not a context"

    brain = Brain(CallableLLM(lambda prompt: "ok"), workflow=BadWorkflow())

    with pytest.raises(TypeError, match="workflow must return a CognitiveContext"):
        brain.chat(CognitiveContext("hi"))


def test_brain_formats_non_context_memory_entries_as_text():
    memory = InMemoryMemory()
    memory.store("plain note")  # an entry without prompt/response attributes
    seen = []
    brain = Brain(CallableLLM(lambda prompt: (seen.append(prompt) or "ok")), memory=memory)

    brain.chat(CognitiveContext("hi"))

    assert "plain note" in seen[0]


def test_brain_remembers_tool_responses():
    memory = InMemoryMemory()
    brain = Brain(
        CallableLLM(lambda prompt: "never"),
        tool_runner=ToolRunner([ReverseTool()]),
        memory=memory,
    )

    assert brain.chat(CognitiveContext("reverse")) == "esrever"
    stored = memory.retrieve(None)
    assert len(stored) == 1
    assert stored[0].response == "esrever"

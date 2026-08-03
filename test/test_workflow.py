import pytest

from contracts import Workflow
from runtime.context import CognitiveContext
from workflows import SequentialWorkflow


def test_workflow_contract_requires_run():
    with pytest.raises(TypeError):
        Workflow()


def test_sequential_workflow_runs_steps_against_the_same_context():
    context = CognitiveContext("workflow")

    def annotate(item):
        item.metadata["validated"] = True

    def respond(item):
        item.response = f"done:{item.prompt}"
        return item

    workflow = SequentialWorkflow([annotate, respond])

    result = workflow.run(context)

    assert result is context
    assert result.metadata == {"validated": True}
    assert result.response == "done:workflow"
    assert workflow.steps == (annotate, respond)


def test_sequential_workflow_validates_steps_and_contexts():
    with pytest.raises(TypeError, match="all workflow steps"):
        SequentialWorkflow(["not callable"])  # type: ignore[list-item]

    workflow = SequentialWorkflow()
    with pytest.raises(TypeError, match="workflow step"):
        workflow.add_step("not callable")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="CognitiveContext"):
        workflow.run("not a context")


def test_sequential_workflow_rejects_invalid_step_results():
    workflow = SequentialWorkflow([lambda _: "not a context"])

    with pytest.raises(TypeError, match="must return"):
        workflow.run(CognitiveContext("workflow"))

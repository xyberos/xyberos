"""Tests for workflow checkpointing and cross-process resume."""

import pytest

from xyberos.exceptions import WorkflowPaused
from xyberos.runtime.context import CognitiveContext
from xyberos.workflows import GraphWorkflow, WorkflowCheckpoint


def make_graph():
    graph = GraphWorkflow("ask")

    def ask(context):
        if GraphWorkflow.RESUME_KEY in context.metadata:
            context.response = "approved"
            return context
        raise WorkflowPaused(prompt="Approve?")

    graph.add_node("ask", ask)
    return graph


def test_checkpoint_round_trips_a_paused_run():
    run = make_graph().execute(CognitiveContext("task"))
    checkpoint = WorkflowCheckpoint()

    checkpoint.save("run-1", run)
    restored = checkpoint.load("run-1")

    assert restored.status == "paused"
    assert restored.node == "ask"
    assert restored.prompt == "Approve?"
    assert restored.context.prompt == "task"
    assert checkpoint.list_ids() == ("run-1",)


def test_checkpoint_load_missing_and_delete():
    checkpoint = WorkflowCheckpoint()

    with pytest.raises(KeyError, match="run_id"):
        checkpoint.load("missing")

    checkpoint.save("x", make_graph().execute(CognitiveContext("t")))
    checkpoint.delete("x")
    assert checkpoint.list_ids() == ()
    checkpoint.close()


def test_checkpoint_persists_across_connections(tmp_path):
    path = str(tmp_path / "runs.db")
    checkpoint = WorkflowCheckpoint(path)
    checkpoint.save("r1", make_graph().execute(CognitiveContext("task")))
    checkpoint.close()

    checkpoint2 = WorkflowCheckpoint(path)
    restored = checkpoint2.load("r1")
    assert restored.node == "ask"
    checkpoint2.close()


def test_resume_from_checkpoint_in_a_new_process(tmp_path):
    path = str(tmp_path / "runs.db")

    # "process 1": pause the graph and persist the run.
    checkpoint = WorkflowCheckpoint(path)
    paused = make_graph().execute(CognitiveContext("task"))
    checkpoint.save("r1", paused)
    checkpoint.close()

    # "process 2": a fresh graph + checkpoint resume the paused run.
    graph = make_graph()
    checkpoint2 = WorkflowCheckpoint(path)
    run = graph.resume_from_checkpoint(checkpoint2, "r1", "yes")

    assert run.status == "completed"
    assert run.context.response == "approved"
    checkpoint2.close()

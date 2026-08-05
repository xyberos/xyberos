"""Tests for the state-graph workflow engine (branches, loops, pause/resume)."""

import pytest

from xyberos import create_app
from xyberos.exceptions import WorkflowError, WorkflowPaused
from xyberos.llm import CallableLLM
from xyberos.runtime.context import CognitiveContext
from xyberos.workflows import GraphWorkflow, WorkflowRun


def test_graph_workflow_completes_a_linear_path():
    graph = GraphWorkflow("start")
    graph.add_node("start", lambda c: c)
    graph.add_node("finish", lambda c: (setattr(c, "response", "done") or c))
    graph.add_edge("start", "finish")

    result = graph.run(CognitiveContext("task"))

    assert result.response == "done"


def test_graph_execute_reports_steps_and_count():
    graph = GraphWorkflow("a")
    graph.add_node("a", lambda c: c).add_node("b", lambda c: c).add_edge("a", "b")
    graph.add_node("c", lambda c: c).add_edge("b", "c")

    run = graph.execute(CognitiveContext("x"))

    assert isinstance(run, WorkflowRun)
    assert run.status == "completed"
    assert run.steps == ("a", "b", "c")
    assert run.steps_taken == 3
    assert run.node == "c"


def test_graph_workflow_branches_with_a_route():
    graph = GraphWorkflow("decide")

    def decide(context):
        context.metadata["path"] = "a" if context.prompt.startswith("a") else "b"
        return context

    def branch_a(context):
        context.response = "went A"
        return context

    def branch_b(context):
        context.response = "went B"
        return context

    graph.add_node("decide", decide)
    graph.add_node("a", branch_a)
    graph.add_node("b", branch_b)
    graph.add_route("decide", lambda ctx: "a" if ctx.metadata["path"] == "a" else "b")

    assert graph.run(CognitiveContext("alpha")).response == "went A"
    assert graph.run(CognitiveContext("beta")).response == "went B"


def test_graph_workflow_loop_terminates_and_guards():
    graph = GraphWorkflow("count")

    def count(context):
        n = context.metadata.get("n", 0)
        context.metadata["n"] = n + 1
        if n + 1 >= 3:
            context.response = "done"
        return context

    graph.add_node("count", count)
    graph.add_route("count", lambda ctx: None if ctx.metadata["n"] >= 3 else "count")

    assert graph.run(CognitiveContext("loop")).response == "done"

    spinning = GraphWorkflow("spin", max_steps=5)
    spinning.add_node("spin", lambda c: c)
    spinning.add_edge("spin", "spin")

    with pytest.raises(WorkflowError, match="max steps"):
        spinning.execute(CognitiveContext("spin"))


def test_graph_workflow_pause_and_resume_loop():
    graph = GraphWorkflow("ask")

    def ask(context):
        if GraphWorkflow.RESUME_KEY in context.metadata:
            context.response = f"approved:{context.metadata[GraphWorkflow.RESUME_KEY]}"
            return context
        raise WorkflowPaused(prompt="Approve the action?")

    graph.add_node("ask", ask)

    run = graph.execute(CognitiveContext("task"))
    assert run.status == "paused"
    assert run.prompt == "Approve the action?"
    assert run.node == "ask"

    run = graph.resume(run, "yes")
    assert run.status == "completed"
    assert run.context.response == "approved:yes"
    assert run.context.metadata[GraphWorkflow.RESUME_KEY] == "yes"


def test_graph_run_raises_workflow_paused_with_run_attached():
    graph = GraphWorkflow("ask")

    def ask(context):
        raise WorkflowPaused(prompt="need input")

    graph.add_node("ask", ask)

    with pytest.raises(WorkflowPaused) as excinfo:
        graph.run(CognitiveContext("hi"))

    pause = excinfo.value
    assert pause.prompt == "need input"
    assert pause.run.status == "paused"
    assert pause.run.node == "ask"


def test_graph_workflow_through_the_brain_completes():
    graph = GraphWorkflow("start")
    graph.add_node("start", lambda c: c)
    graph.add_node("finish", lambda c: (setattr(c, "response", "done") or c))
    graph.add_edge("start", "finish")

    app = create_app(llm=CallableLLM(lambda prompt: "never"), workflow=graph)

    assert app.chat("hi") == "done"


def test_graph_workflow_pause_propagates_through_the_brain():
    graph = GraphWorkflow("ask")

    def ask(context):
        if GraphWorkflow.RESUME_KEY in context.metadata:
            context.response = "human said yes"
            return context
        raise WorkflowPaused(prompt="Approve?")

    graph.add_node("ask", ask)
    app = create_app(workflow=graph)

    with pytest.raises(WorkflowPaused) as excinfo:
        app.chat("hi")

    pause = excinfo.value
    assert pause.prompt == "Approve?"
    assert pause.run.status == "paused"

    run = graph.resume(pause.run, "yes")
    assert run.status == "completed"
    assert run.context.response == "human said yes"


def test_graph_resume_requires_a_paused_run():
    graph = GraphWorkflow("a")
    graph.add_node("a", lambda c: c)
    run = graph.execute(CognitiveContext("x"))

    with pytest.raises(ValueError, match="paused"):
        graph.resume(run)


def test_graph_workflow_validates_nodes_edges_and_routes():
    graph = GraphWorkflow("start")
    graph.add_node("start", lambda c: c)

    with pytest.raises(ValueError, match="unknown node"):
        graph.add_edge("start", "missing")
    with pytest.raises(ValueError, match="unknown node"):
        graph.add_edge("missing", "start")
    with pytest.raises(ValueError, match="already registered"):
        graph.add_node("start", lambda c: c)
    with pytest.raises(ValueError, match="non-empty"):
        graph.add_node("", lambda c: c)
    with pytest.raises(TypeError, match="callable"):
        graph.add_node("bad", object())

    graph.add_node("next", lambda c: c)
    graph.add_edge("start", "next")
    with pytest.raises(ValueError, match="already has"):
        graph.add_route("start", lambda c: "next")


def test_graph_workflow_rejects_route_to_unknown_node_and_bad_results():
    graph = GraphWorkflow("start")
    graph.add_node("start", lambda c: c)
    graph.add_route("start", lambda c: "ghost")

    with pytest.raises(WorkflowError, match="unknown node"):
        graph.execute(CognitiveContext("x"))

    bad = GraphWorkflow("start")
    bad.add_node("start", lambda c: "not a context")
    with pytest.raises(TypeError, match="CognitiveContext"):
        bad.execute(CognitiveContext("x"))


def test_graph_workflow_constructor_validation():
    with pytest.raises(ValueError, match="non-empty"):
        GraphWorkflow("")
    with pytest.raises(ValueError, match="positive"):
        GraphWorkflow("start", max_steps=0)

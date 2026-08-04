"""End-to-end smoke test for the complete Xyberos pipeline."""

from xyberos import create_app
from xyberos.llm import CallableLLM


def test_all_core_components_run_together():
    """A configured app processes a request through every core layer."""
    app = create_app(
        config={"logger_name": "xyberos.tests.end_to_end", "log_level": "WARNING"},
        llm=CallableLLM(lambda prompt: f"processed: {prompt}"),
    )

    context = app.run("validate the complete pipeline", metadata={"request_id": "e2e-001"})

    assert context.succeeded
    assert context.response == "processed: validate the complete pipeline"
    assert context.metadata == {"request_id": "e2e-001"}
    assert context.error is None


def test_default_app_automatically_remembers_conversation_across_turns():
    """A default app wires memory into the brain without user intervention."""
    app = create_app()

    first = app.chat("hello")
    second = app.chat("what did I just say?")

    assert "hello" in first
    assert "hello" in second
    assert len(app.memory.retrieve(None)) == 2

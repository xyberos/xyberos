"""End-to-end smoke test for the complete Xyberos pipeline."""

from brain.llm import CallableLLM
from xyberos import create_app


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

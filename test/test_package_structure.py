"""Keep the public subsystem namespace layout stable as Xyberos grows."""

import importlib

import pytest


@pytest.mark.parametrize(
    "subsystem",
    [
        "kernel",
        "runtime",
        "brain",
        "contracts",
        "memory",
        "knowledge",
        "planner",
        "tools",
        "events",
        "plugins",
        "workflows",
        "agents",
        "experience",
        "intent",
        "learning",
        "trainer",
        "vector",
    ],
)
def test_public_subsystem_namespace_is_importable(subsystem):
    assert importlib.import_module(f"xyberos.{subsystem}")

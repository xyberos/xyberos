"""The public surface is importable, typed, and usable end to end."""

import asyncio
from typing import Annotated, get_type_hints

import pytest

import xyberos
from xyberos import App, Inject, RegistrationError, Scope, Settings, Workflow


class Counter:
    def __init__(self) -> None:
        self.value = 0


class CounterHolder:
    def __init__(self, counter: Annotated[Counter, Inject()]) -> None:
        self.counter = counter


def test_expected_public_names_are_exported() -> None:
    expected = {
        "DIRECT_WORKFLOW",
        "App",
        "AppSettings",
        "Attempt",
        "Backoff",
        "BranchPredicate",
        "CancellationToken",
        "Clock",
        "ConfigurationError",
        "ContextLogFilter",
        "Dependency",
        "DependencyCycleError",
        "DependencyError",
        "DependencyResolutionError",
        "Diagnostics",
        "Edge",
        "EventSink",
        "EventType",
        "Inject",
        "InputType",
        "LifecycleError",
        "LifecycleState",
        "LifecycleStateError",
        "MissingProviderError",
        "PLUGIN_API_VERSION",
        "Plugin",
        "PluginCompatibilityError",
        "PluginConfigurationError",
        "PluginDependencyError",
        "PluginError",
        "PluginInfo",
        "PluginLifecycleError",
        "PluginRegistry",
        "PluginState",
        "PluginValidationError",
        "Provider",
        "ProviderInfo",
        "ProviderRegistry",
        "RegistrationError",
        "RequestContext",
        "Retry",
        "RetryExhaustedError",
        "Scope",
        "ScopeViolationError",
        "Settings",
        "ShutdownError",
        "Step",
        "StepContext",
        "StepFunction",
        "StepOutcome",
        "StepStatus",
        "StepTimeoutError",
        "SystemClock",
        "TransientError",
        "Workflow",
        "WorkflowCancelledError",
        "WorkflowError",
        "WorkflowEvent",
        "WorkflowExecutionError",
        "WorkflowExecutor",
        "WorkflowResult",
        "WorkflowTimeoutError",
        "WorkflowValidationError",
        "XyberosError",
        "bind_context",
        "bind_correlation_id",
        "bind_deadline",
        "capture_context_runner",
        "create_task_in_context",
        "direct",
        "get_context",
        "get_correlation_id",
        "get_deadline",
        "load_settings",
        "milliseconds",
        "minutes",
        "seconds",
    }

    assert expected <= set(xyberos.__all__)
    for name in sorted(expected):
        assert hasattr(xyberos, name), name


def test_public_api_versions_are_present() -> None:
    assert xyberos.__version__ == "2.2.0"


def test_injected_annotations_are_explicit_and_typed() -> None:
    hints = get_type_hints(CounterHolder.__init__, include_extras=True)

    assert hints["counter"] == Annotated[Counter, Inject()]


def test_runtime_rejects_injection_without_a_marker() -> None:
    class Unmarked:
        def __init__(self, counter: Counter) -> None:
            self.counter = counter

    app = App(settings=Settings.load(environ={}))

    with pytest.raises(RegistrationError):
        app.provide(Unmarked)


def test_composition_and_resolution_work_end_to_end() -> None:
    async def scenario() -> None:
        app = App(settings=Settings.load(environ={}))
        app.provide(Counter, scope=Scope.APP)
        app.provide(CounterHolder)
        app.validate()

        async with app.lifespan() as running:
            assert running is app
            holder = await running.resolve(CounterHolder)
            holder.counter.value += 1

            assert (await running.resolve(CounterHolder)).counter.value == 1

    asyncio.run(scenario())


def test_a_workflow_is_part_of_the_core_surface() -> None:
    async def scenario() -> None:
        async def double(value: object, context: object) -> object:
            return value * 2  # type: ignore[operator]

        workflow = Workflow("demo", version="1").step("double", double)

        result = await workflow.run(input=2)

        assert result.value == 4

    asyncio.run(scenario())

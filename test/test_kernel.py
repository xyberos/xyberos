import pytest

from brain.llm import CallableLLM
from kernel.config import Config
from kernel.kernel import Kernel
from runtime.context import CognitiveContext


class LifecycleService:
    def __init__(self, events, name):
        self.events = events
        self.name = name

    def start(self):
        self.events.append(f"start:{self.name}")

    def stop(self):
        self.events.append(f"stop:{self.name}")


def test_kernel_wires_configuration_model_and_runtime():
    config = Config({"logger_name": "xyberos.tests.kernel", "log_level": "WARNING"})
    kernel = Kernel(config, llm=CallableLLM(lambda prompt: prompt[::-1]))

    context = kernel.run("abc", metadata={"trace": "t-1"})

    assert isinstance(context, CognitiveContext)
    assert context.response == "cba"
    assert context.metadata == {"trace": "t-1"}
    assert kernel.chat("xy") == "yx"
    assert kernel.config is config
    assert kernel.resolve("brain") is kernel.brain
    assert kernel.resolve("runtime") is kernel.runtime


def test_kernel_registers_resolves_and_manages_service_lifecycles():
    kernel = Kernel({"logger_name": "xyberos.tests.lifecycle"})
    events = []
    first = LifecycleService(events, "first")
    second = LifecycleService(events, "second")

    assert kernel.resolve("config") is kernel.config
    assert kernel.register("first", first) is first
    kernel.register("second", second)
    kernel.start()

    assert kernel.started
    assert events == ["start:first", "start:second"]

    kernel.stop()

    assert not kernel.started
    assert events == ["start:first", "start:second", "stop:second", "stop:first"]


def test_kernel_validates_and_protects_service_registration():
    kernel = Kernel({"logger_name": "xyberos.tests.registration"})

    with pytest.raises(ValueError, match="non-empty"):
        kernel.register("", object())
    with pytest.raises(KeyError, match="already registered"):
        kernel.register("config", object())
    with pytest.raises(KeyError, match="No service registered"):
        kernel.resolve("missing")


def test_kernel_lifecycle_is_idempotent_and_starts_late_services():
    kernel = Kernel({"logger_name": "xyberos.tests.late-service"})
    events = []

    kernel.start()
    kernel.start()
    late_service = LifecycleService(events, "late")
    kernel.register("late", late_service)
    kernel.register("late", late_service, replace=True)
    kernel.stop()
    kernel.stop()

    assert events == ["start:late", "start:late", "stop:late"]


def test_kernel_rejects_factory_registration_after_starting():
    kernel = Kernel({"logger_name": "xyberos.tests.factory-lifecycle"})
    kernel.start()

    with pytest.raises(RuntimeError, match="before starting"):
        kernel.register_factory("late_factory", lambda: object())

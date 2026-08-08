from xyberos import Xyberos, chat, create_app
from xyberos.llm import CallableLLM


def test_public_api_creates_app_and_supports_one_shot_chat():
    model = CallableLLM(lambda prompt: f"handled:{prompt}")

    app = create_app(llm=model)

    assert isinstance(app, Xyberos)
    assert app.chat("request") == "handled:request"
    assert chat("once", llm=model) == "handled:once"


def test_public_app_delegates_kernel_services_dependency_injection_and_lifecycle():
    app = create_app(config={"logger_name": "xyberos.tests.public"})
    service = object()

    assert app.config is app.kernel.config
    assert app.logger is app.kernel.logger
    assert app.registry is app.kernel.registry
    assert app.llm is app.resolve("llm")
    assert app.memory is app.resolve("memory")
    assert app.knowledge is app.resolve("knowledge")
    assert app.tools is app.resolve("tools")
    assert app.tool_runner is app.resolve("tool_runner")
    assert app.planner is app.resolve("planner")
    assert app.workflow is app.resolve("workflow")
    assert app.register("custom", service) is service
    assert app.resolve("custom") is service
    assert app.register_factory("injected_logger", lambda logger: logger) is not None
    assert app.resolve("injected_logger") is app.logger
    assert app.inject(lambda logger: logger) is app.logger

    app.start()
    assert app.started
    app.stop()
    assert not app.started


def test_public_app_exposes_intent_and_experience_services():
    app = create_app()

    assert app.intent is app.resolve("intent")
    assert app.experience is app.resolve("experience")

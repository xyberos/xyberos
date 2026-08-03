from brain.llm import CallableLLM
from xyberos import Xyberos, chat, create_app


def test_public_api_creates_app_and_supports_one_shot_chat():
    model = CallableLLM(lambda prompt: f"handled:{prompt}")

    app = create_app(llm=model)

    assert isinstance(app, Xyberos)
    assert app.chat("request") == "handled:request"
    assert chat("once", llm=model) == "handled:once"

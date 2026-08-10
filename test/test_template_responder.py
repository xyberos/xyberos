from xyberos.contracts import Template
from xyberos.router import TemplateResponder


class Context:
    def __init__(self, prompt, intent=None, metadata=None):
        self.prompt = prompt
        self.intent = intent
        self.metadata = metadata or {}


class Intent:
    def __init__(self, name):
        self.name = name


def test_template_responder_matches_prompt_substring():
    responder = TemplateResponder([Template(pattern="hello", variants=("Hello!",))])
    assert responder.respond(Context("hello there")) == "Hello!"


def test_template_responder_matches_intent_name_exactly():
    responder = TemplateResponder([Template(pattern="greeting", variants=("Hello!",))])
    context = Context("any prompt", intent=Intent("greeting"))
    assert responder.respond(context) == "Hello!"


def test_template_responder_matches_regex_pattern():
    responder = TemplateResponder([Template(pattern="hello|hi|hey", variants=("Hello!",))])
    assert responder.respond(Context("hey there")) == "Hello!"
    assert responder.respond(Context("hi")) == "Hello!"


def test_template_responder_returns_none_when_nothing_matches():
    responder = TemplateResponder([Template(pattern="hello", variants=("Hello!",))])
    assert responder.respond(Context("reset my password")) is None


def test_template_responder_rotates_variants_to_avoid_repetition():
    responder = TemplateResponder([Template(
        pattern="hello|hi|hey|good morning",
        variants=("Hello!", "Hi there!", "Welcome!"),
    )])
    first = responder.respond(Context("hello"))
    second = responder.respond(Context("hi"))
    third = responder.respond(Context("hey"))
    assert (first, second, third) == ("Hello!", "Hi there!", "Welcome!")
    # Round-robin wraps back to the first variant.
    assert responder.respond(Context("good morning")) == "Hello!"


def test_template_responder_injects_metadata_context():
    responder = TemplateResponder([
        Template(
            pattern="billing",
            variants=("Your last {amount} payment was on {date}.",),
        )
    ])
    context = Context("billing please", metadata={"amount": "$49.99", "date": "Aug 1"})
    assert responder.respond(context) == "Your last $49.99 payment was on Aug 1."


def test_template_responder_leaves_unknown_placeholders_alone():
    responder = TemplateResponder([Template(pattern="billing", variants=("Cost: {amount}.",))])
    context = Context("billing", metadata={"date": "Aug 1"})
    assert responder.respond(context) == "Cost: {amount}."


def test_template_responder_confidence_reflects_best_match():
    responder = TemplateResponder([
        Template(pattern=r"\bhello\b|\bhey\b", variants=("Hi!",), confidence=0.95),
        Template(pattern="billing", variants=("Billing.",), confidence=0.8),
    ])
    assert responder.confidence(Context("hello")) == 0.95
    assert responder.confidence(Context("billing")) == 0.8
    assert responder.confidence(Context("nothing relevant")) == 0.0


def test_template_responder_gates_below_threshold():
    responder = TemplateResponder(
        [Template(pattern="help", variants=("Ok.",), confidence=0.3)],
        threshold=0.5,
    )
    assert responder.respond(Context("help me")) is None

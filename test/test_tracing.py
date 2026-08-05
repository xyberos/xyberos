"""Tests for the event tracing hooks and exporters."""

import pytest

from xyberos import create_app
from xyberos.events import Event, EventBus, EventRecorder, LoggingExporter


class RecordingLogger:
    def __init__(self):
        self.messages = []

    def debug(self, message, *args, **kwargs):
        self.messages.append(message)


def test_event_recorder_records_and_counts_events():
    bus = EventBus()
    recorder = EventRecorder().subscribe_to(bus)

    bus.emit("a")
    bus.emit("b")
    bus.emit("a")

    assert [event.name for event in recorder.history] == ["a", "b", "a"]
    assert recorder.count == 3
    assert recorder.counts() == {"a": 2, "b": 1}
    assert recorder.count_for("a") == 2
    assert recorder.count_for("missing") == 0


def test_event_recorder_history_is_bounded_by_limit():
    recorder = EventRecorder(limit=2)
    recorder.record(Event(name="a"))
    recorder.record(Event(name="b"))
    recorder.record(Event(name="c"))

    assert [event.name for event in recorder.history] == ["b", "c"]
    assert recorder.count == 3  # counts are not bounded


def test_event_recorder_is_a_bus_listener_and_can_detach():
    bus = EventBus()
    recorder = EventRecorder()
    bus.subscribe_any(recorder)
    bus.emit("a")

    recorder.unsubscribe_from(bus)
    bus.emit("b")

    assert [event.name for event in recorder.history] == ["a"]


def test_event_recorder_forwards_to_exporters():
    exported = []
    recorder = EventRecorder(exporters=[lambda event: exported.append(event.name)])

    recorder.record(Event(name="a"))
    assert exported == ["a"]

    recorder.add_exporter(lambda event: exported.append("second"))
    recorder.record(Event(name="b"))
    assert exported == ["a", "b", "second"]


def test_event_recorder_clear_and_validation():
    recorder = EventRecorder()
    recorder.record(Event(name="a"))
    recorder.clear()

    assert recorder.count == 0
    assert recorder.history == ()

    with pytest.raises(ValueError, match="non-negative"):
        EventRecorder(limit=-1)
    with pytest.raises(TypeError, match="callable"):
        recorder.add_exporter(object())


def test_logging_exporter_writes_structured_lines():
    logger = RecordingLogger()
    exporter = LoggingExporter(logger)

    exporter.export(Event(name="x", context=None, data={"a": 1}))
    exporter(Event(name="y"))  # __call__ path

    assert logger.messages == ["event x data={'a': 1}", "event y"]


def test_logging_exporter_without_logger_is_a_noop():
    LoggingExporter().export(Event(name="z"))  # must not raise


def test_recorder_integration_with_default_app():
    app = create_app()
    recorder = EventRecorder().subscribe_to(app.events)

    app.chat("hello")
    app.chat("again")

    assert recorder.count_for("runtime.request_started") == 2
    assert recorder.count_for("runtime.request_completed") == 2
    assert recorder.count_for("brain.response_produced") == 2
    assert recorder.count_for("brain.memory_stored") == 2
    assert recorder.count_for("brain.error") == 0

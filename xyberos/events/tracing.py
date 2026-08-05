"""Tracing and observability hooks for the event bus.

``EventRecorder`` is a ready-made listener that records every event (with a
bounded history and per-name counts) and forwards each event to any attached
``Exporter`` callables — the extension point for metrics/tracing backends such
as Prometheus, OpenTelemetry, or JSON-lines files. ``LoggingExporter`` writes a
structured log line per event for human-readable tracing.

Example::

    from xyberos.events import EventRecorder, LoggingExporter

    recorder = EventRecorder(limit=1000).subscribe_to(app.events)
    recorder.add_exporter(LoggingExporter(app.logger))
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .bus import Event, EventBus

if TYPE_CHECKING:
    from ..kernel.logger import Logger


# A callable that consumes one event; implement this to push events into a
# metrics/tracing backend, a file, or any other sink.
Exporter = Callable[[Event], None]


class EventRecorder:
    """A listener that records every event for inspection and analysis.

    Attach it to an :class:`EventBus` with ``subscribe_to``. Each event is
    appended to ``history`` (bounded by ``limit``), counted by name, and
    forwarded to any configured exporters.
    """

    def __init__(
        self,
        limit: int | None = None,
        exporters: list[Exporter] | None = None,
    ) -> None:
        if limit is not None and limit < 0:
            raise ValueError("limit must be None or a non-negative integer")
        self._limit = limit
        self._history: list[Event] = []
        self._counts: Counter[str] = Counter()
        self._exporters = list(exporters or ())

    def __call__(self, event: Event) -> None:
        """Handle one event (callable so the recorder is a bus listener)."""
        self.record(event)

    def record(self, event: Event) -> None:
        """Record one event, update counts, and forward it to exporters."""
        self._history.append(event)
        if self._limit is not None:
            del self._history[: len(self._history) - self._limit]
        self._counts[event.name] += 1
        for exporter in self._exporters:
            exporter(event)

    def subscribe_to(self, bus: EventBus) -> "EventRecorder":
        """Attach this recorder to ``bus`` so it receives every event."""
        bus.subscribe_any(self)
        return self

    def unsubscribe_from(self, bus: EventBus) -> None:
        """Detach this recorder from ``bus``."""
        bus.unsubscribe_any(self)

    def add_exporter(self, exporter: Exporter) -> Exporter:
        """Register an exporter callable and return it unchanged."""
        if not callable(exporter):
            raise TypeError("exporter must be callable")
        self._exporters.append(exporter)
        return exporter

    @property
    def history(self) -> tuple[Event, ...]:
        """A snapshot of recorded events in order."""
        return tuple(self._history)

    @property
    def count(self) -> int:
        """Total number of events recorded."""
        return sum(self._counts.values())

    def counts(self) -> dict[str, int]:
        """Events recorded per name, useful for dashboards."""
        return dict(self._counts)

    def count_for(self, name: str) -> int:
        """Number of events recorded for ``name``."""
        return self._counts[name]

    def clear(self) -> None:
        """Forget all recorded events and counts."""
        self._history.clear()
        self._counts.clear()


class LoggingExporter:
    """Export every event as a structured log line.

    Sends each event to a logger at debug level by default, producing a
    human-readable event trace. Accepts the Xyberos :class:`~kernel.logger.Logger`
    or any object exposing ``debug(msg, *args, **kwargs)``.
    """

    def __init__(self, logger: Logger | Any | None = None) -> None:
        self._logger = logger

    def __call__(self, event: Event) -> None:
        """Handle one event (callable so the exporter is a valid ``Exporter``)."""
        self.export(event)

    def export(self, event: Event) -> None:
        """Write one event to the configured logger."""
        if self._logger is None:
            return
        detail = f" data={dict(event.data)!r}" if event.data else ""
        self._logger.debug(f"event {event.name}{detail}")

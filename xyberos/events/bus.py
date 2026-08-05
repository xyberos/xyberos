"""Event bus and listener infrastructure."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..kernel.logger import Logger


Listener = Callable[["Event"], None]


@dataclass(frozen=True)
class Event:
    """An immutable notification published to the event bus."""

    name: str
    context: object | None = None
    data: Mapping[str, Any] = field(default_factory=dict)


class EventBus:
    """A small publish/subscribe bus for lifecycle and pipeline events.

    Listeners are isolated: an exception raised by one listener is logged (when
    a logger is configured) and does not prevent other listeners or the caller
    from continuing. This keeps observability hooks from breaking the pipeline.
    """

    def __init__(self, logger: Logger | None = None) -> None:
        self._logger = logger
        self._listeners: dict[str, list[Listener]] = {}
        self._any: list[Listener] = []

    def subscribe(self, event: str, listener: Listener) -> Listener:
        """Register ``listener`` for ``event`` and return it unchanged."""
        if not isinstance(event, str) or not event.strip():
            raise ValueError("event name must be a non-empty string")
        if not callable(listener):
            raise TypeError("listener must be callable")
        self._listeners.setdefault(event, []).append(listener)
        return listener

    def subscribe_any(self, listener: Listener) -> Listener:
        """Register ``listener`` to receive every published event."""
        if not callable(listener):
            raise TypeError("listener must be callable")
        self._any.append(listener)
        return listener

    def unsubscribe(self, event: str, listener: Listener) -> None:
        """Remove a previously registered ``listener`` for ``event``."""
        listeners = self._listeners.get(event)
        if listeners is not None and listener in listeners:
            listeners.remove(listener)

    def unsubscribe_any(self, listener: Listener) -> None:
        """Remove a previously registered wildcard ``listener``."""
        if listener in self._any:
            self._any.remove(listener)

    def publish(self, event: Event) -> None:
        """Deliver ``event`` to every matching listener."""
        listeners = [*self._any, *self._listeners.get(event.name, ())]
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:  # noqa: BLE001 - isolate listener failures
                if self._logger is not None:
                    self._logger.error(f"Event listener failed for '{event.name}': {exc}")

    def emit(self, name: str, context: object | None = None, **data: Any) -> None:
        """Build and publish an event named ``name`` with optional context/data."""
        self.publish(Event(name=name, context=context, data=data))

    def has_listeners(self, event: str) -> bool:
        """Whether any listener would receive ``event``."""
        return bool(self._any) or bool(self._listeners.get(event))

    def clear(self) -> None:
        """Remove all registered listeners."""
        self._listeners.clear()
        self._any.clear()

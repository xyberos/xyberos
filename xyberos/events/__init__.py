"""Event bus and event-handler infrastructure.

Subscribe to pipeline and lifecycle events to observe or extend Xyberos::

    from xyberos.events import RESPONSE_PRODUCED

    def on_response(event):
        print(event.context.prompt, "->", event.data.get("response"))

    app.events.subscribe(RESPONSE_PRODUCED, on_response)
"""

from .bus import Event, EventBus
from .names import (
    BRAIN_ERROR,
    KERNEL_STARTED,
    KERNEL_STOPPED,
    KNOWLEDGE_QUERIED,
    MEMORY_RETRIEVED,
    MEMORY_STORED,
    PLAN_CREATED,
    PLUGIN_LOADED,
    PLUGIN_UNLOADED,
    REQUEST_COMPLETED,
    REQUEST_FAILED,
    REQUEST_STARTED,
    RESPONSE_PRODUCED,
    TOOL_DISPATCHED,
    WORKFLOW_RUN,
)
from .tracing import EventRecorder, Exporter, LoggingExporter

__all__ = [
    "BRAIN_ERROR",
    "Event",
    "EventBus",
    "EventRecorder",
    "Exporter",
    "KERNEL_STARTED",
    "KERNEL_STOPPED",
    "KNOWLEDGE_QUERIED",
    "LoggingExporter",
    "MEMORY_RETRIEVED",
    "MEMORY_STORED",
    "PLAN_CREATED",
    "PLUGIN_LOADED",
    "PLUGIN_UNLOADED",
    "REQUEST_COMPLETED",
    "REQUEST_FAILED",
    "REQUEST_STARTED",
    "RESPONSE_PRODUCED",
    "TOOL_DISPATCHED",
    "WORKFLOW_RUN",
]

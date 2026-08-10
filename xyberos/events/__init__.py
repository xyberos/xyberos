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
    CACHE_HIT,
    DEGRADED,
    ENGINE_REFRESHED,
    ENGINE_TRAINED,
    EPISODE_RECORDED,
    ESCALATED,
    FEEDBACK_RECORDED,
    INTENT_CLASSIFIED,
    KERNEL_STARTED,
    KERNEL_STOPPED,
    KNOWLEDGE_QUERIED,
    MEMORY_RETRIEVED,
    MEMORY_STORED,
    PLAN_CREATED,
    PLAN_REPLANNED,
    PLAN_STEP_EXECUTED,
    PLAN_STEP_FAILED,
    PLUGIN_LOADED,
    PLUGIN_UNLOADED,
    REQUEST_COMPLETED,
    REQUEST_FAILED,
    REQUEST_STARTED,
    RESPONDER_HIT,
    RESPONSE_PRODUCED,
    SECURITY_GUARDRAIL_TRIGGERED,
    SECURITY_KILL_DISENGAGED,
    SECURITY_KILL_ENGAGED,
    SECURITY_REQUEST_BLOCKED,
    TOKEN_STREAMED,
    TOOL_DISPATCHED,
    WORKFLOW_RUN,
)
from .tracing import EventRecorder, Exporter, LoggingExporter

__all__ = [
    "BRAIN_ERROR",
    "CACHE_HIT",
    "DEGRADED",
    "ENGINE_REFRESHED",
    "ENGINE_TRAINED",
    "EPISODE_RECORDED",
    "ESCALATED",
    "Event",
    "EventBus",
    "EventRecorder",
    "Exporter",
    "FEEDBACK_RECORDED",
    "INTENT_CLASSIFIED",
    "KERNEL_STARTED",
    "KERNEL_STOPPED",
    "KNOWLEDGE_QUERIED",
    "LoggingExporter",
    "MEMORY_RETRIEVED",
    "MEMORY_STORED",
    "PLAN_CREATED",
    "PLAN_REPLANNED",
    "PLAN_STEP_EXECUTED",
    "PLAN_STEP_FAILED",
    "PLUGIN_LOADED",
    "PLUGIN_UNLOADED",
    "REQUEST_COMPLETED",
    "REQUEST_FAILED",
    "REQUEST_STARTED",
    "RESPONDER_HIT",
    "RESPONSE_PRODUCED",
    "SECURITY_GUARDRAIL_TRIGGERED",
    "SECURITY_KILL_DISENGAGED",
    "SECURITY_KILL_ENGAGED",
    "SECURITY_REQUEST_BLOCKED",
    "TOKEN_STREAMED",
    "TOOL_DISPATCHED",
    "WORKFLOW_RUN",
]

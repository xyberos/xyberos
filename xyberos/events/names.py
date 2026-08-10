"""Canonical event names emitted by the core pipeline.

These constants are the stable public names for the events published by the
kernel, plugin loader, runtime, and brain. Applications subscribe to them via
``EventBus.subscribe`` (imported as ``xyberos.events``).
"""

# Kernel / plugin lifecycle
KERNEL_STARTED = "kernel.started"
KERNEL_STOPPED = "kernel.stopped"
PLUGIN_LOADED = "plugin.loaded"
PLUGIN_UNLOADED = "plugin.unloaded"

# Runtime request lifecycle
REQUEST_STARTED = "runtime.request_started"
REQUEST_COMPLETED = "runtime.request_completed"
REQUEST_FAILED = "runtime.request_failed"

# Brain pipeline steps
WORKFLOW_RUN = "brain.workflow_run"
MEMORY_RETRIEVED = "brain.memory_retrieved"
MEMORY_STORED = "brain.memory_stored"
KNOWLEDGE_QUERIED = "brain.knowledge_queried"
PLAN_CREATED = "brain.plan_created"
PLAN_STEP_EXECUTED = "brain.plan_step_executed"
PLAN_STEP_FAILED = "brain.plan_step_failed"
PLAN_REPLANNED = "brain.plan_replanned"
TOOL_DISPATCHED = "brain.tool_dispatched"
RESPONSE_PRODUCED = "brain.response_produced"
TOKEN_STREAMED = "brain.token_streamed"
BRAIN_ERROR = "brain.error"

# Trainable-engine events (RFC-0016, Phase 0)
INTENT_CLASSIFIED = "brain.intent_classified"
EPISODE_RECORDED = "brain.episode_recorded"
FEEDBACK_RECORDED = "brain.feedback_recorded"
ENGINE_TRAINED = "engine.trained"
ENGINE_REFRESHED = "engine.refreshed"

# Hybrid-router events (RFC-0017)
RESPONDER_HIT = "brain.responder_hit"
ESCALATED = "brain.escalated"
DEGRADED = "brain.degraded"
CACHE_HIT = "brain.cache_hit"

# Security lifecycle
SECURITY_KILL_ENGAGED = "security.kill_engaged"
SECURITY_KILL_DISENGAGED = "security.kill_disengaged"
SECURITY_REQUEST_BLOCKED = "security.request_blocked"
SECURITY_GUARDRAIL_TRIGGERED = "security.guardrail_triggered"

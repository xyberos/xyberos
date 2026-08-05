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
TOOL_DISPATCHED = "brain.tool_dispatched"
RESPONSE_PRODUCED = "brain.response_produced"
BRAIN_ERROR = "brain.error"

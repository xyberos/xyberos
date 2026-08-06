RFC-0015 — Security

Title: Security Service and Kill Switch

Status: Accepted

Summary

Defines the Security subsystem — a Kernel-level service providing a kill switch,
content guardrails, and audit logging that gates every request through the
Runtime and Brain pipelines.

Motivation

AI systems in production need safety controls: the ability to halt all
processing immediately (kill switch), filter harmful prompts/responses
(guardrails), and maintain an audit trail of security events. These are
cross-cutting concerns that belong in the Kernel, not in individual agents or
tools.

Architecture

```
Kernel
├── Config
├── Logger
├── Registry
├── EventBus
├── PluginManager
└── Security           ← new
    ├── KillSwitch     (active/inactive gate)
    ├── Guardrail      (content filter pipeline)
    └── AuditLog       (security event history)
```

Design Principles

- **Fail-closed**: when the kill switch is active, ALL requests are rejected
- **Cross-cutting**: security checks happen in the Runtime and Brain, not in
  individual agents or tools
- **Observable**: every security action emits events through the EventBus
- **Recoverable**: the kill switch requires explicit re-enable; it never
  auto-recovers
- **Graceful**: in-flight requests may complete or abort with
  ``SecurityHaltError`` depending on the switch mode

Kill Switch

```python
class KillSwitch:
    active: bool          # False = normal, True = all requests halted
    mode: str             # "hard" (abort in-flight) or "soft" (reject new)
    reason: str | None    # human-readable reason for the kill
    activated_at: float   # timestamp of activation

    def engage(self, reason: str = "") -> None: ...
    def disengage(self) -> None: ...
```

States:

| State | New Requests | In-Flight Requests |
|---|---|---|
| ``active=False`` | Accepted | Run normally |
| ``active=True, mode="soft"`` | Rejected | Complete normally |
| ``active=True, mode="hard"`` | Rejected | Aborted with ``SecurityHaltError`` |

Guardrails

A chain of callables that inspect prompts (and optionally responses) before and
after the Brain pipeline:

- Content filters (block patterns, keywords)
- Prompt injection detectors
- Response sanitizers

Audit Log

Records every security event (kill engaged, kill disengaged, request blocked,
guardrail triggered) with timestamp, context, and reason.

Pipeline Integration

### Runtime checks (every request)

```python
def run(self, context):
    if self.security is not None:
        self.security.guard(context)           # run guardrails
        self.security.kill_switch.check()       # raise if active
    # ... normal execution
```

### Brain checks (every pipeline step)

Before each pipeline stage (workflow, memory, knowledge, plans, tools, LLM),
the Brain checks the kill switch. In "soft" mode this only affects new requests
entering the Brain; in "hard" mode it aborts mid-pipeline.

Events

| Event | When |
|---|---|
| ``security.kill_engaged`` | Kill switch activated |
| ``security.kill_disengaged`` | Kill switch deactivated |
| ``security.request_blocked`` | A request was rejected by guardrails or kill switch |
| ``security.guardrail_triggered`` | A content guardrail matched |

Future Directions

- Per-user / per-session kill switches
- Role-based access control (RBAC)
- Token usage quotas and cost limits
- External security provider integration (API gateways, WAF)

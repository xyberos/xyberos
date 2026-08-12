# 15. Security

[**← Previous**](14-observability.md) · [**Next →**](16-testing.md)

## What You'll Learn

- The security model
- The kill switch
- Content guardrails
- Audit logging
- Tool / plugin permissions
- Secrets management
- Prompt injection & tool abuse

---

## The security model

Xyberos gates every request through a **Security** layer at the Runtime and
Brain boundaries. It provides three mechanisms:

- **Kill switch** — halt all processing instantly.
- **Guardrails** — block harmful prompts.
- **Audit log** — record every security event.

## The kill switch

Halt the whole system in an emergency — for example, a robotics controller's
literal emergency stop:

```python
from xyberos import create_app

app = create_app()
app.security.engage_kill_switch("emergency maintenance")
app.chat("hello")            # raises SecurityHaltError
app.security.disengage_kill_switch()
app.chat("hello")            # works again
```

Kill modes:

- **soft** (default) — new requests rejected; in-flight requests complete.
- **hard** — all requests rejected, including in-flight.

```python
app.security.engage_kill_switch("halt", mode="hard")
```

The switch never auto-recovers — it must be explicitly disengaged.

## Content guardrails

Guardrails inspect every context and block requests that fail:

```python
from xyberos import Guardrail, create_app

app = create_app()
app.security.add_guardrail(
    Guardrail("no-hacks", lambda ctx: "hack" not in ctx.prompt)
)
```

A guardrail's check receives the `CognitiveContext` and should raise
`GuardrailTriggeredError` (or return `False`) to block the request.

## Audit logging

Every security event — kill engagements, guardrail triggers, blocked requests —
is recorded in the audit store:

```python
app = create_app(config={"security.audit_path": "audit.db"})
app.security.engage_kill_switch("maintenance")   # recorded to audit.db

print(app.security.audit_log())   # tuple of recorded entries
```

The default is an in-memory store; `security.audit_path` switches to a
persistent SQLite audit trail that survives restarts.

## Tool / plugin permissions

Permissions are the security layer around capabilities. Combine guardrails,
the kill switch, and the audit log to gate what the assistant can do:

```python
app.security.add_guardrail(
    Guardrail("no-destructive", lambda ctx: "rm -rf" not in ctx.prompt)
)
```

## Secrets management

Keep secrets in the environment, never in code or config:

```python
import os
from xyberos.llm import OpenAILLM

llm = OpenAILLM(api_key=os.environ["OPENAI_API_KEY"])
```

## Prompt injection & tool abuse

- **Prompt injection** — treat the prompt as untrusted input; use guardrails
  to block instructions that try to override system behavior.
- **Tool abuse** — gate destructive tools with guardrails, and use the audit
  log to review what tools were invoked.

## Default behavior

- `create_app()` wires a `Security` with an in-memory audit store.
- The kill switch is **off** by default; no guardrails are registered.
- The Runtime and Brain check the kill switch at every gating point.

## Common mistakes

- **Forgetting to disengage the kill switch** — it never auto-recovers.
- **Relying only on the kill switch** — use guardrails for content, the audit
  log for accountability.
- **Storing secrets in config** — environment variables + provider `api_key=`
  is the pattern.

## Next Step

[**16. Testing**](16-testing.md) — make sure your assistant works.

# 13. Configuration

[**← Previous**](12-agents.md) · [**Next →**](14-observability.md)

## What You'll Learn

- Configuration basics
- Default configuration
- Configuration at construction time
- Runtime configuration
- Configuration precedence
- Secrets
- Three ways to wire services (recap)

---

## Configuration basics

Xyberos uses a simple dotted-key config mapping. `create_app(config={...})`
accepts it, and `app.config` exposes it:

```python
from xyberos import create_app

app = create_app(config={
    "brain.inject_plan": True,
    "brain.max_attempts": 3,
    "brain.retry_backoff": 0.5,
    "brain.rate_limit": 10.0,
    "brain.timeout": 30,
    "brain.intent": True,
    "experience.enabled": True,
    "security.audit_path": "audit.db",
})
```

## Default configuration

The defaults are chosen for a zero-setup experience:

| Key | Default | Meaning |
|---|---|---|
| `brain.inject_plan` | `False` | feed the plan to the model prompt |
| `brain.intent` | `False` | classify intent before planning |
| `brain.max_attempts` | `1` | LLM retry attempts on failure |
| `brain.retry_backoff` | `0.1` | exponential backoff base |
| `brain.rate_limit` | `0.0` | max LLM calls/second (`0` = off) |
| `brain.timeout` | `0.0` | seconds per LLM call (`0` = off) |
| `experience.enabled` | `False` | record an episode per turn |

## Runtime configuration

Read and write config at runtime:

```python
app.config.get("brain.intent", False)     # -> False
app.config.set("brain.intent", True)
app.config.update({"brain.timeout": 60})
app.config.as_dict()                      # full snapshot
```

> **Note:** the `Brain` reads its config once at construction. Changing
> `brain.*` keys at runtime affects new providers/apps, but an already-built
> brain keeps its captured settings. Build a fresh app (or use factories +
> plugins) to apply new brain config.

## Configuration precedence

```text
Defaults
   ↓
Config passed to create_app()
   ↓
Runtime changes via app.config
```

## Secrets

Keep secrets out of config and out of code — read them from the environment:

```python
import os
from xyberos import create_app
from xyberos.llm import OpenAILLM

app = create_app(llm=OpenAILLM(api_key=os.environ["OPENAI_API_KEY"]))
```

The `security.audit_path` key writes security events to a SQLite audit log;
guard the file as sensitive.

## Three ways to wire services

1. **Explicit** — pass instances to `create_app()`:

   ```python
   app = create_app(
       llm=CallableLLM(lambda p: f"response: {p}"),
       knowledge=InMemoryKnowledge({"hours": "9am-6pm"}),
   )
   ```

2. **Factory / DI** — register a factory; dependencies resolve by parameter
   name:

   ```python
   app = create_app(config={"llm_provider": "openai"})
   app.register_factory("llm", build_llm, replace=True)
   ```

3. **Plugin** — package services and auto-discover them (see
   [9. Skills & Plugins](09-plugins.md)).

> Full detail and pros/cons: [Configuring Services](18-configuring-services.md).

## Default behavior

- `create_app()` fills in in-memory defaults for anything you omit.
- Config is a plain mutable mapping — no schema enforcement.

## Common mistakes

- **Trying to hot-swap brain config** — the brain captures config at
  construction; rebuild for changes.
- **Storing secrets in `config`** — use environment variables and pass
  `api_key=` to providers.
- **Forgetting `security.audit_path` for production** — audit events are
  in-memory by default; set a path to persist them.

## Next Step

[**14. Observability & Debugging**](14-observability.md) — log, trace, and
troubleshoot.

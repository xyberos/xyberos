# 12. Multi-Agent Systems

[**← Previous**](11-context.md) · [**Next →**](13-configuration.md)

## What You'll Learn

- What a multi-agent system is
- Create multiple agents
- Agent-to-agent communication
- Handoffs & delegation
- Roles
- The message board / audit trail

---

## What is a multi-agent system?

A **multi-agent system** is a team of named participants that each transform a
shared context, and can hand work to one another. Use it for delegation,
triage, and role-based collaboration:

```text
Manager
 ├── Researcher
 ├── Developer
 ├── Writer
 └── Reviewer
```

## Create agents

Xyberos ships a `MultiAgentRuntime` with a default agent. Register more with
`RoleAgent`, which carries a name, a role, and run/receive handlers:

```python
from xyberos import create_app
from xyberos.agents import RoleAgent, handoff, post

def supervisor_run(context):
    post(context, handoff("support_worker", sender="supervisor"))
    return context

def worker_run(context):
    context.response = f"Escalated: a human agent will follow up on '{context.prompt}'."
    return context

app = create_app()
app.register_agent(RoleAgent("supervisor", "triage", run=supervisor_run))
app.register_agent(RoleAgent("support_worker", "resolver", run=worker_run))
```

## Run agents

```python
result = app.run_agents("I need a human", agent_names=["supervisor", "support_worker"])
print(result.response)   # Escalated: a human agent will follow up on 'I need a human'.
```

`run_agents` runs all (or a selected subset of) registered agents over a fresh
context. Each agent runs at most once per call; a `handoff` message runs its
recipient next.

## Agent-to-agent communication

Agents collaborate with `Message` (via `post`) and `handoff`:

```python
from xyberos.agents import Message, handoff, post
from xyberos.runtime.context import CognitiveContext

# queue a message for the runtime
post(context, Message(sender="boss", recipient="worker", content="do the task"))

# or build a handoff (transfers control to the recipient)
post(context, handoff("worker", sender="boss"))
```

- `recipient="*"` broadcasts.
- `kind == "handoff"` transfers control to the recipient.
- Agents that implement `receive(message)` get inbound messages.

The whole exchange is recorded on `app.agents.messages`, so you get a full
audit trail.

## Roles

`RoleAgent` adds a role to each agent — useful for supervising and organizing
teams:

```python
app.register_agent(RoleAgent("boss", "supervisor", run=ask))
app.register_agent(RoleAgent("worker", "performer", run=work_step, receive=on_message))
app.run_agents("task", agent_names=["boss", "worker"])
```

## Agent workflows

For a fixed pipeline of agents, register them and run them in order with
`agent_names`. For branching/looping collaboration, combine agents with
workflows (see [8. Plans & Workflows](08-workflows.md)).

## Custom agent roles

Agents are **contracts** — implement `Agent` (or subclass `RuntimeAgent`) to
create your own:

```python
from xyberos.contracts.agent import Agent

class MyAgent(Agent):
    @property
    def name(self):
        return "my_agent"

    def run(self, context):
        context.response = "handled"
        return context

app.register_agent(MyAgent())
```

## Default behavior

- `create_app()` builds a `MultiAgentRuntime` with one default agent
  (`RuntimeAgent("default", runtime)`).
- `run_agents(prompt)` runs all registered agents by default; pass
  `agent_names` to select.

## Common mistakes

- **Forgetting to `post` a handoff** — a supervisor that doesn't hand off
  simply ends; delegation requires a `handoff` message.
- **Expecting parallel execution** — agents run sequentially over one shared
  context (each at most once per run).
- **Ignoring the message board** — `app.agents.messages` is your audit trail;
  use it for debugging and observability.

## Next Step

[**13. Configuration**](13-configuration.md) — master defaults, precedence,
and secrets.

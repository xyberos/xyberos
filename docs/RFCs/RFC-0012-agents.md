RFC-0012 — Agents

Title: Multi-Agent Coordination

Status: Accepted

Summary

Defines the Agents subsystem — a multi-agent runtime with messaging, handoffs,
and role-based coordination that allows multiple cognitive participants to
collaborate on a single request.

Motivation

Complex tasks benefit from specialized agents: a triage agent classifies, a
support agent resolves, a supervisor delegates. Rather than one monolithic
prompt, agents can message each other, hand off control, and share a context.

Contract

```python
class Agent(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        """A stable, unique agent identifier."""

    @abstractmethod
    def run(self, context: object) -> object:
        """Process and return an execution context."""
```

Architecture

### MultiAgentRuntime

Sequentially runs agents against one canonical ``CognitiveContext``, with
messaging and handoff support:

```python
runtime = MultiAgentRuntime([agent1, agent2], max_handoffs=100)
runtime.run(context, agent_names=["supervisor", "worker"])
```

- Agents execute in registration (or selected) order
- Messages are queued via ``post(context, message)`` and delivered after each
  agent runs
- Handoffs chain execution: ``handoff("worker")`` makes the worker run next
- ``max_handoffs`` bounds runaway chains (``HandoffLoopError``)

### Messages

```python
@dataclass
class Message:
    sender: str
    recipient: str      # agent name or "*" for broadcast
    content: str
    kind: str           # "handoff", "info", etc.
    metadata: dict
```

### RoleAgent

An agent with a named role for intent-based coordination:

```python
agent = RoleAgent("supervisor", "triage", run=supervisor_fn)
agent = RoleAgent("support_worker", "resolver", run=worker_fn)
```

### RuntimeAgent

Wraps the core Xyberos Runtime as an agent so the default cognitive pipeline
participates in multi-agent runs.

Facade Integration

```python
app.register_agent(RoleAgent("supervisor", "triage", run=fn))
app.run_agents("escalate this", agent_names=["supervisor", "worker"])
```

Future Directions

- Async agent collaboration
- Agent-to-agent conversation state
- Dedicated supervisor/re-planning loop

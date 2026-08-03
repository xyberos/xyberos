# Xyberos

An experimental cognitive framework for building AI systems.

## Architecture

```
Kernel   ->  platform services (config, logging, registry, lifecycle, plugins)
Runtime  ->  cognitive execution
Brain    ->  reasoning and inference
LLM      ->  provider abstraction
```

See the `xyberos/docs/RFCs/` directory for the architecture specifications.

## Features

- Layered core: `Kernel` -> `Runtime` -> `Brain` -> `LLM`
- Service registry with constructor dependency injection and lifecycle management
- Extension contracts: Agent, Tool, Memory, Planner, Knowledge, Workflow, Plugin, Service, LLMProvider
- Sequential workflow engine
- Multi-agent runtime with a default agent adapter
- Plugin loader (import and lifecycle)
- Typed exception hierarchy

## Install

```bash
pip install -e .
```

## Usage

```python
from xyberos import create_app
from xyberos.brain.llm import CallableLLM

# Defaults to EchoLLM (suitable for development and tests)
app = create_app()
print(app.chat("hello"))  # -> "hello"

# Provide your own model
app = create_app(llm=CallableLLM(lambda prompt: f"handled: {prompt}"))
print(app.chat("hi"))     # -> "handled: hi"
```

## Status

Current Version: v0.9.0

Implemented:

✓ Kernel / Service Registry / Dependency Injection / Lifecycle
✓ Runtime & Cognitive Context
✓ Brain & LLM abstraction
✓ Contracts (Agent, Tool, Memory, Planner, Knowledge, Workflow, Plugin, Service)
✓ Workflow engine
✓ Plugin system
✓ Multi-agent runtime

58 tests passing
98% coverage
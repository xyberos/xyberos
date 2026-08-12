# 3. Hello Assistant

[**← Previous**](02-getting-started.md) · [**Next →**](04-name-and-personality.md)

## What You'll Learn

- Create an assistant
- Send a message
- Receive a response
- The conversation loop
- Streaming responses
- Async usage
- Error handling

---

## Create an assistant

```python
from xyberos import create_app

assistant = create_app()
```

## Send a message & receive a response

```python
print(assistant.chat("Hello!"))   # -> Hello!
```

`chat()` returns only the text. If you want the full request/response state:

```python
ctx = assistant.run("Hello!")
print(ctx.prompt)      # the input
print(ctx.response)    # the model's reply
print(ctx.succeeded)   # True when there was no error
```

## Conversation loop

```python
from xyberos import create_app

app = create_app()
while True:
    message = input("> ")
    if message.lower() in ("quit", "exit"):
        break
    print(app.chat(message))
```

Memory is wired in by default (in-memory), so the assistant sees prior turns
within a session.

## Streaming responses

Streaming in Xyberos is **event-driven**. Attach a subscriber for
`brain.token_streamed` and tokens arrive as they're generated:

```python
from xyberos import create_app
from xyberos.events import TOKEN_STREAMED
from xyberos.llm import StreamingLLM, CallableLLM

app = create_app(llm=StreamingLLM(
    generate=lambda prompt: prompt.upper(),
    stream=lambda prompt, on_token: [on_token(t) for t in prompt.split()],
))

app.events.subscribe(TOKEN_STREAMED, lambda e: print(e.data["token"], end=" "))
app.chat("write a haiku about code")
```

The `Brain` emits one `brain.token_streamed` event per token whenever the model
supports streaming.

## Async usage

The app exposes async variants that mirror the sync API:

```python
import asyncio
from xyberos import create_app

async def main():
    app = create_app()
    print(await app.achat("Hello!"))   # returns just the text
    ctx = await app.arun("Hello!")     # returns the full context

asyncio.run(main())
```

Async-only providers (via `AsyncLLM`) work with `achat`/`arun`; using one from
the synchronous API raises a clear `TypeError`.

## Error handling

Use `run()` and check the context rather than relying on exceptions for
expected failures:

```python
ctx = app.run("hello")
if not ctx.succeeded:
    print("something went wrong:", ctx.error)
```

Domain exceptions are typed in `xyberos.exceptions`:

```python
from xyberos.exceptions import SecurityHaltError, WorkflowPaused
```

- `SecurityHaltError` — raised when the kill switch is engaged.
- `WorkflowPaused` — raised by workflows that pause for human input.
- `ToolArgumentError` — a tool was called with invalid arguments.
- `ProviderError` — a provider/backend issue (e.g. missing SDK).
- `StructuredOutputError` — structured LLM output failed to parse.

## Default behavior

- `create_app()` builds an assistant that echoes your prompt (no model needed).
- Memory is in-memory by default; the conversation is remembered within the
  process but not across restarts.
- `chat()` raises `RuntimeError` if the pipeline produced no response.

## Alternative

- **One-shot helpers** — `chat()` / `achat()` at package level build a default
  app, run, and return text in one line:

  ```python
  from xyberos import chat
  print(chat("Hello!"))
  ```

- **`Xyberos()` directly** — full control, no defaults injected:

  ```python
  from xyberos import Xyberos
  app = Xyberos()
  ```

## Common mistakes

- **Using `run()` and expecting a string** — `run()` returns a
  `CognitiveContext`; use `.response` or `chat()` for the text.
- **Forgetting async/sync separation** — `achat`/`arun` are for the async
  pipeline; don't mix `AsyncLLM` into the sync path.
- **Not checking `succeeded`** — when robustness matters, check `ctx.succeeded`
  instead of assuming `response` is set.

## Next Step

[**4. Give It a Name & Personality**](04-name-and-personality.md) — make your
assistant yours.

# Hello World to Full Stack

One runnable script that grows a Xyberos app from a one-liner into a small
full-stack support assistant. Every stage builds on the previous one and prints
its own output, so you can watch the framework come together.

## Run it

```bash
python examples/hello_world_to_full_stack/app.py
```

No setup beyond the package install (`pip install -e .`) is required.

## What you'll see

| Stage | Topic |
|-------|-------|
| 0 | Hello world with `create_app()` / `chat()` |
| 1 | Swapping in a custom model (`CallableLLM`) |
| 2 | Configuration, services, factories, dependency injection |
| 3 | Memory provider |
| 4 | Knowledge provider |
| 5 | Tools |
| 6 | Tool runner (name-based dispatch) |
| 7 | Workflow |
| 8 | Agents |
| 9 | Plugins |
| 10 | Everything together — a support assistant |

## Reading along

- The [full tutorial](../../docs/learn/23-customer-support-tutorial.md) covers the same ground step by step.
- The [API reference](../../docs/api-reference.md) lists each class, what it owns,
  and when to use it.
- `minimal_chat.py` and `extended_app.py` in `../` are shorter, focused examples.

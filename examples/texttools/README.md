# Texttools

Text utility tools (count words, slugify, echo) for agents — an example Xyberos
**Tool** plugin that also serves as this repository's CI validation target.

A Xyberos plugin of type **Tool**, generated with
[`xyberos plugin create`](https://github.com/xyberos/xyberos/blob/main/docs/plugin-contribution.md)
and then implemented.

## What it integrates with

plain text strings (no external services, no dependencies)

## Contributed tools

| Tool          | Arguments | Result                      |
| ------------- | --------- | --------------------------- |
| `count_words` | `text`    | `{"text": ..., "words": N}` |
| `slugify`     | `text`    | `{"slug": "url-safe-slug"}` |
| `echo`        | `text`    | `{"echo": "<text>"}`        |

## Install (development)

From the repository root, install the core + plugin tooling, then this plugin
(the plugin tooling packages are not on PyPI yet, so install them from the
checkout):

```bash
pip install -e ./ -e ./xyberos_plugin_sdk -e ./xyberos_plugin_validator -e ./xyberos_cli
pip install -e ./examples/texttools
```

## Use

```python
from xyberos import create_app

app = create_app()
app.load_entry_points()   # auto-discovers the xyberos.plugins entry point

registry = app.resolve("tools")
print(registry.execute("slugify", None, text="Hello, World! 42"))
# -> {"slug": "hello-world-42"}
```

## Validate

```bash
xyberos plugin validate .            # static + live-kernel checks
xyberos plugin validate . --run-tests
```

## Test

```bash
python -m pytest
```

## Contribution pipeline

`CREATE -> IMPLEMENT -> TEST -> VALIDATE -> DOCUMENT -> PACKAGE -> PULL REQUEST`
(see `plugin-contribution.md`).

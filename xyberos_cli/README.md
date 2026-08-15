# xyberos-cli

The Xyberos plugin developer command line — makes plugin contribution
one-command (see [`plugin-contribution.md`](https://github.com/xyberos/xyberos/blob/main/docs/plugin-contribution.md)).

## Install

```bash
pip install xyberos-cli
```

## Commands

```bash
# Scaffold a new plugin (interactive wizard)
xyberos plugin create

# Scaffold non-interactively
xyberos plugin create --name github --type tool --description "GitHub API integration" \
    --integrate-with "GitHub REST API" --auth token --non-interactive

# Validate a plugin package (static + live-kernel subprocess check)
xyberos plugin validate .

# Auto-repair missing contract stubs
xyberos plugin repair . --check
xyberos plugin repair .

# Repair-then-validate
xyberos plugin validate . --fix
```

## What it generates

`xyberos plugin create` scaffolds: `pyproject.toml` (with the
`xyberos.plugins` entry point), `README.md`, the plugin package
(`__init__`, `config`, `service`, `plugin`), `tests/test_plugin.py`, and
`examples/example.py`. The `service` class is derived from the chosen
contract by introspection, so the skeleton always matches the current
contracts (the "one rule").

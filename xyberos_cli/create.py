"""Plugin scaffold generator (``plugin-contribution.md`` CLI milestone #4).

Runs ``xyberos plugin create``: asks a few questions (or accepts flags), then
emits a validated, tested, packaged plugin skeleton whose *service* class is
derived from the chosen contract by introspection (the "one rule").
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from string import Template
from typing import Any

from xyberos_plugin_sdk.introspect import CONTRACTS, abstract_members, render_stub

__all__ = ["run_create"]

#: Per-type generation info. ``plural`` marks a contribution that returns a list.
TYPE_INFO: dict[str, dict[str, Any]] = {
    "tool": {
        "contract": "Tool", "base": "ToolPlugin", "method": "tools",
        "return": "list[Tool]", "label": "Tool", "plural": True,
    },
    "llm": {
        "contract": "LLMProvider", "base": "LLMPlugin", "method": "llm",
        "return": "LLMProvider", "label": "LLM Provider", "plural": False,
    },
    "memory": {
        "contract": "Memory", "base": "MemoryPlugin", "method": "memory",
        "return": "MemoryProvider", "label": "Memory", "plural": False,
    },
    "knowledge": {
        "contract": "Knowledge", "base": "KnowledgePlugin", "method": "knowledge",
        "return": "KnowledgeProvider", "label": "Knowledge", "plural": False,
    },
    "vector": {
        "contract": "VectorStore", "base": "VectorPlugin", "method": "vector_store",
        "return": "VectorStore", "label": "Vector Store", "plural": False,
    },
    "workflow": {
        "contract": "Workflow", "base": "WorkflowPlugin", "method": "workflow",
        "return": "Workflow", "label": "Workflow", "plural": False,
    },
    "planner": {
        "contract": "Planner", "base": "PlannerPlugin", "method": "planner",
        "return": "Planner", "label": "Planner", "plural": False,
    },
    "agent": {
        "contract": "Agent", "base": "AgentPlugin", "method": "agent",
        "return": "Agent", "label": "Agent", "plural": False,
    },
    "service": {
        "contract": "Service", "base": "ServicePlugin", "method": "service",
        "return": "Service", "label": "Service", "plural": False,
    },
    "other": {
        "contract": "Plugin", "base": None, "method": None,
        "return": None, "label": "Other", "plural": False,
    },
}


def _sanitize_package(name: str) -> str:
    return re.sub(r"\W", "_", name.lower()).strip("_") or "plugin"


def _to_pascal(name: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[\W_]+", name)) or "Plugin"


def _env_prefix(name: str) -> str:
    return re.sub(r"\W", "_", name).upper()


# --------------------------------------------------------------------------- #
# Templates
# --------------------------------------------------------------------------- #

_PYPROJECT = Template(
    """[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "$dist_name"
version = "0.1.0"
description = "$description"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "Apache-2.0"}
dependencies = ["xyberos>=1.0", "xyberos-plugin-sdk>=0.1"]

[project.entry-points."xyberos.plugins"]
$name = "$pkg.plugin:plugin"

[tool.setuptools]
packages = ["$pkg"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
"""
)

_README = Template(
    """# $Name

$description

A Xyberos plugin of type **$label**, generated with
[`xyberos plugin create`](https://github.com/xyberos/xyberos/blob/main/docs/plugin-contribution.md).

## What it integrates with

$integrate_with

## Install (development)

```bash
pip install -e .
```

## Use

```python
from xyberos import create_app

app = create_app()
app.load_entry_points()   # auto-discovers the xyberos.plugins entry point
```

## Validate

```bash
pip install xyberos-cli
xyberos plugin validate .
```

## Contribution pipeline

`CREATE -> IMPLEMENT -> TEST -> VALIDATE -> DOCUMENT -> PACKAGE -> PULL REQUEST`
(see `plugin-contribution.md`).
"""
)

_INIT = Template(
    """\"\"\"$Name — a Xyberos $label plugin.\"\"\"

from .plugin import plugin

__all__ = ["plugin"]
"""
)

_CONFIG = Template(
    """\"\"\"Configuration and authentication for the $name integration.\"\"\"

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Config:
    \"\"\"Runtime configuration for the $name integration.\"\"\"

    auth_token: str | None = None
    base_url: str = "$base_url"
    timeout: float = 30.0
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "Config":
        \"\"\"Build a Config from ${prefix}_* environment variables.\"\"\"
        prefix = "$prefix"
        return cls(
            auth_token=os.getenv(f"{prefix}_TOKEN") or os.getenv(f"{prefix}_API_KEY"),
            base_url=os.getenv(f"{prefix}_BASE_URL", cls.base_url),
        )
"""
)

_SERVICE_TOOL = Template(
    """\"\"\"A $Name tool for Xyberos.\"\"\"

from __future__ import annotations

from typing import Any

from xyberos.contracts import Tool


class ${pascal}Tool(Tool):
    \"\"\"TODO: describe what this tool does for $name.\"\"\"

    @property
    def name(self) -> str:
        return "$name"

    def execute(self, context: object, **arguments: Any) -> Any:
        # TODO: call the underlying API / service and return a structured result.
        raise NotImplementedError
"""
)

_SERVICE_GENERIC = Template(
    """\"\"\"A $label for the $name integration.\"\"\"

from __future__ import annotations

from xyberos.contracts import $contract


class ${pascal}Service($contract):
    \"\"\"TODO: implement the $contract contract for $name.\"\"\"

$stubs
"""
)

_PLUGIN_TYPED = Template(
    """\"\"\"Plugin entry point for the $name integration.\"\"\"

from __future__ import annotations

${contracts_import}from xyberos_plugin_sdk.base import $base

from .service import $contribution


class ${pascal}Plugin($base):
    \"\"\"A $label plugin that contributes $contribution.\"\"\"

    @property
    def name(self) -> str:
        return "$name"

    def $method(self) -> $return_type:
        return $contribution_value


plugin = ${pascal}Plugin()
"""
)

_PLUGIN_OTHER = Template(
    """\"\"\"Plugin entry point for the $name integration.\"\"\"

from __future__ import annotations

from xyberos.contracts import Plugin


class ${pascal}Plugin(Plugin):
    \"\"\"Registers the $name $label with a Xyberos kernel.\"\"\"

    @property
    def name(self) -> str:
        return "$name"

    def register(self, kernel: object) -> None:
        # TODO: wire your $label into the kernel, e.g.
        # kernel.register("$name", <service>)
        raise NotImplementedError

    def unregister(self, kernel: object) -> None:
        # TODO: undo whatever register() did.
        raise NotImplementedError


plugin = ${pascal}Plugin()
"""
)

_TESTS = Template(
    """\"\"\"Contract + load tests for the $name plugin.\"\"\"

from xyberos import create_app

from $pkg.plugin import ${pascal}Plugin


def test_plugin_is_loadable():
    app = create_app()
    plugin = ${pascal}Plugin()
    assert app.load_plugin(plugin) is plugin
    assert plugin.name == "$name"
    app.unload_plugin(plugin.name)


def test_plugin_conforms_to_contract():
    plugin = ${pascal}Plugin()
    assert isinstance(plugin.name, str) and plugin.name.strip()
    assert callable(plugin.register) and callable(plugin.unregister)
"""
)

_EXAMPLE = Template(
    """\"\"\"Example: load the $name plugin and exercise it.\"\"\"

from xyberos import create_app

from $pkg import plugin


def main() -> None:
    app = create_app()
    app.load_plugin(plugin)
    print("loaded plugins:", app.plugins.names)
    # TODO: exercise the contributed service.


if __name__ == "__main__":
    main()
"""
)


# --------------------------------------------------------------------------- #
# Generation
# --------------------------------------------------------------------------- #


def _service_source(plugin_type: str, info: dict[str, Any], name: str, pascal: str) -> str:
    if info["plural"]:
        return _SERVICE_TOOL.substitute(name=name, Name=pascal, pascal=pascal)
    stubs = "".join(
        render_stub(
            CONTRACTS[plugin_type],
            member,
            name_value=name if member == "name" else None,
            indent=4,
        )
        for member in abstract_members(CONTRACTS[plugin_type])
    )
    return _SERVICE_GENERIC.substitute(
        label=info["label"], name=name, pascal=pascal, contract=info["contract"], stubs=stubs
    )


def _plugin_source(info: dict[str, Any], name: str, pascal: str, pkg: str) -> str:
    if info["base"] is None:
        return _PLUGIN_OTHER.substitute(name=name, pascal=pascal, label=info["label"])
    contribution = f"{pascal}Tool" if info["plural"] else f"{pascal}Service"
    contribution_value = f"[{contribution}()]" if info["plural"] else f"{contribution}()"
    contracts_import = f"from xyberos.contracts import {info['contract']}\n\n"
    return _PLUGIN_TYPED.substitute(
        name=name,
        pascal=pascal,
        base=info["base"],
        label=info["label"],
        contribution=contribution,
        method=info["method"],
        return_type=info["return"],
        contribution_value=contribution_value,
        contracts_import=contracts_import,
    )


def generate_plugin(target: Path, answers: dict[str, Any]) -> list[Path]:
    """Scaffold a plugin into ``target``. Returns the created file paths."""
    name = answers["name"]
    pkg = _sanitize_package(name)
    pascal = _to_pascal(name)
    plugin_type = answers["type"]
    info = TYPE_INFO[plugin_type]
    prefix = _env_prefix(name)

    files = {
        "pyproject.toml": _PYPROJECT.substitute(
            dist_name=pkg, description=answers["description"], name=name, pkg=pkg
        ),
        "README.md": _README.substitute(
            Name=pascal,
            name=name,
            description=answers["description"],
            label=info["label"],
            integrate_with=answers["integrate_with"] or "TODO: describe the external system",
        ),
        f"{pkg}/__init__.py": _INIT.substitute(Name=pascal, label=info["label"]),
        f"{pkg}/config.py": _CONFIG.substitute(
            name=name, base_url=f"https://api.{name}.example.com", prefix=prefix
        ),
        f"{pkg}/service.py": _service_source(plugin_type, info, name, pascal),
        f"{pkg}/plugin.py": _plugin_source(info, name, pascal, pkg),
        "tests/test_plugin.py": _TESTS.substitute(name=name, pascal=pascal, pkg=pkg),
        "examples/example.py": _EXAMPLE.substitute(name=name, pkg=pkg),
    }
    created: list[Path] = []
    for relative, content in files.items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        created.append(path)
    return created


# --------------------------------------------------------------------------- #
# Wizard
# --------------------------------------------------------------------------- #


def _prompt(message: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"{message}{suffix} > ").strip()
    except (EOFError, KeyboardInterrupt):
        value = ""
    return value or default or ""


def _prompt_type() -> str:
    types = list(TYPE_INFO)
    print("What type of plugin is this?")
    for index, key in enumerate(types, start=1):
        print(f"  {index}. {TYPE_INFO[key]['label']}")
    choice = _prompt("Choose a number")
    try:
        return types[int(choice) - 1]
    except (ValueError, IndexError):
        return "other"


def gather_answers(args: argparse.Namespace) -> dict[str, Any]:
    """Collect answers from flags or an interactive wizard."""
    answers: dict[str, Any] = {
        "name": args.name,
        "type": args.type,
        "description": args.description,
        "integrate_with": args.integrate_with,
        "auth": args.auth or "none",
        "async_support": args.async_support,
        "streaming": args.streaming,
    }
    if args.non_interactive:
        missing = [key for key in ("name", "type", "description") if not answers[key]]
        if missing:
            raise SystemExit(
                "error: --non-interactive requires --name, --type and --description "
                f"(missing: {', '.join(missing)})"
            )
        return answers

    answers["name"] = _prompt("What is your plugin name?", default=answers["name"] or "myplugin")
    answers["type"] = answers["type"] or _prompt_type()
    answers["description"] = _prompt(
        "What does this plugin do?",
        default=answers["description"] or f"A {TYPE_INFO[answers['type']]['label']} plugin",
    )
    answers["integrate_with"] = _prompt(
        "What does this plugin integrate with?", default=answers["integrate_with"] or ""
    )
    return answers


def run_create(args: argparse.Namespace) -> int:
    answers = gather_answers(args)
    target = Path(args.dir) / answers["name"]
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"error: {target} already exists and is not empty")
    created = generate_plugin(target, answers)
    print(f"Created plugin {answers['name']!r} in {target}")
    label = TYPE_INFO[answers['type']]['label']
    print(f"  {len(created)} files generated ({answers['type']} / {label})")
    print()
    print("Next steps:")
    print(f"  cd {target}")
    print("  pip install -e .            # install the plugin + entry point")
    print("  # implement the TODO items in <pkg>/service.py")
    print("  xyberos plugin validate .   # static + live-kernel validation")
    print("  python -m pytest            # run the generated tests")
    return 0

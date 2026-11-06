"""Generate the inventory half of the feature-support page.

That page answers two different questions, and only one of them is a fact about the tree.

*What exists* is derived: the extras come from ``pyproject.toml``, the packages from
``packages.toml`` — read through the same loader the compatibility job uses, so this page and that
job cannot read the manifest differently — and the modules from ``src/xyberos/``. Even the extra a
module needs is read rather than remembered, because a module that refuses to import without one
names it in its own guard, which is the same string its ``ModuleNotFoundError`` carries.

*What this project promises* is a decision, so it stays hand-written in the page: the labels, the
extension points you implement, what is refused, and where a capability you add yourself belongs.

    python site/scripts/matrix.py            # write the inventory into the page
    python site/scripts/matrix.py --check    # fail when the page has drifted from the tree
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from frontmatter import REPOSITORY_ROOT, SITE_ROOT

if str(REPOSITORY_ROOT / "tools") not in sys.path:
    # The manifest loader lives beside the compatibility job that reads the same file, and is on
    # `sys.path` for the test suite already. A docs build is not, so it is added here.
    sys.path.insert(0, str(REPOSITORY_ROOT / "tools"))

import ecosystem  # noqa: E402 - the path above has to be in place before this import

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python 3.10 reads TOML through tomli, with the same API.
    import tomli as tomllib

PAGE = SITE_ROOT / "feature-support.md"
CORE_ROOT = REPOSITORY_ROOT / "src" / "xyberos"
PYPROJECT = REPOSITORY_ROOT / "pyproject.toml"
MANIFEST = REPOSITORY_ROOT / "packages.toml"

MARKER_OPEN = "<!-- generated:inventory -->"
MARKER_CLOSE = "<!-- generated:end -->"

_GUARD = re.compile(r'extra_error\(\s*"([a-z]+)"')

#: The one thing a reader wants that the tree cannot state, keyed by the module or extra it
#: describes. `_summaries_for` refuses to render a row without one, so a new module or extra is a
#: failing check rather than a blank cell.
_SUMMARIES = {
    "xyberos": "Composition, dependency injection, lifecycle, configuration, routing, context, "
    "workflow engine, error taxonomy",
    "xyberos.ai": "Provider-neutral AI facade: chat, streaming, structured output, tools, and a "
    "closed JSON Schema subset",
    "xyberos.cli": "The `xyberos` command's implementation; the command and its options are the "
    "promise, not these modules",
    "xyberos.database": "SQLite provider, connection and transaction handling, Alembic runner, "
    "provider conformance suite",
    "xyberos.durable": "Experimental single-host durable execution: journal, store, scheduler, "
    "worker, recovery",
    "xyberos.execution": "In-process workflow engine: steps, edges, retries, timeouts, "
    "cancellation, events",
    "xyberos.http": "Starlette adapter, route compiling, middleware, request metrics, sessions, "
    "CSRF protection, test client",
    "xyberos.mcp": "Model Context Protocol client over streamable HTTP, and the projection of a "
    "server's tools into the AI tool model",
    "xyberos.plugins": "The plugin protocol and registry: trusted, ordered, no discovery",
    "xyberos.runtime": "Dependency scopes, context binding, correlation ids, deadlines",
    "xyberos.storage": "Storage contract, filesystem provider, in-memory double, conformance suite",
    "http": "Routing an application's routes as an ASGI application",
    "database": "A single-file SQLAlchemy-friendly database, and the migrations that go with it",
    "ollama": "The first AI provider: a local Ollama service",
    "durable": "Persistence for workflow progress, single host and at-least-once",
    "dev": "The contributor's toolchain, and the two libraries this line expects an *application* "
    "to bring: Jinja2 and python-multipart",
}


@dataclass(frozen=True)
class Module:
    """One module this package ships, and the two different things `Needs` and `Needed by` mean.

    ``extras`` answers a reader's question — *can I import this with core alone?* — and is only the
    extras reachable from the package's own entry point. ``guards`` is the wider fact: every file
    under the package that refuses to import without an extra, wherever it sits, which is what the
    extras table has to list.
    """

    path: str
    extras: tuple[str, ...]
    guards: tuple[tuple[str, str], ...]

    @property
    def needs(self) -> str:
        """What a reader has to install for this import: nothing, or the extras its guard names."""
        if not self.extras:
            return "core"
        return ", ".join(f"`[{extra}]`" for extra in self.extras)

    def guarded_modules(self, extra: str) -> tuple[str, ...]:
        """Return the modules under this package that guard ``extra``."""
        return tuple(sorted(name for name, guarded in self.guards if guarded == extra))


def declared_extras() -> dict[str, tuple[str, ...]]:
    """Return each extra and the requirements it declares, read from the packaging metadata."""
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    extras = project.get("optional-dependencies", {})
    if not isinstance(extras, dict) or not extras:
        raise SystemExit("pyproject.toml declares no optional dependencies to inventory")
    return {name: tuple(requirements) for name, requirements in extras.items()}


def modules() -> tuple[Module, ...]:
    """Return the package's own surface: the root, and one row per subpackage.

    A row answers the question a reader has — *can I import this with core alone?* — so the extras
    are the ones reachable from the package's own ``__init__.py``. That is the difference between
    `xyberos.ai`, which is core, and `xyberos.ai.ollama`, which is not: the facade does not import
    the adapter, so the rollup has to follow the entry point rather than every file underneath it.
    """
    public = [CORE_ROOT]
    public.extend(sorted(path for path in CORE_ROOT.iterdir() if _is_package(path)))
    return tuple(_module(path) for path in public)


def _is_package(path: Path) -> bool:
    return path.is_dir() and (path / "__init__.py").is_file() and not path.name.startswith("_")


def _module(path: Path) -> Module:
    name = "xyberos" if path == CORE_ROOT else f"xyberos.{path.name}"
    entry = path / "__init__.py"
    reachable: dict[str, str] = {}
    for source in [entry, *_relative_targets(entry)]:
        for extra in _GUARD.findall(source.read_text(encoding="utf-8")):
            reachable.setdefault(extra, _dotted(source))
    guarded: dict[str, str] = {}
    # The root row describes the root's own modules: every subpackage has its own row, and letting
    # the root scan recursively would list each of their guards twice.
    sources = path.glob("*.py") if path == CORE_ROOT else path.rglob("*.py")
    for source in sorted(sources):
        if "__pycache__" in source.parts:
            continue
        for extra in _GUARD.findall(source.read_text(encoding="utf-8")):
            guarded.setdefault(_dotted(source), extra)
    return Module(
        path=name,
        extras=tuple(sorted(reachable)),
        guards=tuple(sorted((module, extra) for module, extra in guarded.items())),
    )


def _relative_targets(entry: Path) -> list[Path]:
    """Return the files ``entry`` imports from this package, relative or absolute.

    Both spellings are in use — `from .sqlite import ...` and `from xyberos.database.sqlite import
    ...` — and either way the import is what decides whether the package as a whole can be imported
    without an extra, so both are followed.
    """
    tree = ast.parse(entry.read_text(encoding="utf-8"))
    targets: list[Path] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        names = [alias.name for alias in node.names]
        module = node.module or ""
        if node.level:
            targets.extend(_candidates(entry.parent, module, names))
        elif module == "xyberos" or module.startswith("xyberos."):
            targets.extend(_candidates(REPOSITORY_ROOT / "src", module, names))
    return [target for target in targets if target.is_file()]


def _candidates(base: Path, module: str, names: list[str]) -> list[Path]:
    """Return the files a `from ... import ...` could mean, for a module or a bare name."""
    if not module:
        return [base / f"{name}.py" for name in names] + [
            base / name / "__init__.py" for name in names
        ]
    path = module.replace(".", "/")
    return [base / f"{path}.py", base / path / "__init__.py"]


def _dotted(source: Path) -> str:
    """Return the import path of one file, as a reader would write it."""
    relative = source.relative_to(REPOSITORY_ROOT / "src").with_suffix("")
    parts = [part for part in relative.parts if part != "__init__"]
    return ".".join(parts)


def summarize(modules_seen: tuple[Module, ...], extras_seen: dict[str, tuple[str, ...]]) -> None:
    """Refuse to render a module or extra this file cannot describe, and an unknown extra."""
    for module in modules_seen:
        for extra in module.extras:
            if extra not in extras_seen:
                raise SystemExit(
                    f"{module.path} refuses to import without an extra {extra!r}, which "
                    f"pyproject.toml does not declare"
                )
    for key in (*[module.path for module in modules_seen], *extras_seen):
        if key not in _SUMMARIES:
            raise SystemExit(
                f"no summary for {key!r}: add one to _SUMMARIES in site/scripts/matrix.py"
            )


def render_region() -> str:
    """Return the generated tables, as the markdown that replaces the page's marker region."""
    extras_seen = declared_extras()
    modules_seen = modules()
    summarize(modules_seen, extras_seen)
    return "\n".join(
        [
            "_Generated when the site is built, and checked by `site/scripts/matrix.py "
            "--check`, so this inventory cannot describe a tree that no longer exists._",
            "",
            "**Modules.** What this package ships, and what a reader has to install for it. The "
            "`Needs` column is read from the code rather than remembered: a module that refuses to "
            "import without an extra names it in its own import guard, and the rollup follows each "
            "package's own entry point, which is why `xyberos.ai` is core while its Ollama adapter "
            "is not.",
            "",
            "| Module | What it provides | Needs |",
            "| ------ | ---------------- | ----- |",
            *[
                f"| `{module.path}` | {_SUMMARIES[module.path]} | {module.needs} |"
                for module in modules_seen
            ],
            "",
            "**Extras.** One install each, and the modules that cannot be imported without it. "
            "`dev` is the contributor's toolchain rather than a user's: it is what makes the two "
            "libraries an *application* brings — Jinja2 and python-multipart — available to the "
            "test suite that documents them.",
            "",
            "| Extra | Declares | Needed by | What it adds |",
            "| ----- | -------- | --------- | ------------ |",
            *[
                _extra_row(name, requirements, modules_seen)
                for name, requirements in sorted(extras_seen.items())
            ],
            "",
            "**Packages outside this repository.** Every name this line knows about, from "
            "[`packages.toml`](https://github.com/xyberos/xyberos/blob/master/packages.toml) — "
            "the manifest the compatibility job also reads. `planned` means decided and no "
            "distribution is written, `written` means the distribution exists and this line "
            "has no release of it, and `published` means a release exists that the job installs "
            "and proves.",
            "",
            "| Package | Import root | Status | Declares | Subject |",
            "| ------- | ----------- | ------ | -------- | ------- |",
            *[_package_row(entry) for entry in ecosystem.packages(ecosystem.load(MANIFEST))],
        ]
    )


def _extra_row(name: str, requirements: tuple[str, ...], modules_seen: tuple[Module, ...]) -> str:
    needed_by = sorted({module for seen in modules_seen for module in seen.guarded_modules(name)})
    declares = ", ".join(f"`{requirement}`" for requirement in requirements) or "—"
    return f"| `[{name}]` | {declares} | {_or_dash(needed_by)} | {_SUMMARIES[name]} |"


def _package_row(entry: dict[str, object]) -> str:
    name = str(entry["name"])
    status = str(entry["status"])
    if status == "retired" and entry.get("replaced_by"):
        status = f"retired → `{entry['replaced_by']}`"
    dependencies = entry.get("dependencies") or []
    declares = ", ".join(f"`{item}`" for item in _sequence(dependencies)) or "—"
    return f"| `{name}` | `{entry['import_root']}` | {status} | {declares} | {entry['summary']} |"


def _sequence(value: object) -> list[object]:
    """Return a manifest list field as a list, so a missing or malformed one is not a crash."""
    return list(value) if isinstance(value, list) else []


def _or_dash(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "—"


def render(page: str) -> str:
    """Return ``page`` with the region between the markers replaced by the generated inventory."""
    openings, closings = page.count(MARKER_OPEN), page.count(MARKER_CLOSE)
    if openings != 1 or closings != 1:
        raise SystemExit(
            f"{PAGE.name} needs exactly one {MARKER_OPEN} and one {MARKER_CLOSE} to fill in; "
            f"it has {openings} and {closings}"
        )
    start = page.index(MARKER_OPEN) + len(MARKER_OPEN)
    end = page.index(MARKER_CLOSE)
    if end < start:
        raise SystemExit(f"{PAGE.name} closes its inventory region before it opens it")
    return f"{page[:start]}\n\n{render_region()}\n\n{page[end:]}"


def main(argv: list[str] | None = None) -> int:
    """Write the inventory into the page, or check that the page still matches the tree."""
    parser = argparse.ArgumentParser(
        description="Generate and check the feature-support page's inventory."
    )
    parser.add_argument("--check", action="store_true", help="fail when the page has drifted")
    args = parser.parse_args(argv)

    page = PAGE.read_text(encoding="utf-8")
    rendered = render(page)
    if rendered == page:
        if args.check:
            print("matrix: the inventory matches the tree")
        return 0
    if args.check:
        print(
            "matrix: site/feature-support.md has drifted from pyproject.toml, packages.toml, or "
            "the source tree; run `python site/scripts/build.py` to regenerate it",
            file=sys.stderr,
        )
        return 1
    PAGE.write_text(rendered, encoding="utf-8")
    print("matrix: wrote the inventory into site/feature-support.md")
    return 0


if __name__ == "__main__":  # pragma: no cover - the build and the tests call main() directly.
    sys.exit(main())

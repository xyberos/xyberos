"""Render ``docs/`` into the site as the API and guide reference.

``docs/`` stays the only copy of each guide: this script copies it into ``site/reference/`` at build
time and the directory is generated rather than committed, so a guide is never maintained twice.

The one transformation is link rewriting. A guide's links are written for GitHub, so they point at
targets outside ``docs/``: another repository file, an example directory, an ADR. Relative links
that stay inside ``docs/`` keep working because the tree is preserved; a link that escapes it is
rewritten to the repository's blob URL, because a site that resolves to a file it does not contain
fails its own strict build.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

from frontmatter import REPOSITORY_ROOT, SITE_ROOT

DOCS_ROOT = REPOSITORY_ROOT / "docs"
REFERENCE_ROOT = SITE_ROOT / "reference"
MARKER = ".generated"
BLOB = "https://github.com/xyberos/xyberos/blob/master"

_LINK = re.compile(r'\]\(([^)\s]+)(\s+"[^"]*")?\)')

INDEX = """\
# Reference

The guides, generated from the repository's [`docs/`]({blob}/tree/master/docs) directory. Each page
below is a copy of the file it names, so a correction belongs in `docs/` and never here.

| Guide | What it covers |
| ----- | -------------- |
{rows}
"""

_INDEX_ROW = "| [{title}]({target}) | {summary} |"

_SUMMARIES = {
    "adr": "Architecture decision records, and the reason behind each refusal",
    "ai": "The provider-neutral AI facade, structured output, tools, and the Ollama adapter",
    "architecture": "The architecture review",
    "capabilities": "What is absent by decision, and the seam or package that answers it",
    "cli": "The four commands: `new`, `check`, `run`, and `migrate`",
    "database": "Database operations with the shipped SQLite provider",
    "database-providers": "Writing a provider package that passes the conformance suite",
    "durable": "Durable execution, and its stated non-guarantees",
    "getting-started": "Installation and the first application",
    "http": "The Starlette-backed HTTP adapter",
    "implementation": "The phase-by-phase implementation plan for this release",
    "mcp": "Consuming an MCP server's tools through the shipped tool model",
    "performance": "The performance baselines",
    "plugins": "The trusted plugin contract",
    "positioning": "Who the framework is for, and who it is not for",
    "release": "The release procedure and its preconditions",
    "runtime": "Scopes, lifecycle, configuration, and the error taxonomy",
    "security": "The security posture, and the one deployment failure mode that matters",
    "stability": "Which surface is stable, preview, or experimental",
    "storage": "Object storage: the contract, the shipped filesystem provider, and the key rules",
    "testing": "Test doubles and how to test an application without a service",
    "troubleshooting": "Diagnosing the errors the runtime raises",
    "tutorial": "The tutorial that this site retires into the Fundamentals path",
    "workflow": "The in-process workflow engine",
}


def _rewrite(
    text: str, source: Path, destination: Path, reference_root: Path = REFERENCE_ROOT
) -> str:
    """Point every link at its copy inside ``docs/``, or at the repository blob.

    Two cases, and the second is easy to get wrong. A link that stays inside ``docs/`` is *rebased*
    rather than kept: a guide may reach a sibling through ``../docs/``, which is correct where the
    guide is written and wrong once the file has moved into ``site/reference/``. A link that escapes
    ``docs/`` becomes a repository URL, because the documentation build only contains the guides.
    """

    def replace(match: re.Match[str]) -> str:
        target, suffix = match.group(1), match.group(2) or ""
        if "://" in target or target.startswith(("#", "mailto:")):
            return match.group(0)
        path, _, fragment = target.partition("#")
        if not path:
            return match.group(0)

        resolved = (source.parent / path).resolve()
        anchor = f"#{fragment}" if fragment else ""

        try:
            inside = resolved.relative_to(DOCS_ROOT.resolve())
        except ValueError:
            try:
                outside = resolved.relative_to(REPOSITORY_ROOT).as_posix().rstrip("/")
            except ValueError:
                return match.group(0)
            return f"]({BLOB}/{outside}{suffix})"

        here = destination.parent.relative_to(reference_root)
        rebased = Path(os.path.relpath(inside, start=here)).as_posix()
        return f"]({rebased}{anchor}{suffix})"

    return _LINK.sub(replace, text)


def _title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def _clear(reference_root: Path) -> None:
    """Remove the previous generated copy, and refuse to touch anything else.

    The directory is generated and git-ignored, but deleting a directory is the one destructive
    thing this script does, so it requires the marker it wrote on a previous run.
    """
    if not reference_root.exists():
        return
    if not (reference_root / MARKER).exists():
        raise SystemExit(
            f"refusing to clear {reference_root} because it has no {MARKER} marker: "
            "it was not written by this script"
        )
    shutil.rmtree(reference_root)


def render(docs_root: Path = DOCS_ROOT, reference_root: Path = REFERENCE_ROOT) -> int:
    """Render ``docs_root`` into ``reference_root``, and return how many guides were written.

    The roots are parameters so a test can render a fresh copy elsewhere and compare it with the one
    the build produced, which is what proves the site's reference is generated rather than edited.
    """
    _clear(reference_root)
    reference_root.mkdir(parents=True)
    (reference_root / MARKER).write_text(
        "Generated by site/scripts/reference.py from docs/. Do not edit, and do not commit.\n",
        encoding="utf-8",
    )

    rows: list[str] = []
    count = 0
    for source in sorted(docs_root.rglob("*.md")):
        relative = source.relative_to(docs_root)
        destination = reference_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        text = source.read_text(encoding="utf-8")
        destination.write_text(
            _rewrite(text, source, destination, reference_root), encoding="utf-8"
        )
        count += 1
        if relative.name == "README.md":
            continue
        key = relative.parts[0].removesuffix(".md")
        rows.append(
            _INDEX_ROW.format(
                title=_title(text, relative.stem),
                target=relative.as_posix(),
                summary=_SUMMARIES.get(key, ""),
            )
        )

    (reference_root / "index.md").write_text(
        INDEX.format(blob=BLOB, rows="\n".join(sorted(rows))), encoding="utf-8"
    )
    return count


def main() -> int:
    """Render the reference, and report what was written."""
    count = render()
    print(f"reference: rendered {count} guides from docs/ into site/reference/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

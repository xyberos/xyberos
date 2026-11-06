"""The capability index is the answer to "do I have to adopt Django for this?", so it is checked.

`docs/capabilities.md` is written by hand, because the *placement* of a capability is a decision
rather than a fact about the tree — but every name, link, and extra it points at has to resolve.
This is the same guard `tests/test_packages_manifest.py` runs over the plugin catalogue: a
hand-maintained list is exactly the list that drifts, so the drift is a failing test rather than a
reader's discovery.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import ecosystem

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python 3.10 uses the tomli fallback.
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "capabilities.md"
MANIFEST = ROOT / "packages.toml"
MKDOCS = ROOT / "mkdocs.yml"
ADRS = ROOT / "docs" / "adr"

TEXT = PAGE.read_text(encoding="utf-8")
ENTRIES = ecosystem.packages(ecosystem.load(MANIFEST))

#: A package name, wherever the page writes it: backticked in prose, or inside an install line.
PACKAGE = re.compile(r"xyberos-[a-z0-9-]+")
ADR = re.compile(r"adr/(\d{4}-[a-z0-9-]+\.md)")
EXTRA = re.compile(r"xyberos\[([a-z]+)\]")
#: A repository-relative markdown link, which is what the page has to resolve.
LINK = re.compile(r"\]\((\.{1,2}/[^)\s#]+)")


def pyproject_extras() -> set[str]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    return set(project.get("optional-dependencies", {}))


def test_the_page_names_every_package_and_invents_none() -> None:
    known = {str(entry["name"]) for entry in ENTRIES}
    mentioned = {name.rstrip("-") for name in PACKAGE.findall(TEXT)}

    invented = mentioned - known
    omitted = known - mentioned

    assert not invented, f"the index names packages the manifest does not know: {invented}"
    assert not omitted, f"the index omits packages a reader would look for: {omitted}"


def test_every_adr_the_page_cites_exists() -> None:
    cited = set(ADR.findall(TEXT))
    assert cited, "the index cites no ADR, which means the parse is broken rather than the page"

    missing = sorted(name for name in cited if not (ADRS / name).is_file())
    assert missing == [], f"the index cites ADRs that do not exist: {missing}"


def test_every_extra_the_page_names_is_declared() -> None:
    mentioned = set(EXTRA.findall(TEXT))
    assert mentioned, "the index names no extra, so the parse is broken rather than the page"

    undeclared = sorted(mentioned - pyproject_extras())
    assert undeclared == [], f"the index names extras pyproject.toml does not declare: {undeclared}"


def test_every_link_resolves_from_the_docs_directory() -> None:
    problems: list[str] = []
    for target in LINK.findall(TEXT):
        resolved = (PAGE.parent / target).resolve()
        candidates = (resolved, resolved.with_suffix(".md"), resolved / "index.md")
        if not any(candidate.exists() for candidate in candidates):
            problems.append(f"{target!r} does not resolve from docs/")
    assert problems == [], "\n".join(problems)


def test_the_page_is_offered_by_the_reference_navigation() -> None:
    """A guide the reader cannot reach is a guide that does not exist."""
    assert "reference/capabilities.md" in MKDOCS.read_text(encoding="utf-8")


def test_the_page_states_the_placement_of_the_sessions_and_csrf_row() -> None:
    """The row this index changed most recently has to say what shipped and what did not."""
    assert "CSRFMiddleware" in TEXT
    assert "SessionMiddleware" in TEXT
    assert "0024-sessions-and-csrf-are-middleware-in-the-http-module.md" in TEXT

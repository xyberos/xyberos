"""Generate the roadmap page, and hold the site to it.

Two jobs, and they share one source of truth: the front matter on each page.

* ``python site/scripts/roadmap.py`` writes ``site/roadmap.md`` from the declared statuses, so the
  counters, the per-path tables, and the navigation cannot disagree with the pages.
* ``--check`` fails a build that would ship a hole: a lesson page with no example, a lesson that is
  not in the navigation, a duplicate path and lesson number, or a ``draft`` lesson inside the
  navigation. ``--release`` adds the completeness requirement, so a lesson that is not ``verified``
  and a section that is still ``planned`` stop a release rather than embarrassing one.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from frontmatter import (
    LESSON_KEYS,
    PATHS,
    SITE_ROOT,
    STATUSES,
    TIERS,
    VERIFICATIONS,
    Page,
    iter_pages,
    load_config,
)

REPOSITORY_ROOT = SITE_ROOT.parent
MKDOCS = REPOSITORY_ROOT / "mkdocs.yml"
ROADMAP = SITE_ROOT / "roadmap.md"

#: Pages the build generates rather than reads, so their absence here is expected.
GENERATED = ("roadmap.md",)
GENERATED_PREFIXES = ("reference/",)

PATH_TITLES = {
    "fundamentals": "Fundamentals",
    "traditional": "Traditional Apps",
    "ai": "AI Apps",
    "hybrid": "Hybrid Apps",
}

TIER_LABELS = {
    "built-in": "Built-in",
    "extension-point": "Extension point",
    "third-party": "You add it",
    "not-provided": "You build it",
}


def _is_generated(relative: str) -> bool:
    return relative in GENERATED or relative.startswith(GENERATED_PREFIXES)


def navigation() -> list[str]:
    """Flatten ``mkdocs.yml``'s navigation into the page paths it names."""
    if not MKDOCS.exists():
        return []
    loaded = load_config(MKDOCS)
    return _flatten(loaded.get("nav"))


def _flatten(node: Any) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        found: list[str] = []
        for item in node:
            found.extend(_flatten(item))
        return found
    if isinstance(node, dict):
        found = []
        for value in node.values():
            found.extend(_flatten(value))
        return found
    return []


def _draft_in_nav(pages: list[Page], nav: list[str]) -> list[str]:
    """Return navigation entries that are not finished.

    This is checked on every run, including the plain generation that ``build.py`` performs, so a
    ``draft`` lesson cannot reach a built site: the gate is the build failing, not a promise.
    """
    return [
        f"{page.repository_relative}: is {page.status or 'unstatused'} yet in the navigation"
        for page in pages
        if page.relative in nav and page.status in {"draft", ""}
    ]


def _lesson_problems(pages: list[Page], nav: list[str]) -> list[str]:
    """Return every way a lesson page breaks its contract."""
    problems: list[str] = []
    seen: dict[tuple[str, int], str] = {}

    for page in pages:
        where = page.repository_relative
        if not page.is_lesson:
            continue

        for missing in LESSON_KEYS:
            if page.meta.get(missing) in (None, ""):
                problems.append(f"{where}: a lesson must declare {missing!r}")

        if page.status not in STATUSES:
            problems.append(f"{where}: status {page.status!r} is not one of {', '.join(STATUSES)}")
        if page.tier not in TIERS:
            problems.append(f"{where}: tier {page.tier!r} is not one of {', '.join(TIERS)}")
        if page.verify not in VERIFICATIONS:
            problems.append(
                f"{where}: verify {page.verify!r} is not one of {', '.join(VERIFICATIONS)}"
            )

        path = page.meta.get("path")
        lesson = page.meta.get("lesson")
        if path not in PATHS:
            problems.append(f"{where}: path {path!r} is not one of {', '.join(PATHS)}")
        if not isinstance(lesson, int):
            problems.append(f"{where}: lesson must be an integer, not {lesson!r}")
        elif path in PATHS:
            position = (str(path), lesson)
            if position in seen:
                problems.append(f"{where}: {path} lesson {lesson} is already {seen[position]}")
            seen[position] = where

        if page.relative not in nav:
            problems.append(f"{where}: a lesson must appear in the navigation")

        if page.verify in {"command", "scaffold"}:
            if not page.command:
                problems.append(f"{where}: a {page.verify} lesson must declare the command it runs")
            if not page.outputs:
                problems.append(f"{where}: a {page.verify} lesson must document its result")
            if page.verify == "scaffold" and page.example is not None:
                problems.append(f"{where}: a scaffold lesson declares no example, only a command")
            continue

        example = page.example
        if example is None or not example.exists():
            problems.append(f"{where}: example {page.meta.get('example')!r} does not exist")

        if not page.snippets:
            problems.append(f"{where}: a lesson must include its code by snippet")
        if page.verify == "output" and not page.outputs:
            problems.append(f"{where}: a lesson must document its output")

    for entry in nav:
        if _is_generated(entry) or "://" in entry:
            continue
        if not (SITE_ROOT / entry).exists():
            problems.append(f"mkdocs.yml: navigation names {entry!r}, which does not exist")

    return problems


def _shipping_problems(pages: list[Page]) -> list[str]:
    """Return everything that makes the site incomplete, whether or not it is in the navigation.

    A page that is still ``planned`` counts even when it is deliberately absent from the navigation:
    the release waits for all four paths, and a path that is not listed anywhere is the easiest way
    to ship one that does not exist.
    """
    problems: list[str] = []
    for page in pages:
        if page.is_lesson:
            if page.status != "verified":
                problems.append(
                    f"{page.repository_relative}: is {page.status or 'unstatused'}, not verified"
                )
        elif page.status == "planned":
            problems.append(f"{page.repository_relative}: is still planned")
    return problems


def render(pages: list[Page]) -> str:
    """Return the roadmap page."""
    lessons = sorted(
        (page for page in pages if page.is_lesson),
        key=lambda page: (str(page.meta.get("path")), int(page.meta.get("lesson", 0))),
    )
    verified = sum(1 for page in lessons if page.status == "verified")
    draft = sum(1 for page in lessons if page.status == "draft")
    planned = sum(1 for page in pages if page.status == "planned" and not page.is_lesson)

    lines = [
        "---",
        "title: Documentation roadmap",
        "status: verified",
        "---",
        "",
        "# Documentation roadmap",
        "",
        "Generated by `site/scripts/roadmap.py` from each page's front matter, so the counters",
        "are what the pages declare and cannot go stale. The phase-by-phase plan, with its exit",
        "criteria, is",
        "[the implementation plan](https://github.com/xyberos/xyberos/blob/master/site/implementation.md).",
        "",
        f"**{verified} of {len(lessons)} lessons verified.** "
        f"{draft} in progress, {planned} sections planned.",
        "",
        "| Learning path | Lessons | Verified | In progress |",
        "| ------------- | ------- | -------- | ----------- |",
    ]

    for path in PATHS:
        in_path = [page for page in lessons if page.meta.get("path") == path]
        if not in_path:
            lines.append(f"| {PATH_TITLES[path]} | 0 | 0 | 0 |")
            continue
        lines.append(
            f"| {PATH_TITLES[path]} | {len(in_path)} | "
            f"{sum(1 for page in in_path if page.status == 'verified')} | "
            f"{sum(1 for page in in_path if page.status == 'draft')} |"
        )

    for path in PATHS:
        in_path = [page for page in lessons if page.meta.get("path") == path]
        if not in_path:
            continue
        lines += [
            "",
            f"## {PATH_TITLES[path]}",
            "",
            "| Lesson | Title | Status | Availability |",
            "| ------ | ----- | ------ | ------------ |",
        ]
        for page in in_path:
            lines.append(
                f"| {page.meta['lesson']} | {page.title} | {page.status} | "
                f"{TIER_LABELS.get(page.tier, page.tier)} |"
            )

    lines.append("")
    return "\n".join(lines)


def problems(pages: list[Page], nav: list[str], *, release: bool = False) -> list[str]:
    """Return every way the site breaks its own rules.

    Public so the test suite reads the same rules the build does: a rule lives in one place, and a
    failure names the page rather than only appearing in a build log.
    """
    found = _draft_in_nav(pages, nav)
    found += _lesson_problems(pages, nav)
    if release:
        found += _shipping_problems(pages)
    return found


def main(argv: list[str] | None = None) -> int:
    """Write the roadmap, and check what the arguments ask for."""
    parser = argparse.ArgumentParser(description="Generate and check the documentation roadmap.")
    parser.add_argument("--check", action="store_true", help="validate the pages without writing")
    parser.add_argument("--release", action="store_true", help="also require a complete site")
    args = parser.parse_args(argv)

    pages = list(iter_pages())
    nav = navigation()

    if args.release:
        found = problems(pages, nav, release=True)
    elif args.check:
        found = problems(pages, nav)
    else:
        # A plain generation still refuses to publish an unfinished page: the cheapest gate runs
        # every time the roadmap is written, which is every build.
        found = _draft_in_nav(pages, nav)

    if found:
        for problem in found:
            print(f"roadmap: {problem}", file=sys.stderr)
        return 1

    if not args.check:
        ROADMAP.parent.mkdir(parents=True, exist_ok=True)
        ROADMAP.write_text(render(pages), encoding="utf-8")
        print(f"roadmap: wrote {ROADMAP.relative_to(REPOSITORY_ROOT).as_posix()}")

    if args.release:
        print("roadmap: the site is complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())

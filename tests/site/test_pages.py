"""The rules that make a page a claim: structure, tiers, public names, and links.

Where the build already enforces a rule, this file calls the same function rather than restating it,
so a failure names the page instead of only appearing in a build log.
"""

from __future__ import annotations

import ast
import importlib
import json
import re
import sys
from pathlib import Path

import pytest
import site_pages as site
from site_pages import REPOSITORY_ROOT, SITE_ROOT, Page

#: A server command a page quotes, so the page's instruction can be checked rather than trusted.
SERVER_COMMAND = re.compile(r"uvicorn\s+--app-dir\s+(\S+)\s+--factory\s+([\w.]+):(\w+)")

PAGES = site.pages()
LESSONS = site.lessons()
IDS = site.lesson_ids()

#: A relative markdown link, which is what a documentation build resolves against its own tree.
LINK = re.compile(r"\]\((?!https?://|mailto:|#)([^)\s#]+)(?:#[^)]*)?\)")

#: Rows of the stability guide's "what is in each tier" table.
TIER_ROW = re.compile(
    r"^\|\s*[^|]+?\s*\|\s*(?P<imports>[^|]+?)\s*\|\s*(?P<tier>[^|]+?)\s*\|\s*$", re.MULTILINE
)
BACKTICKED = re.compile(r"`([a-z][a-z0-9_.]*)`")
TIERS = {"stable", "preview", "experimental"}

#: Pages the build generates, so they are absent from a fresh clone.
GENERATED = {"roadmap.md", "reference/index.md"}


def test_the_pages_satisfy_the_build_rules() -> None:
    """The same gate the build runs, so a structural mistake fails here first and by name."""
    assert site.roadmap.problems(PAGES, site.navigation()) == []


def stability_tiers() -> dict[str, str]:
    """Map each import path named by the stability guide to the tier it is given."""
    text = (REPOSITORY_ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
    found: dict[str, str] = {}
    for match in TIER_ROW.finditer(text):
        tier = match.group("tier").strip().strip("*").lower()
        if tier not in TIERS:
            continue
        for name in BACKTICKED.findall(match.group("imports")):
            if name.startswith("xyberos"):
                found[name] = tier
    return found


def test_the_stability_guide_is_parseable() -> None:
    """The checks below are worthless if this table silently stops parsing."""
    tiers = stability_tiers()
    assert tiers.get("xyberos.durable") == "experimental"
    assert tiers.get("xyberos.http") == "preview"
    assert tiers.get("xyberos.plugins") == "stable"


def imports_of(source: str) -> list[tuple[str, list[str]]]:
    """Every ``xyberos`` import in a module, as (module, names), by parsing rather than matching."""
    found: list[tuple[str, list[str]]] = []
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.split(".")[0] == "xyberos"
        ):
            found.append((node.module, [alias.name for alias in node.names]))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "xyberos":
                    found.append((alias.name, []))
    return found


def test_an_experimental_import_is_labelled_experimental() -> None:
    """A lesson that reaches an experimental surface has to say so on the page."""
    experimental = {name for name, tier in stability_tiers().items() if tier == "experimental"}
    problems: list[str] = []
    for page in LESSONS:
        example = page.example
        if example is None:
            continue
        source = example.read_text(encoding="utf-8")
        if any(name in source for name in experimental) and "experimental" not in page.body.lower():
            problems.append(
                f"{page.repository_relative} imports an experimental surface without saying so"
            )
    assert problems == []


def test_a_lesson_imports_only_documented_public_names() -> None:
    """A lesson may not teach a name the framework does not publish.

    A module that cannot be imported here is skipped rather than failed: an optional capability's
    extra may not be installed, and a lesson is still allowed to say which extra it needs.
    """
    problems: list[str] = []
    skipped: set[str] = set()
    for page in LESSONS:
        example = page.example
        if example is None:
            continue
        source = example.read_text(encoding="utf-8")
        for module_name, names in imports_of(source):
            try:
                module = importlib.import_module(module_name)
            except ModuleNotFoundError:
                skipped.add(module_name)
                continue
            exported = getattr(module, "__all__", None)
            if exported is None:
                continue
            for name in names:
                if name not in exported:
                    problems.append(
                        f"{page.repository_relative} imports {module_name}.{name}, "
                        "which is not public"
                    )
    assert problems == [], "\n".join(problems)


def _link_target(page: Page, target: str) -> Path:
    """Return where a link has to resolve for the build to accept it.

    A link into the generated reference is checked against ``docs/``, which is where that content is
    maintained: the copy under ``site/reference/`` is produced by the build and need not exist yet.
    """
    resolved: Path = (page.source.parent / target).resolve()
    try:
        relative = resolved.relative_to((SITE_ROOT / "reference").resolve())
    except ValueError:
        return resolved
    return REPOSITORY_ROOT / "docs" / relative


def test_the_site_links_only_to_files_that_exist() -> None:
    """A reader clicks the links, so a link that resolves nowhere is a build failure."""
    problems: list[str] = []
    for page in PAGES:
        for target in LINK.findall(page.body):
            if target in GENERATED:
                continue
            resolved = _link_target(page, target)
            candidates = (resolved, resolved.with_suffix(".md"), resolved / "index.md")
            if not any(candidate.exists() for candidate in candidates):
                problems.append(
                    f"{page.repository_relative} links to {target!r}, which does not exist"
                )
    assert problems == [], "\n".join(problems)


def test_a_quoted_server_command_names_a_real_factory() -> None:
    """A page that tells a reader to run a server has to name a factory that builds one.

    This is the check the tutorial's own suite used to make, moved to the pages that quote the
    command.
    """
    from starlette.applications import Starlette

    problems: list[str] = []
    for page in PAGES:
        for directory, module_name, attribute in SERVER_COMMAND.findall(page.body):
            search = str(REPOSITORY_ROOT / directory)
            sys.path.insert(0, search)
            try:
                built = getattr(importlib.import_module(module_name), attribute)()
            except Exception as error:  # noqa: BLE001 - the message is the point
                problems.append(
                    f"{page.repository_relative}: {module_name}:{attribute} failed: {error}"
                )
            else:
                if not isinstance(built, Starlette):
                    problems.append(
                        f"{page.repository_relative}: {module_name}:{attribute} built "
                        f"{type(built).__name__}, not an ASGI application"
                    )
            finally:
                sys.path.remove(search)
    assert problems == [], "\n".join(problems)


def test_every_page_marker_becomes_a_directive() -> None:
    """A page's claimed code is included, not merely named: every marker renders something."""
    problems = []
    for page in PAGES:
        rendered = site.snippets_hook.on_page_markdown(page.body)
        if site.snippets_hook.MARKER in rendered:
            problems.append(f"{page.repository_relative}: a marker survived the hook")
        for path in page.snippets:
            if f'--8<-- "{path}"' not in rendered:
                problems.append(
                    f"{page.repository_relative}: {path} is not included as a directive"
                )
    assert problems == [], "\n".join(problems)


def test_mkdocs_loads_the_snippet_hook() -> None:
    """The hook is wired: a page's markers are rendered by the build, not by a convention."""
    loaded = site.frontmatter.load_config()
    hooks = loaded.get("hooks") or []
    assert "site/scripts/snippets_hook.py" in hooks
    assert (REPOSITORY_ROOT / "site" / "scripts" / "snippets_hook.py").is_file()


def test_the_snippet_hook_renders_the_canonical_marker() -> None:
    """One marker in, one *fenced* directive out, including the spaced spelling."""
    hook = site.snippets_hook.on_page_markdown
    expected = '```python title="examples/a.py"\n--8<-- "examples/a.py"\n```\n'
    assert hook("<!-- snippet: examples/a.py -->\n") == expected
    assert hook("<!--snippet:examples/a.py-->\n") == expected
    assert hook("no marker here") == "no marker here"
    # Only a whole-line marker is rendered. A marker inside prose is left alone, and the build's
    # post-build check is what refuses it rather than a hook that guesses at the author's intent.
    inline = "prose <!-- snippet: examples/a.py --> more prose"
    assert hook(inline) == inline


def test_a_snippet_is_fenced_by_its_own_language() -> None:
    """The fence names the language and the file, so an include is highlighted and attributable."""
    assert site.snippets_hook.fenced("examples/learn_extend/sql_provider.py").startswith(
        '```python title="examples/learn_extend/sql_provider.py"'
    )
    assert site.snippets_hook.fenced("examples/learn_traditional/templates/list.html").startswith(
        "```html "
    )
    assert site.snippets_hook.fenced("notes.txt").startswith("```text ")


def test_an_included_file_renders_as_a_code_block() -> None:
    """The fence is the difference between a page that shows code and a page the code rewrote.

    A bare `--8<--` line splices the file into the Markdown stream, where a docstring becomes a
    paragraph, `from __future__ import annotations` renders with **future** in bold, and a `#:`
    comment becomes a heading. Converting the hook's own output with the extensions the build
    declares is what tells those two apart — the built site is the same conversion.
    """
    from html import unescape

    from markdown import markdown  # type: ignore[import-untyped]  # Markdown ships no stubs

    names: list[str] = []
    configs: dict[str, dict[str, object]] = {}
    for entry in site.frontmatter.load_config()["markdown_extensions"]:
        if isinstance(entry, str):
            names.append(entry)
        else:
            name, options = next(iter(entry.items()))
            names.append(name)
            configs[name] = options

    marker = "<!-- snippet: examples/learn_extend/sql_provider.py -->\n"
    converted = markdown(
        site.snippets_hook.on_page_markdown(marker), extensions=names, extension_configs=configs
    )
    source = (REPOSITORY_ROOT / "examples/learn_extend/sql_provider.py").read_text(encoding="utf-8")

    assert "<strong>" not in converted, "the file was parsed as Markdown rather than shown as code"
    block = re.search(r"<code[^>]*>(?P<body>.*?)</code>", converted, re.DOTALL)
    assert block is not None, "the include is not inside a code block"
    # Highlighting wraps every token in a span, so compare the block's text with the file's.
    shown = unescape(re.sub(r"<[^>]+>", "", block.group("body")))
    for line in source.splitlines():
        if line.startswith(("from ", "class ")):
            assert line in shown, f"{line!r} is not inside the code block"


def test_site_url_resolves_for_a_preview_and_the_release(monkeypatch: pytest.MonkeyPatch) -> None:
    """One configuration publishes twice, and every reader agrees which URL it is publishing under.

    `mkdocs.yml` writes `site_url: !ENV [SITE_URL, "https://docs.xyberos.com/"]`, the tag MkDocs
    resolves itself. The build, the roadmap, and the hook read the same file with `load_config`, so
    the tag has to resolve for them too — otherwise a preview fails on a configuration MkDocs
    accepts, and the failure looks like a broken site rather than an unread tag.
    """
    monkeypatch.delenv("SITE_URL", raising=False)
    assert site.frontmatter.load_config()["site_url"] == "https://docs.xyberos.com/"
    assert site.roadmap.navigation(), "the navigation reads the same configuration"

    monkeypatch.setenv("SITE_URL", "https://xyberos.github.io/xyberos/")
    assert site.frontmatter.load_config()["site_url"] == "https://xyberos.github.io/xyberos/"
    assert site.snippets_hook.output_directory() == REPOSITORY_ROOT / "build" / "site"


def test_a_surviving_marker_is_found_in_the_built_output(tmp_path: Path) -> None:
    """The build's post-build check works, rather than always reporting success."""
    pages = tmp_path / "learn"
    pages.mkdir()
    (pages / "index.html").write_text("<p>no code</p>", encoding="utf-8")
    assert site.snippets_hook.unrendered_pages(tmp_path) == []

    (pages / "lesson.html").write_text("<p><!-- snippet: examples/a.py --></p>", encoding="utf-8")
    assert site.snippets_hook.unrendered_pages(tmp_path) == [pages / "lesson.html"]
    assert site.snippets_hook.unrendered_pages(tmp_path / "absent") == []


def test_rendered_reference_matches_docs(tmp_path: Path) -> None:
    """The site's reference is a fresh copy of ``docs/``, not a copy that can drift from it."""
    generated = SITE_ROOT / "reference"
    if not generated.exists():
        pytest.skip("run `python site/scripts/build.py` to generate site/reference/ first")

    fresh = tmp_path / "reference"
    count = site.reference.render(docs_root=REPOSITORY_ROOT / "docs", reference_root=fresh)
    assert count > 0

    def read(root: Path) -> dict[str, str]:
        return {
            source.relative_to(root).as_posix(): source.read_text(encoding="utf-8")
            for source in root.rglob("*.md")
        }

    expected, actual = read(fresh), read(generated)
    assert actual.keys() == expected.keys()
    assert sorted(name for name in expected if expected[name] != actual[name]) == []


def test_the_published_schema_is_the_one_the_package_ships() -> None:
    """`$id` names an address, so the address has to answer with the schema the runtime reads."""
    published = SITE_ROOT / "schema" / "xyberos-config-1.json"
    if not published.exists():
        pytest.skip("run `python site/scripts/build.py` to publish the schema first")

    shipped = REPOSITORY_ROOT / "src" / "xyberos" / "config.schema.json"

    assert published.read_bytes() == shipped.read_bytes()
    assert json.loads(published.read_text(encoding="utf-8"))["$id"].endswith(
        "/schema/xyberos-config-1.json"
    )


def test_the_navigation_names_every_reference_guide() -> None:
    """The reference tree is generated, so the navigation is what makes it browsable.

    The list in `mkdocs.yml` is written rather than derived, because a reference is browsed and the
    groups are a judgement about reading order. This is the check that keeps the list true: a guide
    added to `docs/` is a page the Reference tab does not offer until it is named, and a name whose
    page the build excludes — `implementation.md` is one — fails the build rather than the reader.
    """
    generated = SITE_ROOT / "reference"
    if not generated.is_dir():
        pytest.skip("run `python site/scripts/build.py` to generate site/reference/ first")

    named = {path for path in site.navigation() if path.startswith("reference/")}
    written = {
        path.relative_to(SITE_ROOT).as_posix()
        for path in generated.rglob("*.md")
        if not site.frontmatter.is_excluded(path.relative_to(SITE_ROOT).as_posix())
    }

    assert sorted(written - named) == [], "a generated guide is not named by the navigation"
    assert sorted(named - written) == [], "the navigation names a page the build does not contain"

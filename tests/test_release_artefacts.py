"""The built artefacts contain what the release promises.

These assertions are about things that have actually gone wrong here: a `py.typed` marker missing
from the wheel, text describing the licence left stale inside `METADATA`, a licence file that does
not ship, an entry point that is not declared, and `src`-layout paths that end up one directory too
deep. Each of them is invisible from a checkout and obvious from an artefact, which is the whole
reason this file builds one.

The build runs once per session: it is the slowest thing in the suite, and every assertion is about
the same two files.
"""

from __future__ import annotations

import email
import re
import subprocess
import sys
import tarfile
import zipfile
from configparser import ConfigParser
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python 3.10 uses the tomli fallback.
    import tomli as tomllib

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DIST = REPOSITORY_ROOT / "dist"


@pytest.fixture(scope="session")
def project_version() -> str:
    pyproject = tomllib.loads((REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = pyproject["project"]["version"]
    assert isinstance(version, str)
    return version


@pytest.fixture(scope="session")
def artefacts(project_version: str) -> tuple[Path, Path]:
    """Build the wheel and sdist once, and return their paths."""
    for stale in DIST.glob("xyberos-*"):
        stale.unlink()
    result = subprocess.run(
        [sys.executable, "-m", "build"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    wheel = DIST / f"xyberos-{project_version}-py3-none-any.whl"
    sdist = DIST / f"xyberos-{project_version}.tar.gz"
    assert wheel.is_file(), sorted(p.name for p in DIST.iterdir())
    assert sdist.is_file(), sorted(p.name for p in DIST.iterdir())
    return wheel, sdist


def wheel_names(wheel: Path) -> list[str]:
    with zipfile.ZipFile(wheel) as archive:
        return archive.namelist()


def test_the_wheel_ships_the_package_and_its_marker(artefacts: tuple[Path, Path]) -> None:
    wheel, _ = artefacts

    names = wheel_names(wheel)
    assert "xyberos/__init__.py" in names
    assert "xyberos/py.typed" in names, "the package is typed, so the marker has to ship"
    assert "xyberos/cli/main.py" in names
    assert "xyberos/config.schema.json" in names, (
        "the configuration schema ships in the wheel, which is what lets an editor validate "
        "xyberos.toml with no extension installed"
    )


def test_the_wheel_ships_no_test_or_example_code(artefacts: tuple[Path, Path]) -> None:
    wheel, _ = artefacts

    leaked = [
        name
        for name in wheel_names(wheel)
        if name.startswith(("tests/", "examples/", "docs/")) or "__pycache__" in name
    ]
    assert not leaked, leaked


def test_the_wheel_declares_its_metadata(
    artefacts: tuple[Path, Path], project_version: str
) -> None:
    """Assert on parsed metadata, not on raw text.

    Build backends normalise a specifier's order and a marker's quoting, so matching the file's
    formatting would test the backend rather than this project. The description is checked because
    the README is embedded in it, and text that is stale there ships inside the wheel — which is
    exactly how a wrong licence statement got into an earlier build.
    """
    wheel, _ = artefacts

    with zipfile.ZipFile(wheel) as archive:
        raw = archive.read(f"xyberos-{project_version}.dist-info/METADATA").decode("utf-8")
    message = email.message_from_string(raw)

    assert message["Metadata-Version"] == "2.5"
    assert message["Name"] == "xyberos"
    assert message["Version"] == project_version
    assert message["License-Expression"] == "Apache-2.0"
    assert message["Requires-Python"] == ">=3.10"
    project_urls = dict(
        value.split(", ", maxsplit=1) for value in message.get_all("Project-URL") or []
    )
    assert project_urls == {
        "Documentation": "https://docs.xyberos.com/",
        "Repository": "https://github.com/xyberos/xyberos",
        "Issues": "https://github.com/xyberos/xyberos/issues",
    }
    assert set(message.get_all("Provides-Extra") or []) == {
        "dev",
        "durable",
        "http",
        "database",
        "ollama",
    }
    requirements = message.get_all("Requires-Dist") or []
    assert any(
        requirement.startswith("tomli") and "python_version < '3.11'" in requirement
        for requirement in requirements
    ), requirements
    description = message.get_payload()
    assert isinstance(description, str)
    assert (
        description.strip() == (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8").strip()
    )
    assert "[Apache License 2.0](" in description
    # The description is what the project page renders, where a relative target resolves against the
    # index rather than the repository and 404s. Every link in it has to be absolute.
    relative = re.findall(r"\]\((?!https?://|#|mailto:)[^)\s]*\)", description)
    assert not relative, f"the long description links relative paths: {relative[:5]}"


def test_the_wheel_ships_the_licence(artefacts: tuple[Path, Path], project_version: str) -> None:
    wheel, _ = artefacts

    names = wheel_names(wheel)
    licences = [name for name in names if name.endswith("licenses/LICENSE")]
    assert licences, names
    with zipfile.ZipFile(wheel) as archive:
        text = archive.read(licences[0]).decode("utf-8")

    assert "Apache License" in text
    assert "Version 2.0, January 2004" in text


def test_the_wheel_declares_the_console_script(
    artefacts: tuple[Path, Path], project_version: str
) -> None:
    wheel, _ = artefacts

    with zipfile.ZipFile(wheel) as archive:
        raw = archive.read(f"xyberos-{project_version}.dist-info/entry_points.txt").decode("utf-8")

    parser = ConfigParser()
    parser.read_string(raw)
    assert parser["console_scripts"]["xyberos"] == "xyberos.cli.main:main"


def test_the_sdist_carries_what_a_source_build_needs(artefacts: tuple[Path, Path]) -> None:
    _, sdist = artefacts

    with tarfile.open(sdist) as archive:
        names = archive.getnames()

    roots = {name.split("/", 1)[1] for name in names if "/" in name}
    assert "pyproject.toml" in roots
    assert "src/xyberos/__init__.py" in roots
    assert "LICENSE" in roots
    assert "README.md" in roots
    assert "docs/stability.md" in roots
    assert "tests/test_public_surface.py" in roots


def test_the_sdist_contains_no_build_or_environment_leftovers(artefacts: tuple[Path, Path]) -> None:
    _, sdist = artefacts

    with tarfile.open(sdist) as archive:
        names = archive.getnames()

    leaked = [
        name
        for name in names
        if "__pycache__" in name or name.endswith((".pyc", ".db", ".whl")) or "/.venv/" in name
    ]
    assert not leaked, leaked

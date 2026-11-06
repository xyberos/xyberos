"""The command line does what its options say, and fails in a way a caller can act on.

The commands are tested through ``main`` rather than through a subprocess wherever the behavior is
in-process, because the exit code and the two output streams are the whole contract. The two things
that genuinely need a separate process — a missing server and a real migration — are covered where
they belong: the server hand-off by a fake module, the migration by an actual run against a
temporary database.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from xyberos.cli.check import check
from xyberos.cli.errors import CliError
from xyberos.cli.main import EXIT_OK, main
from xyberos.cli.migrations import migrate, redact, scrub
from xyberos.cli.project import new
from xyberos.cli.scaffold import files_for
from xyberos.cli.server import run
from xyberos.cli.targets import load_target, parse_target

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = REPOSITORY_ROOT / "examples" / "sqlite_crud" / "migrations"


def test_version_is_reported_without_a_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])

    assert exit_info.value.code == 0
    assert "xyberos 2.2.0" in capsys.readouterr().out


def test_no_command_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main([])

    assert exit_info.value.code == 2
    assert "command" in capsys.readouterr().err


def test_help_lists_every_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])

    output = capsys.readouterr().out
    for command in ("check", "new", "run", "migrate"):
        assert command in output


def test_check_without_an_application_reports_settings(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check"]) == EXIT_OK

    output = capsys.readouterr().out
    assert "settings: xyberos (development)" in output
    assert "schema_version 1" in output
    assert "application: not inspected" in output


def test_check_inspects_a_composed_application(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check", "--app", "hello_app.app:create_app"]) == EXIT_OK

    output = capsys.readouterr().out
    assert "provider graph: valid" in output
    assert "Greeter [app] from application" in output
    assert "routes: 2 (handler signatures valid)" in output


def test_check_uses_an_explicit_config_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "xyberos.toml"
    config.write_text('[app]\nname = "checked"\n', encoding="utf-8")

    assert main(["check", "--config", str(config)]) == EXIT_OK

    output = capsys.readouterr().out
    assert "settings: checked (development)" in output
    assert f"config file: {config}" in output


def test_check_fails_when_the_settings_are_invalid(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "xyberos.toml"
    config.write_text('[app]\nname = "checked"\nunknown = 1\n', encoding="utf-8")

    assert main(["check", "--config", str(config)]) == 1

    printed = capsys.readouterr().err
    assert "ConfigurationError" in printed
    assert "unknown" in printed


def test_check_exits_two_when_the_target_is_not_an_application(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["check", "--app", "hello_app.app:asgi_app"]) == 2

    printed = capsys.readouterr().err
    assert "ASGI application, not an App" in printed


def test_check_exits_two_when_the_module_has_no_such_attribute(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["check", "--app", "hello_app.app:missing"]) == 2

    printed = capsys.readouterr().err
    assert "has no attribute 'missing'" in printed
    assert "create_app" in printed


def test_check_exits_two_when_the_target_is_not_importable(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["check", "--app", "no_such_module.app:create_app"]) == 2

    assert "cannot import 'no_such_module.app'" in capsys.readouterr().err


def test_check_reports_a_target_that_needs_arguments(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["check", "--app", "hello_app.app:build_asgi_app"]) == 2

    assert "takes no arguments" in capsys.readouterr().err


def test_check_reports_a_factory_that_returns_something_else(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    package = tmp_path / "src" / "toybad"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "app.py").write_text(
        'def create_app() -> str:\n    return "not an application"\n', encoding="utf-8"
    )

    argv = ["check", "--app", "toybad.app:create_app", "--app-dir", str(tmp_path / "src")]
    assert main(argv) == 2

    assert "returned str, not an App" in capsys.readouterr().err


def test_check_imports_a_src_layout_through_app_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The package name is unique per test on purpose: importing a temporary module puts it in
    # sys.modules for the rest of the session, so two tests sharing a name would share a module.
    package = tmp_path / "src" / "toyvalid"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "app.py").write_text(
        "from xyberos import App\n\n\ndef create_app() -> App:\n    app = App()\n    return app\n",
        encoding="utf-8",
    )

    argv = ["check", "--app", "toyvalid.app:create_app", "--app-dir", str(tmp_path / "src")]
    assert main(argv) == 0

    output = capsys.readouterr().out
    assert "provider graph: valid" in output
    assert "routes: 0" in output


def test_check_reports_a_missing_app_dir(tmp_path: Path) -> None:
    with pytest.raises(CliError) as error:
        check(target="toyvalid.app:create_app", app_dir=tmp_path / "absent")

    assert error.value.exit_code == 2
    assert "is not a directory" in str(error.value)


def test_parse_target_rejects_a_missing_halves() -> None:
    with pytest.raises(CliError):
        parse_target(":create_app")
    with pytest.raises(CliError):
        parse_target("myapp.app:")


def test_parse_target_accepts_a_bare_module() -> None:
    assert parse_target("myapp.app") == ("myapp.app", None)


def test_load_target_returns_the_module_when_no_attribute_is_named() -> None:
    module = load_target("hello_app.app")

    assert module.__name__ == "hello_app.app"


def test_load_target_names_the_extra_that_provides_a_missing_dependency(
    tmp_path: Path,
) -> None:
    """A target that fails on a missing third-party package says which extra provides it.

    The module raises the error itself rather than relying on the package really being absent, so
    the message is asserted deterministically whether or not the extra is installed.
    """
    package = tmp_path / "missingdep"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "app.py").write_text(
        "raise ModuleNotFoundError(\"No module named 'starlette'\", name='starlette')\n",
        encoding="utf-8",
    )

    with pytest.raises(CliError) as error:
        load_target("missingdep.app:create_app", app_dir=tmp_path)

    message = str(error.value)
    assert "No module named 'starlette'" in message
    assert "The 'http' extra provides it" in message
    assert 'pip install "xyberos[http]"' in message


def test_load_target_does_not_invent_an_extra_for_an_unknown_package(tmp_path: Path) -> None:
    package = tmp_path / "missingother"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "app.py").write_text(
        "raise ModuleNotFoundError(\"No module named 'finance'\", name='finance')\n",
        encoding="utf-8",
    )

    with pytest.raises(CliError) as error:
        load_target("missingother.app:create_app", app_dir=tmp_path)

    assert "extra provides it" not in str(error.value)


def test_new_writes_the_project_it_promises(tmp_path: Path) -> None:
    written = new("demo", directory=tmp_path)

    relative = sorted(path.relative_to(tmp_path).as_posix() for path in written)
    assert relative == [
        "demo/.gitignore",
        "demo/README.md",
        "demo/pyproject.toml",
        "demo/src/demo/__init__.py",
        "demo/src/demo/app.py",
        "demo/tests/test_app.py",
        "demo/xyberos.toml",
    ]


def test_new_refuses_a_non_empty_directory(tmp_path: Path) -> None:
    existing = tmp_path / "demo"
    existing.mkdir()
    (existing / "keep.txt").write_text("work", encoding="utf-8")

    with pytest.raises(CliError) as error:
        new("demo", directory=tmp_path)

    assert error.value.exit_code == 2
    assert (existing / "keep.txt").read_text(encoding="utf-8") == "work"


@pytest.mark.parametrize("name", ["Demo", "with-dash", "1demo", ""])
def test_new_rejects_a_name_that_cannot_be_a_package(name: str) -> None:
    with pytest.raises(CliError):
        files_for(name)


def test_the_scaffolded_project_is_importable_and_valid(tmp_path: Path) -> None:
    new("demo", directory=tmp_path)
    sources = (
        tmp_path / "demo" / "src" / "demo" / "app.py",
        tmp_path / "demo" / "tests" / "test_app.py",
    )
    for source in sources:
        ast.parse(source.read_text(encoding="utf-8"))

    report = check(target="demo.app:create_app", app_dir=tmp_path / "demo" / "src")

    assert "provider graph: valid" in report
    assert "routes: 2 (handler signatures valid)" in report


def test_new_reports_what_it_wrote(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    assert main(["new", "demo", "--directory", str(tmp_path)]) == EXIT_OK

    output = capsys.readouterr().out
    assert "created" in output
    assert "src/demo/app.py" in output
    assert "xyberos check --app demo.app:create_app --app-dir src" in output


def test_run_passes_every_option_to_the_server(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(target: str, **options: object) -> None:
        calls.append({"target": target, **options})

    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=fake_run))

    run(
        target="demo.app:asgi_app",
        factory=True,
        host="0.0.0.0",
        port=9000,
        reload=True,
        app_dir=tmp_path,
    )

    assert calls == [
        {
            "target": "demo.app:asgi_app",
            "factory": True,
            "host": "0.0.0.0",
            "port": 9000,
            "reload": True,
            "app_dir": str(tmp_path),
        }
    ]


def test_run_explains_how_to_install_a_server(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class Blocker:
        def find_spec(self, name: str, path: object = None, target: object = None) -> None:
            if name == "uvicorn":
                raise ModuleNotFoundError("No module named 'uvicorn'", name=name)
            return None

    monkeypatch.delitem(sys.modules, "uvicorn", raising=False)
    monkeypatch.setattr(sys, "meta_path", [Blocker(), *sys.meta_path])

    assert main(["run", "--app", "demo.app:asgi_app"]) == 1

    printed = capsys.readouterr().err
    assert "no ASGI server is installed" in printed
    assert "pip install uvicorn" in printed


def test_run_rejects_an_impossible_port() -> None:
    with pytest.raises(CliError) as error:
        run(target="demo.app:asgi_app", port=0)

    assert error.value.exit_code == 2


def test_migrate_reports_a_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(CliError) as error:
        migrate(tmp_path / "absent", url="sqlite:///unused.db")

    assert error.value.exit_code == 2


def test_migrate_applies_revisions_to_a_temporary_database(tmp_path: Path) -> None:
    database = tmp_path / "app.db"

    report = migrate(MIGRATIONS, url=f"sqlite:///{database.as_posix()}")

    assert database.exists()
    assert "applied" in report


def test_migrate_never_prints_a_password() -> None:
    assert (
        redact("postgresql://user:secret@db.example/app") == "postgresql://user:***@db.example/app"
    )
    assert redact("sqlite:///var/app.db") == "sqlite:///var/app.db"


def test_migrate_handles_a_url_a_migration_runner_cannot_interpolate(tmp_path: Path) -> None:
    """A percent sign in the URL used to be a crash, and the crash quoted the whole URL.

    A password is percent-encoded as a matter of course, so this is the ordinary case rather than an
    exotic one; the file-path form is used here because it needs no database server.
    """
    database = tmp_path / "a%b.db"

    report = migrate(MIGRATIONS, url=f"sqlite:///{database.as_posix()}")

    assert database.exists()
    assert "applied" in report


def test_a_failed_migration_never_prints_the_url_or_the_password(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The failure path is where a traceback would otherwise quote the configured value."""
    password = "S3cr3t%40pw"
    url = f"postgresql://user:{password}@db.invalid:5432/app"
    empty = tmp_path / "revisions"
    empty.mkdir()

    assert main(["migrate", "--migrations", str(empty), "--url", url]) == 1

    printed = capsys.readouterr().err
    assert password not in printed
    assert url not in printed
    assert "S3cr3t" not in printed
    assert "migrations failed" in printed


def test_scrub_removes_the_url_and_the_password_in_either_encoding() -> None:
    url = "postgresql://user:S3cr3t%40pw@db.invalid:5432/app"

    assert scrub(f"could not connect to {url}", url) == (
        "could not connect to postgresql://user:***@db.invalid:5432/app"
    )
    assert "S3cr3t%40pw" not in scrub(f"invalid syntax in '{url}'", url)
    assert "S3cr3t@pw" not in scrub("decoded S3cr3t@pw here", url)
    assert scrub("nothing to hide", url) == "nothing to hide"


def test_redact_leaves_a_url_without_a_password_alone() -> None:
    assert redact("postgresql://db.example/app") == "postgresql://db.example/app"
    assert redact("not a url") == "not a url"

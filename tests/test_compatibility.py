"""The frozen surfaces that are not import names: configuration, plugins, and metadata.

Freezing ``__all__`` covers what a user can import. Three more things can change under someone's
feet without any import moving:

* **configuration fields** — a renamed setting silently stops being read, so a deployment keeps
  starting with the wrong values;
* **the plugin protocol** — a removed attribute breaks every out-of-tree plugin at load time;
* **serialized workflow metadata** — the durable fingerprint and journal schema are *persisted*, so
  changing how they are computed invalidates in-flight executions and refuses to resume them.

The fingerprint test is the sharpest of the three: a golden value here means a change to the
fingerprint payload is a deliberate, reviewed edit rather than a silent break.
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Mapping

import pytest

import xyberos
from xyberos import AppSettings, ConfigurationError, Settings, Workflow, load_settings
from xyberos.cli.check import DOCUMENT_VERSION, document
from xyberos.diagnostics import ProviderInfo
from xyberos.durable import JOURNAL_SCHEMA_VERSION, definition_fingerprint
from xyberos.plugins import PLUGIN_API_VERSION, Plugin, PluginInfo, PluginState
from xyberos.runtime.dependencies import ProviderRegistry

# --------------------------------------------------------------------------------------
# Configuration fields
# --------------------------------------------------------------------------------------

# The TOML root keys and the settings record. A key removed here stops being read; a key added here
# is a deliberate compatibility decision, because a deployment's file may already contain it.
CONFIGURATION_ROOT_KEYS = {"schema_version", "app", "plugins", "ai"}
CONFIGURATION_SCHEMA_VERSION = 1
APP_SETTINGS_FIELDS = ("name", "environment", "debug", "shutdown_timeout")
SETTINGS_FIELDS = ("schema_version", "app", "plugins", "ai")
ENVIRONMENT_PREFIX = "XYBEROS_"
NESTED_SEPARATOR = "__"
PLUGIN_STATES = {"registered", "started", "stopped", "failed"}
# `config_type` was added for `check --schema`, which types a plugin's `[plugins.<name>]` section
# from it. The records below are read by `check --json` and `check --why`, so their fields are
# pinned too: a field removed breaks a consumer that never imported anything.
PLUGIN_INFO_FIELDS = {"api_version", "name", "requires", "state", "config_type"}
PROVIDER_INFO_FIELDS = {"contract", "scope", "eager", "source", "dependencies"}
# ClassVar annotations on the base class are the contract a plugin implements: they are declared
# without values, so `hasattr` is false for two of them and the annotation is the real surface.
PLUGIN_REQUIRED_CLASSVARS = {"name", "api_version", "requires", "config_type"}
PLUGIN_HOOKS = {"register", "start", "stop"}
PROVIDER_REGISTRY_MEMBERS = {
    "clone",
    "freeze",
    "frozen",
    "get",
    "providers",
    "register",
    "require",
    "validate",
}

CANONICAL_FINGERPRINT = "3cb37cb41f81982016bfef506c56e197818f7e12b409ab6be564f81539867185"


async def _first(value: object, context: object) -> str:
    return "first"


async def _second(value: str, context: object) -> str:
    return f"second:{value}"


def canonical_workflow(
    *, version: str = "1", metadata: Mapping[str, object] | None = None
) -> Workflow:
    """A definition whose fingerprint is pinned below."""
    return (
        Workflow("canonical", version=version, metadata=metadata or {})
        .step("first", _first)
        .step("second", _second, timeout=5.0)
        .edge("first", "second")
    )


def test_the_configuration_root_keys_are_frozen() -> None:
    """Every documented root key loads, and an undocumented one is still refused."""
    settings = load_settings(environ={}, overrides={"app": {}, "plugins": {}, "ai": {}})

    assert isinstance(settings, Settings)
    assert set(CONFIGURATION_ROOT_KEYS) == {"schema_version", "app", "plugins", "ai"}

    with pytest.raises(ConfigurationError):
        load_settings(environ={}, overrides={"unknown_section": {}})


def test_the_configuration_schema_version_is_frozen() -> None:
    assert Settings.load(environ={}).schema_version == CONFIGURATION_SCHEMA_VERSION


def test_application_setting_fields_and_defaults_are_frozen() -> None:
    names = tuple(field for field in AppSettings.__dataclass_fields__ if not field.startswith("_"))
    settings = Settings.load(environ={})

    assert set(names) == set(APP_SETTINGS_FIELDS)
    assert set(SETTINGS_FIELDS) <= set(Settings.__dataclass_fields__)
    assert (settings.app.name, settings.app.environment, settings.app.debug) == (
        "xyberos",
        "development",
        False,
    )
    assert settings.app.shutdown_timeout is None


def test_the_environment_variable_mapping_is_frozen() -> None:
    """The documented convention is ``XYBEROS_`` plus a ``__``-separated path."""
    environ = {"XYBEROS_APP__DEBUG": "true", "XYBEROS_APP__NAME": "from-env"}
    settings = load_settings(environ=environ)

    assert settings.app.debug is True
    assert settings.app.name == "from-env"
    assert ENVIRONMENT_PREFIX == "XYBEROS_"
    assert NESTED_SEPARATOR == "__"


# --------------------------------------------------------------------------------------
# Plugin protocol
# --------------------------------------------------------------------------------------


def test_the_plugin_api_version_is_frozen() -> None:
    """Plugins declare compatibility against this string, so changing it is a breaking change."""
    assert PLUGIN_API_VERSION == "1"


def test_the_plugin_protocol_requires_the_documented_members() -> None:
    declared = set(getattr(Plugin, "__annotations__", {}))

    assert PLUGIN_REQUIRED_CLASSVARS <= declared, (
        f"Plugin no longer declares {sorted(PLUGIN_REQUIRED_CLASSVARS - declared)}"
    )
    for hook in sorted(PLUGIN_HOOKS):
        assert hasattr(Plugin, hook), f"Plugin no longer declares {hook!r}"
    assert not inspect.iscoroutinefunction(Plugin.register), (
        "Plugin.register is synchronous by contract: the registry calls it during registration"
    )


def test_the_plugin_lifecycle_states_are_frozen() -> None:
    assert {state.value for state in PluginState} == PLUGIN_STATES


def test_the_plugin_information_record_is_frozen() -> None:
    assert set(PluginInfo.__dataclass_fields__) == PLUGIN_INFO_FIELDS


def test_the_provider_information_record_is_frozen() -> None:
    """`check --json` serializes it and `check --why` walks `dependencies`, so both are surface."""
    assert set(ProviderInfo.__dataclass_fields__) == PROVIDER_INFO_FIELDS


def test_the_provider_registry_seams_are_stable() -> None:
    """Diagnostics and tests use these; removing one breaks them without breaking imports."""
    present = {name for name in vars(ProviderRegistry) if not name.startswith("_")}

    assert present == PROVIDER_REGISTRY_MEMBERS, (
        f"ProviderRegistry changed: missing={sorted(PROVIDER_REGISTRY_MEMBERS - present)}, "
        f"added={sorted(present - PROVIDER_REGISTRY_MEMBERS)}"
    )


# --------------------------------------------------------------------------------------
# Serialized workflow metadata
# --------------------------------------------------------------------------------------


def test_the_definition_fingerprint_is_frozen() -> None:
    """A persisted execution resumes only if this still matches, so the value is a promise."""
    assert definition_fingerprint(canonical_workflow()) == CANONICAL_FINGERPRINT


def test_the_fingerprint_ignores_metadata_and_notices_shape() -> None:
    baseline = definition_fingerprint(canonical_workflow())

    with_metadata = canonical_workflow(metadata={"owner": "team"})
    assert definition_fingerprint(with_metadata) == baseline, (
        "metadata is not resumable state, so it must not change the fingerprint"
    )

    renamed = (
        Workflow("canonical", version="1")
        .step("first", _first)
        .step("renamed", _second, timeout=5.0)
        .edge("first", "renamed")
    )
    assert definition_fingerprint(renamed) != baseline, (
        "a step id decides which step runs next, so renaming one must invalidate the fingerprint"
    )

    next_version = canonical_workflow(version="2")
    assert definition_fingerprint(next_version) != baseline, (
        "a new definition version is how a changed workflow is meant to be published"
    )


def test_the_journal_schema_version_is_frozen() -> None:
    """A journal file carries this version, and an older package refuses a newer file."""
    assert JOURNAL_SCHEMA_VERSION == 1


def test_definition_metadata_is_json_serializable() -> None:
    """Definition metadata is persisted in the journal, so it has to round-trip through JSON."""
    metadata = {"owner": "team", "priority": 3, "tags": ["a", "b"]}

    workflow = canonical_workflow(metadata=metadata)

    assert json.loads(json.dumps(dict(workflow.metadata))) == metadata


def test_the_package_version_is_where_the_release_starts() -> None:
    assert xyberos.__version__ == "2.2.0"


# --------------------------------------------------------------------------------------
# Introspection documents
# --------------------------------------------------------------------------------------

# `check --json` is read by scripts, so its top-level keys are an interface. The nested shape is
# pinned beside the code that builds it, in `tests/cli/test_introspection.py`.
INTROSPECTION_DOCUMENT_KEYS = {
    "document",
    "xyberos_version",
    "config_file",
    "settings",
    "application",
}
INTROSPECTION_SETTINGS_KEYS = {"schema_version", "app", "plugins", "ai"}


def test_the_introspection_document_version_is_frozen() -> None:
    """A reader ignores unknown keys, so adding one is additive; changing this is the break."""
    assert DOCUMENT_VERSION == 1


def test_the_introspection_document_keys_are_frozen() -> None:
    body = json.loads(document())

    assert set(body) == INTROSPECTION_DOCUMENT_KEYS
    assert set(body["settings"]) == INTROSPECTION_SETTINGS_KEYS

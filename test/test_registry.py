import pytest

from exceptions import CircularDependencyError, DependencyResolutionError, ServiceNotFoundError
from kernel.registry import ServiceRegistry


class Database:
    pass


class Repository:
    def __init__(self, database):
        self.database = database


def test_registry_registers_instances_and_injects_constructor_dependencies():
    registry = ServiceRegistry()
    database = Database()
    registry.register("database", database)

    repository = registry.inject(Repository)

    assert repository.database is database
    assert registry.resolve("registry") is registry
    assert registry.names == ("registry", "database")


def test_registry_resolves_singleton_and_transient_factories_with_dependencies():
    registry = ServiceRegistry()
    registry.register("prefix", "xyberos")
    calls = []

    def singleton_factory(prefix):
        calls.append(prefix)
        return {"name": prefix}

    registry.register_factory("singleton", singleton_factory)
    registry.register_factory("transient", lambda: object(), singleton=False)

    assert registry.resolve("singleton") is registry.resolve("singleton")
    assert calls == ["xyberos"]
    assert registry.resolve("transient") is not registry.resolve("transient")


def test_registry_reports_missing_dependencies_and_dependency_cycles():
    registry = ServiceRegistry()

    with pytest.raises(DependencyResolutionError, match="missing"):
        registry.inject(lambda missing: missing)
    with pytest.raises(ServiceNotFoundError, match="unknown"):
        registry.resolve("unknown")

    registry.register_factory("first", lambda second: second)
    registry.register_factory("second", lambda first: first)

    with pytest.raises(CircularDependencyError, match="first -> second -> first"):
        registry.resolve("first")


def test_registry_replaces_and_unregisters_services():
    registry = ServiceRegistry()
    registry.register("value", 1)
    registry.register("value", 2, replace=True)

    assert registry.unregister("value") == 2
    assert not registry.contains("value")


def test_registry_supports_overrides_defaults_and_positional_only_dependencies():
    registry = ServiceRegistry()
    registry.register("value", "from-registry")

    def target(value, optional="default", *args, **kwargs):
        return value, optional

    def positional_only(value, /):
        return value

    assert registry.inject(target, value="override") == ("override", "default")
    assert registry.inject(positional_only) == "from-registry"


def test_registry_rejects_invalid_factories_targets_and_reserved_removal():
    registry = ServiceRegistry()

    with pytest.raises(TypeError, match="factory must be callable"):
        registry.register_factory("invalid", None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="target must be callable"):
        registry.inject(None)  # type: ignore[arg-type]
    with pytest.raises(Exception, match="cannot be removed"):
        registry.unregister("registry")

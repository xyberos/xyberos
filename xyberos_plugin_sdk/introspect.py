"""Shared introspection of Xyberos contracts — the "one rule" from ``EXTRA.md``.

Both the generator (``xyberos-cli``) and the validator
(``xyberos-plugin-validator``) derive their definitions from this module so the
two can never drift apart: the core contract is the single source of truth.

- For **ABC** contracts (``Tool``, ``Memory``, ``Knowledge``, ``VectorStore``,
  ``Workflow``, ``Planner``, ``Agent``, ``Plugin``) the abstract member set is
  read from ``__abstractmethods__``.
- For **Protocol** contracts (``LLMProvider``, ``Service``) members are read
  from the protocol's class body.
"""

from __future__ import annotations

import inspect
import types

from xyberos.contracts import (
    Agent,
    Knowledge,
    LLMProvider,
    Memory,
    Planner,
    Plugin,
    Service,
    Tool,
    VectorStore,
    Workflow,
)

#: Plugin type key (used by the CLI wizard and declarative config) -> contract.
CONTRACTS: dict[str, type] = {
    "tool": Tool,
    "llm": LLMProvider,
    "memory": Memory,
    "knowledge": Knowledge,
    "vector": VectorStore,
    "workflow": Workflow,
    "planner": Planner,
    "agent": Agent,
    "service": Service,
    "other": Plugin,
}

#: Human-readable labels for the wizard.
LABELS: dict[str, str] = {
    "tool": "Tool",
    "llm": "LLM Provider",
    "memory": "Memory",
    "knowledge": "Knowledge",
    "vector": "Vector Store",
    "workflow": "Workflow",
    "planner": "Planner",
    "agent": "Agent",
    "service": "Service",
    "other": "Other",
}


def plugin_types() -> list[str]:
    """All supported plugin type keys, in wizard order."""
    return list(CONTRACTS)


def contract_for(plugin_type: str) -> type:
    """Return the contract class for a plugin type key."""
    try:
        return CONTRACTS[plugin_type]
    except KeyError:
        raise ValueError(
            f"unknown plugin type {plugin_type!r}; expected one of {list(CONTRACTS)}"
        ) from None


def is_concrete(cls: type) -> bool:
    """Whether ``cls`` implements every abstract member of its contracts."""
    return isinstance(cls, type) and not bool(getattr(cls, "__abstractmethods__", ()))


def missing_abstracts(cls: type) -> tuple[str, ...]:
    """Abstract member names still unimplemented on ``cls`` (empty == concrete)."""
    return tuple(getattr(cls, "__abstractmethods__", ()))


def abstract_members(contract: type) -> dict[str, str]:
    """Ordered mapping of abstract member name -> kind ('property' | 'method').

    Works for both ABC contracts (``__abstractmethods__``) and
    runtime-checkable Protocol contracts (``LLMProvider``, ``Service``).
    """
    members: dict[str, str] = {}
    abstract = getattr(contract, "__abstractmethods__", ())
    if abstract:
        for name in abstract:
            static = inspect.getattr_static(contract, name)
            members[name] = "property" if isinstance(static, property) else "method"
        return members
    for name, value in vars(contract).items():
        if name.startswith("__"):
            continue
        if isinstance(value, property):
            members[name] = "property"
        elif isinstance(value, (types.FunctionType, staticmethod, classmethod)):
            members[name] = "method"
    return members


def member_signature(contract: type, name: str) -> inspect.Signature | None:
    """Best-effort signature of an abstract member (``None`` for properties)."""
    try:
        raw = inspect.getattr_static(contract, name)
    except AttributeError:
        return None
    if isinstance(raw, property):
        return None
    try:
        return inspect.signature(raw)
    except (TypeError, ValueError):
        return None


def signature_compatible(impl: type, contract: type, name: str) -> bool:
    """Light check: the implementation accepts every *required* abstract param.

    Implementations are allowed to drop optional/varargs parameters and to add
    extra optional ones, but every required positional parameter of the contract
    must still be accepted.
    """
    abstract = member_signature(contract, name)
    if abstract is None:
        return True
    try:
        concrete = inspect.signature(getattr(impl, name))
    except (TypeError, ValueError, AttributeError):
        return False
    for pname, param in abstract.parameters.items():
        if pname == "self":
            continue
        if param.default is not param.empty or param.kind in (
            param.VAR_POSITIONAL,
            param.VAR_KEYWORD,
        ):
            continue  # optional / varargs: an implementer may drop these
        if pname not in concrete.parameters:
            return False
        concrete_param = concrete.parameters[pname]
        if concrete_param.kind in (
            concrete_param.VAR_POSITIONAL,
            concrete_param.VAR_KEYWORD,
        ) or concrete_param.default is not concrete_param.empty:
            return False
    return True


def render_stub(contract: type, name: str, *, name_value: str | None = None, indent: int = 4) -> str:
    """Render an implementable stub line for ``name`` (used by the generator).

    ``name_value`` is used for ``name`` properties so a scaffolded plugin is
    immediately loadable; every other member raises ``NotImplementedError`` so
    the author is forced to implement it before the validator passes.
    """
    pad = " " * indent
    kind = abstract_members(contract).get(name, "method")
    if kind == "property":
        value = name_value if name_value is not None else "..."
        return (
            f"{pad}@property\n"
            f"{pad}def {name}(self) -> object:\n"
            f"{pad}    return {value!r}  # TODO: implement\n"
        )
    # ``object`` annotations keep stubs compilable without any imports.
    return (
        f"{pad}def {name}(self, context: object, **arguments: object) -> object:\n"
        f"{pad}    raise NotImplementedError  # TODO: implement\n"
    )

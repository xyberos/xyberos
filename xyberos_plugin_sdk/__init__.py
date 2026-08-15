"""xyberos-plugin-sdk — typed plugins, declarative loading, and contract introspection.

External, additive tooling layered on the stable Xyberos public API. It never
touches the ``xyberos`` core package.
"""

from . import base, declarative, introspect
from .base import (
    CONTRIBUTE_METHODS,
    AgentPlugin,
    KnowledgePlugin,
    LLMPlugin,
    MemoryPlugin,
    PlannerPlugin,
    ServicePlugin,
    ToolPlugin,
    TypedPlugin,
    VectorPlugin,
    WorkflowPlugin,
)
from .declarative import DeclarativePlugin, load_declarative, register_declarative
from .introspect import (
    CONTRACTS,
    LABELS,
    abstract_members,
    contract_for,
    is_concrete,
    missing_abstracts,
    plugin_types,
    signature_compatible,
)

__all__ = [
    "CONTRACTS",
    "CONTRIBUTE_METHODS",
    "LABELS",
    "AgentPlugin",
    "DeclarativePlugin",
    "KnowledgePlugin",
    "LLMPlugin",
    "MemoryPlugin",
    "PlannerPlugin",
    "ServicePlugin",
    "ToolPlugin",
    "TypedPlugin",
    "VectorPlugin",
    "WorkflowPlugin",
    "abstract_members",
    "base",
    "contract_for",
    "declarative",
    "introspect",
    "is_concrete",
    "load_declarative",
    "missing_abstracts",
    "plugin_types",
    "register_declarative",
    "signature_compatible",
]

__version__ = "0.1.0"

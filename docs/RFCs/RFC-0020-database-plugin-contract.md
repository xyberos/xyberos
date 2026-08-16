# RFC-0020 — Database Plugin Contract

> The DB-agnostic contract for database integrations: **connect → inspect
> schema → query → transform → structured result**. Companion to
> [RFC-0019](RFC-0019-integrations-roadmap.md) (Track D).

| | |
|---|---|
| **Status** | Active |
| **Version** | 1.0 |
| **Applies to** | Database integrations (Track D) — core remains additive-only |
| **Reference impl** | [`db/`](https://github.com/xyberos/xyberos-plugins/tree/master/db) plugin (`xyberos-db`): SQLite (stdlib) + Postgres/MySQL/DuckDB (lazy drivers) |

## 1. Why one contract

Every database integration (SQL, document, graph, analytics) should speak the
same shape so agents, memory, knowledge, and workflows can use "a database"
without caring which one. The contract is intentionally small and
backend-agnostic.

## 2. The contract

```python
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Database(Protocol):
    """connect -> inspect -> query -> structured result."""

    name: str

    def connect(self) -> None: ...
    def list_tables(self) -> list[str]: ...
    def query(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]: ...
    def close(self) -> None: ...
```

- `connect()` — open the connection (lazy, kernel-lifecycle friendly).
- `list_tables()` — inspect the schema (table names).
- `query(sql, params=None)` — return rows as **dicts** (column name → value);
  one shape for SQL, document, and graph backends.
- `close()` — release the connection.

## 3. Transform → structured result

`query` returns `list[dict]`. Backends may add a `transform()` convenience for
common projections, but the contract itself does **not** require it — a plain
query result is already "structured". Follow the existing Xyberos convention:
providers are implementations of the contract, never different architectures
per database.

## 4. Ship location ladder

1. **SQLite** — Core-equivalent (stdlib), reference for parity tests.
2. **Postgres / MySQL / DuckDB** — optional drivers, lazy-imported with a
   clear `ProviderError` when missing (`pip install xyberos-db[postgres]` etc.).
3. **MSSQL / Oracle / Snowflake / Databricks** — community plugins (Track D).

## 5. DoD

- Implements `Database`; no core changes outside this RFC.
- Drivers lazily imported with a clear `ProviderError`.
- Parity smoke tests against the SQLite reference (same contract, same
  behavior).
- Example + docs + status updated in RFC-0019.

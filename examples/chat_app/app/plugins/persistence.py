"""ChatPersistencePlugin: registers app-scoped database services.

This plugin is auto-discovered, not imported by name: ``main.py`` calls
``xyberos.load_plugins_from("app.plugins")``, which scans every module in the
package for concrete ``Plugin`` subclasses and loads them.

Note the split of responsibilities from the earlier architecture discussion:
- App-scoped, reusable services (engine, ORM base) -> registered here with the
  kernel, so anything that needs them can resolve them by name.
- Request-scoped things (a DB *session*) -> still come from FastAPI's
  ``Depends(get_db)``, because a session must not outlive a single request.
"""

from xyberos.contracts import Plugin

from ..db import Base, engine


class ChatPersistencePlugin(Plugin):
    """Registers the database engine and ORM base with the Xyberos kernel."""

    @property
    def name(self) -> str:
        return "chat_persistence"

    def register(self, kernel) -> None:
        kernel.register("db_engine", engine)
        kernel.register("db_base", Base)

    def unregister(self, kernel) -> None:
        kernel.registry.unregister("db_engine")
        kernel.registry.unregister("db_base")

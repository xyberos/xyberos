"""Thread-safe SQLite connection helpers."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Callable


class ThreadLocalSQLite:
    """One :class:`sqlite3.Connection` per thread, opened lazily.

    ``sqlite3`` connections are bound to the thread that created them, so a
    single shared connection raises ``sqlite3.ProgrammingError`` when touched
    from another thread (FastAPI's event loop, thread pools, …). This helper
    keeps one connection per thread — opened on first use and reused — so
    providers stay safe no matter which thread calls them. ``close()`` only
    closes the calling thread's connection; other threads reopen theirs on
    next use.
    """

    def __init__(
        self,
        path: str,
        initialize: Callable[[sqlite3.Connection], None] | None = None,
    ) -> None:
        self._path = path
        self._initialize = initialize
        self._local = threading.local()
        # Open the constructor-thread connection eagerly so the database file
        # and schema exist immediately after construction (some callers rely
        # on the file being present). Other threads still get their own
        # connection on first use.
        self.connection()

    def connection(self) -> sqlite3.Connection:
        """Return the calling thread's connection, opening it on first use."""
        conn: sqlite3.Connection | None = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._path)
            if self._initialize is not None:
                self._initialize(conn)
            self._local.conn = conn
        return conn

    def close(self) -> None:
        """Close the calling thread's connection, if one is open."""
        conn: sqlite3.Connection | None = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

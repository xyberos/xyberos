"""Database module: engine, session factory, and the ORM Base.

This is the single place that owns HOW the app talks to the database.
FastAPI routes never write SQL here -- they ask for a session via ``get_db()``
and hand it to a service (see ``services/chat.py``).

Why a module instead of inline code in routes?
    * Routes stay thin and testable.
    * Swapping SQLite -> PostgreSQL is a one-line change (DATABASE_URL).
    * The same session machinery is reused by every router.
"""

from collections.abc import Generator
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# SQLite for local development. Point this at PostgreSQL in production, e.g.
#   set DATABASE_URL=postgresql+psycopg://user:pass@host:5432/chatdb
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chat.db")

# ``check_same_thread=False`` is required only because FastAPI/uvicorn can hand
# the same SQLite connection to different threads.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class every ORM model in ``models.py`` inherits from."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

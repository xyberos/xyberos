"""FastAPI entrypoint for the chat app example.

Run from ``examples/chat_app`` (with the venv active):
    uvicorn app.main:app --reload

Interactive docs: http://127.0.0.1:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from xyberos import create_app

from .db import Base, engine
from .routers import chat

# Composition root for pluggable services. The persistence plugin is NOT
# imported by name here -- it is auto-discovered by convention (every concrete
# Plugin subclass inside app/plugins) and registered with the kernel.
xyberos = create_app()
xyberos.load_plugins_from("app.plugins")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: create tables on startup. Use Alembic migrations for
    # any real project so schema changes are tracked and versioned.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Xyberos Chat", lifespan=lifespan)
app.include_router(chat.router)


@app.get("/")
def root() -> dict[str, object]:
    return {
        "app": "xyberos-chat",
        "docs": "/docs",
        "websocket": "/api/ws/{conversation_id}",
        "auto_discovered_plugins": list(xyberos.plugins.names),
        "db_engine_registered": xyberos.resolve("db_engine") is not None,
    }

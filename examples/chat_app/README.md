# FastAPI Chat App Example

A real, runnable chat app built on **FastAPI + SQLAlchemy** with the
**Xyberos** framework generating the replies. It answers the architecture
question: *should the database be a module or a service alongside FastAPI?*

**Answer: both.** The database is its own module (`app/db.py`) that owns the
engine/session, and the business logic is a *service* (`ChatService`) that
FastAPI routes call. Routes never touch SQL directly.

## Layout

```
chat_app/
├── app/
│   ├── db.py               # database MODULE: engine, session factory, get_db()
│   ├── models.py           # SQLAlchemy ORM models (User, Conversation, Message)
│   ├── schemas.py          # Pydantic request/response contracts
│   ├── main.py             # FastAPI app + lifespan (creates tables)
│   ├── services/
│   │   └── chat.py         # SERVICE: ChatService (all business logic + DB work)
│   └── routers/
│       └── chat.py         # thin HTTP + WebSocket endpoints
└── requirements.txt
```

```
Client  ->  FastAPI routers  ->  ChatService  ->  SQLAlchemy session  ->  database
             (thin)              (logic)          (from db.get_db)
```

## Setup

```bash
cd examples/chat_app
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
pip install -e ../..     # the xyberos package itself
```

## Run

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive Swagger UI.

## Try it

```bash
# 1. Create a user
curl -X POST http://127.0.0.1:8000/api/users \
     -H "Content-Type: application/json" \
     -d '{"username": "alice"}'

# 2. Start a conversation (use the returned user id)
curl -X POST http://127.0.0.1:8000/api/conversations \
     -H "Content-Type: application/json" \
     -d '{"user_id": 1, "title": "First chat"}'

# 3. Chat (use the returned conversation id)
curl -X POST http://127.0.0.1:8000/api/conversations/1/messages \
     -H "Content-Type: application/json" \
     -d '{"content": "Hello!"}'

# 4. Read history
curl http://127.0.0.1:8000/api/conversations/1/messages
```

### Realtime (WebSocket)

```bash
# One terminal: connect and echo lines
python -m websockets ws://127.0.0.1:8000/api/ws/1
```

Then type a message; the assistant's reply is sent back over the socket.

## Pluggable auto-discovery

The chat app doesn't import its plugin by name. `main.py` calls
`xyberos.load_plugins_from("app.plugins")`, and the kernel auto-discovers every
concrete `Plugin` subclass it finds (`app/plugins/persistence.py`), registering
their services (`db_engine`, `db_base`) with the registry.

Two discovery styles are built into `PluginLoader`:

1. **Convention scan** — walk a package for `Plugin` classes (what this example
   uses). Adding a new module under `app/plugins/` is enough to wire it up:
   ```python
   app.load_plugins_from("app.plugins")
   ```

2. **Entry points** — declare a plugin in your package metadata and it is found
   automatically, no app code change (same mechanism as pytest):
   ```toml
   [project.entry-points."xyberos.plugins"]
   chat = "app.plugins.persistence:ChatPersistencePlugin"
   ```
   ```python
   app.load_entry_points()   # discovers everything installed
   ```

Both are idempotent: re-running discovery never double-registers a plugin.

## Key ideas

- **`db.py` = the database module.** One place owns the engine, `SessionLocal`,
  `Base`, and the `get_db()` FastAPI dependency. Change `DATABASE_URL` to
  switch engines.
- **`ChatService` = the service.** Constructed with a session (`Depends(get_db)`)
  so it's request-scoped and unit-testable without the web layer.
- **`routers/` stay thin.** Parse/validate in, call one service method, return
  the schema. All SQL lives in `models.py` / `ChatService`.
- **Xyberos integration.** `ChatService._generate_reply` falls back to the
  `xyberos.chat()` helper. Swap it for `create_app(llm=...).chat(...)` to bring
  in agents, tools, and memory providers.
- **WebSockets need a fresh session per message** — a long-lived session held
  open for the socket's lifetime is unsafe.

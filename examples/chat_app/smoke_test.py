"""End-to-end smoke test for the chat app example.

Run from ``examples/chat_app`` with the venv active:
    .venv/Scripts/python smoke_test.py        (Windows)
    .venv/bin/python smoke_test.py            (macOS/Linux)

It exercises the DB module + ChatService through the real HTTP layer
(FastAPI TestClient), so a green run means the whole stack is wired up:
routes -> service -> SQLAlchemy -> SQLite.
"""

import os
import tempfile

from fastapi.testclient import TestClient

# Use a throwaway DB so the smoke test never touches chat.db, and delete any
# leftover file from a previous run so the test is always green from scratch.
_db_path = os.path.join(tempfile.gettempdir(), "xyberos_chat_smoke.db").replace("\\", "/")
for _suffix in ("", "-wal", "-shm"):
    try:
        os.remove(_db_path + _suffix)
    except FileNotFoundError:
        pass
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

# Import AFTER setting DATABASE_URL so db.py picks it up.
from app.db import DATABASE_URL  # noqa: E402
from app.main import app, xyberos  # noqa: E402


def main() -> None:
    print(f"using db: {DATABASE_URL}")

    # Using the client as a context manager runs the app's lifespan startup,
    # which is what creates the tables (Base.metadata.create_all).
    with TestClient(app) as client:
        _run_checks(client)
    print("\nSMOKE TEST PASSED")


def _run_checks(client: TestClient) -> None:
    # 0. pluggable auto-discovery: the plugin is found by convention and its
    #    services are registered with the Xyberos kernel -- no manual wiring.
    assert "chat_persistence" in xyberos.plugins.names, xyberos.plugins.names
    assert xyberos.resolve("db_engine") is not None
    assert xyberos.resolve("db_base") is not None
    print("auto_discovery  :", list(xyberos.plugins.names))

    # 1. create a user
    user = client.post("/api/users", json={"username": "alice"}).json()
    assert user["username"] == "alice", user
    print("create_user      :", user["id"], user["username"])

    # 2. start a conversation
    convo = client.post(
        "/api/conversations", json={"user_id": user["id"], "title": "First chat"}
    ).json()
    assert convo["user_id"] == user["id"], convo
    print("create_conversation:", convo["id"], convo["title"])

    # 3. send a message -> should get a persisted user + assistant pair
    chat = client.post(
        f"/api/conversations/{convo['id']}/messages", json={"content": "Hello!"}
    ).json()
    assert chat["user_message"]["role"] == "user"
    assert chat["assistant_message"]["role"] == "assistant"
    assert chat["assistant_message"]["content"], "expected a reply"
    print("send_message     : user ->", chat["user_message"]["content"])
    print("                   reply ->", chat["assistant_message"]["content"])

    # 4. history should contain both messages, oldest first
    history = client.get(f"/api/conversations/{convo['id']}/messages").json()
    assert [m["role"] for m in history] == ["user", "assistant"], history
    print("history          :", [m["role"] for m in history])

    # 5. list conversations for the user
    convos = client.get(f"/api/users/{user['id']}/conversations").json()
    assert len(convos) == 1
    print("list_conversations:", [c["title"] for c in convos])


if __name__ == "__main__":
    main()

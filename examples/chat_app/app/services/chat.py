"""ChatService: the business-logic layer between FastAPI and the database.

This is the "service" answer to the architecture question. Routes stay thin:
they validate the request (schemas) and call one method here. All database
work and the reply-generation step live in this class so they can be unit
tested without the web layer.

A session is passed in (via FastAPI's ``Depends(get_db)``) instead of the
service creating its own -- that keeps it request-scoped and easy to test.
"""

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Conversation, Message, User
from ..schemas import ChatResponse, MessageOut

# An optional callable that turns a prompt into a reply. Defaults to the
# Xyberos ``chat()`` helper when nothing is injected.
LLM = Callable[[str], str]


class ChatService:
    """Owns all chat persistence plus the reply-generation step."""

    def __init__(self, db: Session, llm: LLM | None = None) -> None:
        self.db = db
        self._llm = llm

    # --- users ---------------------------------------------------------
    def create_user(self, username: str) -> User:
        user = User(username=username)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    # --- conversations -------------------------------------------------
    def create_conversation(self, user_id: int, title: str = "New chat") -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def list_conversations(self, user_id: int) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    # --- messages ------------------------------------------------------
    def history(self, conversation_id: int, limit: int = 50) -> list[Message]:
        """Most recent messages first, oldest -> newest within the window."""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))[::-1]

    def send(self, conversation_id: int, content: str) -> ChatResponse:
        """Persist the user's message, generate a reply, and persist that too."""
        user_message = self._save(conversation_id, "user", content)
        reply_text = self._generate_reply(content)
        assistant_message = self._save(conversation_id, "assistant", reply_text)
        return ChatResponse(
            user_message=MessageOut.model_validate(user_message),
            assistant_message=MessageOut.model_validate(assistant_message),
        )

    # --- internals -----------------------------------------------------
    def _save(self, conversation_id: int, role: str, content: str) -> Message:
        message = Message(conversation_id=conversation_id, role=role, content=content)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def _generate_reply(self, user_content: str) -> str:
        if self._llm is not None:
            return self._llm(user_content)
        # Default: the Xyberos one-liner. Swap for create_app(llm=...).chat(...)
        # if you want tools/agents/memory wired in.
        from xyberos import chat

        return chat(user_content)

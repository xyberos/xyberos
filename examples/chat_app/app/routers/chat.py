"""Chat routes. Deliberately thin: validate in, call the service, return out."""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ..db import SessionLocal, get_db
from ..models import Conversation, Message, User
from ..schemas import (
    ChatResponse,
    ConversationCreate,
    ConversationOut,
    MessageCreate,
    MessageOut,
    UserCreate,
    UserOut,
)
from ..services.chat import ChatService

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/users", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    return ChatService(db).create_user(payload.username)


@router.post("/conversations", response_model=ConversationOut)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)) -> Conversation:
    return ChatService(db).create_conversation(payload.user_id, payload.title)


@router.get("/users/{user_id}/conversations", response_model=list[ConversationOut])
def list_conversations(user_id: int, db: Session = Depends(get_db)) -> list[Conversation]:
    return ChatService(db).list_conversations(user_id)


@router.post("/conversations/{conversation_id}/messages", response_model=ChatResponse)
def send_message(
    conversation_id: int, payload: MessageCreate, db: Session = Depends(get_db)
) -> ChatResponse:
    return ChatService(db).send(conversation_id, payload.content)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def get_history(
    conversation_id: int, limit: int = 50, db: Session = Depends(get_db)
) -> list[Message]:
    return ChatService(db).history(conversation_id, limit)


@router.websocket("/ws/{conversation_id}")
async def chat_ws(websocket: WebSocket, conversation_id: int) -> None:
    """Realtime chat: every client message gets a persisted assistant reply.

    A fresh DB session is opened per message (request-scoped), because holding
    one session open for the life of a WebSocket is unsafe across threads.
    """
    await websocket.accept()
    try:
        while True:
            content = await websocket.receive_text()
            with SessionLocal() as db:
                response = ChatService(db).send(conversation_id, content)
            await websocket.send_text(response.assistant_message.content)
    except WebSocketDisconnect:
        return

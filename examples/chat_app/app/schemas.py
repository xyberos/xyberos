"""Pydantic schemas: the API contract between clients and the server.

``model_config = ConfigDict(from_attributes=True)`` lets FastAPI serialize
ORM objects straight into these response models.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    username: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    created_at: datetime


class ConversationCreate(BaseModel):
    user_id: int
    title: str = "New chat"


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    title: str
    created_at: datetime


class MessageCreate(BaseModel):
    content: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut

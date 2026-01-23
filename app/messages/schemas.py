"""Messages schemas"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel
from tortoise.contrib.pydantic import pydantic_model_creator

from app.accounts.schemas import AccountRead
from app.base.schemas import FileOut
from app.messages.models import Message, Chat


# Auto-generated Pydantic models from Tortoise models
MessageRead = pydantic_model_creator(
    Message,
    name="MessageRead",
    exclude_readonly=False,
)

ChatRead = pydantic_model_creator(
    Chat,
    name="ChatRead",
    exclude_readonly=False,
)

# Message Schemas


class MessageCreate(BaseModel):
    """Schema for creating a new message/conversation"""
    user2_id: UUID  # user1 will be the authenticated user


class DirectMessageCreate(BaseModel):
    """Schema for starting a direct message conversation"""
    participant_id: UUID  # The other participant (current user is automatically added)


class GroupMessageCreate(BaseModel):
    """Schema for creating a group message conversation"""
    name: str  # Name of the group
    # List of participant IDs (current user is automatically added)
    participant_ids: List[UUID]


class MessageDetail(BaseModel):
    """Detailed message schema with related data"""
    id: UUID
    name: Optional[str] = None
    participants: List[AccountRead]
    last_chat: Optional[ChatRead] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


# Chat Schemas
class ChatCreate(BaseModel):
    """Schema for creating a new chat message"""
    message_id: UUID
    value: str
    file_id: Optional[int] = None


class ChatUpdate(BaseModel):
    """Schema for updating a chat message"""
    value: Optional[str] = None
    file_id: Optional[int] = None


class ChatDetail(BaseModel):
    """Detailed chat schema with related data"""
    id: UUID
    message_id: UUID
    sender: AccountRead
    value: str
    file: Optional[FileOut] = None
    meeting_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True


# Custom Schemas
class MessageWithChatDetail(BaseModel):
    """Detailed message schema with related data"""
    id: UUID
    participants: List[AccountRead]
    last_20_chats: Optional[List[ChatDetail]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config"""
        from_attributes = True

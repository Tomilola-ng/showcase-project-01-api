"""Messages models"""

import uuid

from enum import Enum
from tortoise import fields, models


class MessageStatus(Enum):
    """Message status enum"""
    OPEN = "open"
    CLOSED = "closed"


class Message(models.Model):
    """
    Table: messages
    Represents a conversation between users
    """

    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    status = fields.CharEnumField(
        MessageStatus, max_length=20, default=MessageStatus.OPEN
    )
    name = fields.CharField(max_length=255, null=True, default="Message Name")

    # Relationships - participants in the conversation
    participants = fields.ManyToManyField(
        "models.Account",
        related_name="conversations",
        through="message_participants",
    )

    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        """Meta class for Message model"""
        table = "messages"
        indexes = [
            ("created_at",),
        ]

    def __str__(self):
        """String representation of Message"""
        return f"Message {self.id}"


class Chat(models.Model):
    """
    Table: chats
    Represents individual chat messages within a conversation
    """

    id = fields.UUIDField(pk=True, default=uuid.uuid4)

    # Relationship to the parent message/conversation
    message = fields.ForeignKeyField(
        "models.Message",
        related_name="chats",
        on_delete=fields.CASCADE,
    )

    # Sender of this specific chat
    sender = fields.ForeignKeyField(
        "models.Account",
        related_name="sent_chats",
        on_delete=fields.CASCADE,
    )

    # Core chat data
    value = fields.TextField()  # The actual message content

    # Optional file reference
    file = fields.ForeignKeyField(
        "models.FileAsset",
        related_name="chats",
        on_delete=fields.SET_NULL,
        null=True,
    )

    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        """Meta class for Chat model"""
        table = "chats"
        indexes = [
            ("message_id",),
            ("sender_id",),
            ("created_at",),
        ]

    def __str__(self):
        """String representation of Chat"""
        return f"Chat from {self.sender.id} in {self.message.id}"

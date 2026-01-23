"""Message Routes"""

from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    status,
    HTTPException,
    Depends,
    Query
)
from fastapi.security import HTTPBearer

from app.accounts.models import Account
from app.accounts.auth import get_current_user
from app.messages.models import Message, Chat
from app.messages.schemas import (
    ChatRead, MessageDetail, ChatDetail, MessageWithChatDetail, ChatUpdate,
    DirectMessageCreate, GroupMessageCreate)
from app.base.models import FileAsset
from app.config.settings import settings

security = HTTPBearer()
router = APIRouter(prefix="/messages", tags=["Messages"])


async def create_message(
    participants: list[Account],
    sender: Account,
    name: str,
):
    """
    Create a new message/conversation and send the first chat.

    - participants: List of users in the conversation
    - value: The message text
    - sender: The user sending the message
    - file: Optional file attachment
    """
    # Check if conversation already exists between these users (M2M)
    # Approach: Get all messages for sender, prefetch participants, check sets.

    message = await Message.create(name=name)
    await message.participants.add(*participants)

    # Create the first chat message
    chat = await Chat.create(
        message=message,
        sender=sender,
        value="Conversation started",
    )

    # Reload message with relations
    message = await Message.get(id=message.id).prefetch_related(
        "participants", "participants__image"
    )

    return MessageDetail(
        id=message.id,
        name=message.name,
        participants=list(message.participants),
        last_chat=ChatRead.model_validate(chat) if chat else None,
        created_at=message.created_at,
        updated_at=message.updated_at
    )


async def find_existing_direct_message(user1_id: UUID, user2_id: UUID) -> Optional[Message]:
    """
    Find an existing direct message conversation between two users.

    Returns the existing message if found, None otherwise.
    """
    # Get all messages where user1 is a participant
    messages = await Message.filter(
        participants__id=user1_id
    ).prefetch_related("participants")

    # Check each message to see if it has exactly 2 participants (user1 and user2)
    for message in messages:
        participant_ids = {p.id for p in message.participants}
        if len(participant_ids) == 2 and user1_id in participant_ids and user2_id in participant_ids:
            return message

    return None


@router.post(
    "/direct",
    response_model=MessageDetail,
    status_code=status.HTTP_201_CREATED
)
async def start_direct_message(
    data: DirectMessageCreate,
    current_user: Account = Depends(get_current_user)
):
    """
    Start a direct message conversation with another user.

    - If a direct message already exists between the two users, returns the existing one
    - If not, creates a new direct message conversation
    - Automatically includes the current user as a participant
    """
    # Validate that participant is not the current user
    if data.participant_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot start a direct message with yourself"
        )

    # Check if participant exists
    participant = await Account.get_or_none(id=data.participant_id)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )

    # Check if a direct message already exists
    existing_message = await find_existing_direct_message(
        current_user.id,
        data.participant_id
    )

    if existing_message:
        # Reload with relations and get last chat
        existing_message = await Message.get(id=existing_message.id).prefetch_related(
            "participants", "participants__image"
        )

        # Get last chat
        last_chat = await Chat.filter(
            message_id=existing_message.id
        ).order_by("-created_at").first()

        return MessageDetail(
            id=existing_message.id,
            name=existing_message.name,
            participants=list(existing_message.participants),
            last_chat=ChatRead.model_validate(
                last_chat) if last_chat else None,
            created_at=existing_message.created_at,
            updated_at=existing_message.updated_at
        )

    # Create new direct message
    # Generate name from participant names
    participant_name = f"{participant.first_name} {participant.last_name}".strip(
    )
    current_user_name = f"{current_user.first_name} {current_user.last_name}".strip(
    )
    message_name = f"{current_user_name} and {participant_name}"

    return await create_message(
        participants=[current_user, participant],
        sender=current_user,
        name=message_name
    )


@router.post(
    "/group",
    response_model=MessageDetail,
    status_code=status.HTTP_201_CREATED
)
async def create_group_message(
    data: GroupMessageCreate,
    current_user: Account = Depends(get_current_user)
):
    """
    Create a group message conversation with multiple participants.

    - Requires a group name
    - Requires at least one other participant (in addition to current user)
    - Automatically includes the current user as a participant
    - Validates that all participant IDs exist
    """
    # Validate that there's at least one other participant
    if not data.participant_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one participant is required"
        )

    # Remove duplicates and ensure current user is included
    unique_participant_ids = list(set(data.participant_ids))
    if current_user.id not in unique_participant_ids:
        unique_participant_ids.append(current_user.id)

    # Validate that all participants exist
    participants = []
    for participant_id in unique_participant_ids:
        participant = await Account.get_or_none(id=participant_id)
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Participant with ID {participant_id} not found"
            )
        participants.append(participant)

    # Validate group name
    if not data.name or not data.name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group name is required"
        )

    # Create the group message
    return await create_message(
        participants=participants,
        sender=current_user,
        name=data.name.strip()
    )


@router.get(
    "/list",
    response_model=list[MessageDetail]
)
async def list_messages(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Account = Depends(get_current_user)
):
    """
    List all conversations for the current user.

    - Shows all messages where user is a participant
    - Paginated results
    """
    offset = (page - 1) * page_size

    messages = await Message.filter(
        participants__id=current_user.id
    ).offset(offset).limit(page_size).prefetch_related(
        "participants", "participants__image"
    ).order_by("-updated_at")

    # Get last chat for each message
    message_ids = [msg.id for msg in messages]
    all_chats = await Chat.filter(
        message_id__in=message_ids
    ).order_by("-created_at")

    # Keep only the most recent chat for each message
    last_chat_map = {}
    for chat in all_chats:
        if chat.message_id not in last_chat_map:
            last_chat_map[chat.message_id] = chat

    return [
        MessageDetail(
            id=msg.id,
            name=msg.name,
            participants=list(msg.participants),
            last_chat=ChatRead.model_validate(last_chat_map.get(
                msg.id)) if last_chat_map.get(msg.id) else None,
            created_at=msg.created_at,
            updated_at=msg.updated_at
        )
        for msg in messages
    ]


@router.get(
    "/{message_id}",
    response_model=MessageWithChatDetail
)
async def get_message(
    message_id: UUID,
    current_user: Account = Depends(get_current_user)
):
    """
    Get a specific message/conversation.

    - User must be a participant in the conversation
    """
    message = await Message.get_or_none(id=message_id).prefetch_related(
        "participants", "participants__image"
    )

    if not message:
        raise HTTPException(
            status_code=404,
            detail="Message not found"
        )

    # Check authorization
    participant_ids = [p.id for p in message.participants]
    if current_user.id not in participant_ids:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view this message"
        )

    # Get last 20 chats for this message
    chats = await Chat.filter(
        message_id=message_id
    ).order_by("-created_at").limit(20).select_related(
        "sender", "file", "sender__image", "meeting"
    )

    return MessageWithChatDetail(
        id=message.id,
        participants=list(message.participants),
        last_20_chats=[
            ChatDetail(
                id=chat.id,
                message_id=chat.message_id,
                sender=chat.sender,
                value=chat.value,
                file=chat.file,
                meeting_id=chat.meeting_id if chat.meeting else None,
                created_at=chat.created_at,
                updated_at=chat.updated_at
            )
            for chat in chats
        ],
        created_at=message.created_at,
        updated_at=message.updated_at
    )


@router.get(
    "/{message_id}/chats",
    response_model=list[ChatDetail]
)
async def get_message_chats(
    message_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: Account = Depends(get_current_user)
):
    """
    Get all chats for a specific message/conversation.

    - User must be part of the conversation
    - Paginated results
    """
    message = await Message.get_or_none(id=message_id).prefetch_related("participants")

    if not message:
        raise HTTPException(
            status_code=404,
            detail="Message not found"
        )

    # Check authorization
    participant_ids = [p.id for p in message.participants]
    if current_user.id not in participant_ids:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view this message"
        )

    offset = (page - 1) * page_size

    chats = await Chat.filter(
        message_id=message_id
    ).offset(offset).limit(page_size).select_related(
        "sender", "file", "sender__image", "meeting"
    ).order_by("-created_at")

    return [
        ChatDetail(
            id=chat.id,
            message_id=chat.message_id,
            sender=chat.sender,
            value=chat.value,
            file=chat.file,
            meeting_id=chat.meeting_id if chat.meeting else None,
            created_at=chat.created_at,
            updated_at=chat.updated_at
        )
        for chat in chats
    ]


@router.patch(
    "/chats/{chat_id}",
    response_model=ChatDetail
)
async def edit_chat(
    chat_id: UUID,
    data: ChatUpdate,
    current_user: Account = Depends(get_current_user)
):
    """
    Edit a chat message.

    - User must be the sender of the chat
    - Can update value, file_id
    """
    # Get the chat with related data
    chat = await Chat.get_or_none(id=chat_id).select_related(
        "sender", "file", "sender__image", "meeting"
    )

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    # Check authorization - only sender can edit
    if chat.sender_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to edit this chat"
        )

    # Update fields if provided
    if data.value is not None:
        chat.value = data.value

    if data.file_id is not None:
        # Verify file exists
        file_asset = await FileAsset.get_or_none(id=data.file_id)
        if file_asset:
            chat.file = file_asset
        else:
            raise HTTPException(
                status_code=404,
                detail="File not found"
            )

    # Save changes
    await chat.save()

    # Reload with relations for response
    chat = await Chat.get(id=chat_id).select_related(
        "sender", "file", "sender__image", "meeting"
    )

    return ChatDetail(
        id=chat.id,
        message_id=chat.message_id,
        sender=chat.sender,
        value=chat.value,
        file=chat.file,
        meeting_id=chat.meeting_id if chat.meeting else None,
        created_at=chat.created_at,
        updated_at=chat.updated_at
    )


@router.delete(
    "/{message_id}",
    status_code=status.HTTP_200_OK
)
async def delete_message(
    message_id: UUID,
    current_user: Account = Depends(get_current_user)
):
    """
    Delete a message/conversation and all associated chats.

    - Only available in local environment (not production)
    - User must be a participant in the conversation
    - Deletes all chats and activities associated with the message
    """
    # Check if environment is local
    if settings.ENVIRONMENT != "local":
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only available in local environment"
        )

    message = await Message.get_or_none(id=message_id).prefetch_related("participants")

    if not message:
        raise HTTPException(
            status_code=404,
            detail="Message not found"
        )

    # Check authorization
    participant_ids = [p.id for p in message.participants]
    if current_user.id not in participant_ids:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to delete this message"
        )

    # Delete all associated chats (will cascade delete via foreign key)
    await Chat.filter(message_id=message_id).delete()

    # Delete the message
    await message.delete()

    return {
        "success": True,
        "message": "Message and all associated chats deleted successfully",
        "message_id": message_id
    }

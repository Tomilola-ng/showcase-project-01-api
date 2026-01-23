"""WebSocket logic for real-time chat"""

import json
from typing import Dict, List
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from tortoise.exceptions import DoesNotExist

from app.messages.models import Message, Chat
from app.accounts.models import Account


class ConnectionManager:
    """Manages WebSocket connections for chat"""

    def __init__(self):
        # Maps message_id -> list of WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, message_id: str):
        """Accept and store a WebSocket connection"""
        await websocket.accept()

        if message_id not in self.active_connections:
            self.active_connections[message_id] = []

        self.active_connections[message_id].append(websocket)
        print(
            f"[WebSocket] User connected to message {message_id}. Active connections: {len(self.active_connections[message_id])}")

    def disconnect(self, websocket: WebSocket, message_id: str):
        """Remove a WebSocket connection"""
        if message_id in self.active_connections:
            try:
                self.active_connections[message_id].remove(websocket)
                print(
                    f"[WebSocket] User disconnected from message {message_id}. Remaining: {len(self.active_connections[message_id])}")
            except ValueError:
                # Connection already removed
                pass

            # Clean up empty message rooms
            if not self.active_connections[message_id]:
                del self.active_connections[message_id]

    async def send_personal_message(self, message: dict, websocket: WebSocket) -> bool:
        """Send a message to a specific WebSocket. Returns True if successful, False otherwise."""
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            print(f"[WebSocket] Failed to send personal message: {str(e)}")
            return False

    async def broadcast_to_message(self, message: dict, message_id: str):
        """Broadcast a message to all connections in a message room"""
        if message_id not in self.active_connections:
            return

        # Create a copy of the connections list to avoid modification during iteration
        connections = self.active_connections[message_id].copy()
        dead_connections = []

        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(
                    f"[WebSocket] Failed to broadcast to connection: {str(e)}")
                # Mark connection as dead for cleanup
                dead_connections.append(connection)

        # Clean up dead connections
        for dead_conn in dead_connections:
            self.disconnect(dead_conn, message_id)


# Global connection manager instance
manager = ConnectionManager()


async def verify_user_in_message(user_id: UUID, message_id: UUID) -> bool:
    """Verify that a user is part of a message/conversation"""
    try:
        message = await Message.get(id=message_id).prefetch_related("participants")
        participant_ids = [p.id for p in message.participants]
        return user_id in participant_ids
    except DoesNotExist:
        return False


async def handle_chat_message(
    data: dict,
    message_id: UUID,
    user: Account,
    websocket: WebSocket
):
    """Handle incoming chat message from WebSocket"""

    # Validate message data
    if "value" not in data:
        await manager.send_personal_message(
            {"error": "Message value is required"},
            websocket
        )
        return

    # Verify user is part of the conversation
    if not await verify_user_in_message(user.id, message_id):
        await manager.send_personal_message(
            {"error": "Not authorized for this conversation"},
            websocket
        )
        return

    # Create chat message
    chat = await Chat.create(
        message_id=message_id,
        sender_id=user.id,
        value=data["value"],
        file_id=data.get("file_id"),
    )

    # Prepare response
    response = {
        "type": "chat",
        "id": str(chat.id),
        "message_id": str(chat.message_id),
        "sender_id": str(chat.sender_id),
        "value": chat.value,
        "file_id": chat.file_id if chat.file_id else None,
        "created_at": chat.created_at.isoformat(),
    }

    # Broadcast to all connections in this message room
    await manager.broadcast_to_message(response, str(message_id))


async def handle_websocket_connection(
    websocket: WebSocket,
    message_id: str,
    user: Account
):
    """Main WebSocket connection handler"""

    # Verify message exists and user has access
    try:
        message_uuid = UUID(message_id)
    except ValueError:
        print(f"[WebSocket] Invalid message ID format: {message_id}")
        await websocket.close(code=1008, reason="Invalid message ID")
        return

    if not await verify_user_in_message(user.id, message_uuid):
        print(
            f"[WebSocket] User {user.id} not authorized for message {message_id}")
        await websocket.close(code=1008, reason="Not authorized")
        return

    # Connect the WebSocket
    await manager.connect(websocket, message_id)

    # Send connection confirmation
    await manager.send_personal_message(
        {
            "type": "connected",
            "message_id": message_id,
            "user_id": str(user.id)
        },
        websocket
    )

    try:
        while True:
            # Receive message from WebSocket
            data = await websocket.receive_text()
            print(
                f"[WebSocket] Received data from user {user.id}: {data[:100]}...")

            try:
                message_data = json.loads(data)
                await handle_chat_message(
                    message_data,
                    message_uuid,
                    user,
                    websocket
                )
            except json.JSONDecodeError as e:
                print(f"[WebSocket] JSON decode error: {str(e)}")
                await manager.send_personal_message(
                    {"error": "Invalid JSON format"},
                    websocket
                )
            except Exception as e:
                # Catch any other errors from handle_chat_message
                print(f"[WebSocket] Error handling chat message: {str(e)}")
                # Try to send error, but don't fail if websocket is closing
                await manager.send_personal_message(
                    {"error": f"Failed to process message: {str(e)}"},
                    websocket
                )

    except WebSocketDisconnect:
        print(
            f"[WebSocket] User {user.id} disconnected from message {message_id}")
    except Exception as e:
        print(f"[WebSocket] Unexpected error in connection handler: {str(e)}")
    finally:
        # Always cleanup the connection
        manager.disconnect(websocket, message_id)
        # Broadcast that user left
        await manager.broadcast_to_message(
            {
                "type": "user_disconnected",
                "user_id": str(user.id)
            },
            message_id
        )

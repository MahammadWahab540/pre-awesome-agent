from typing import Dict
from fastapi import WebSocket
import logging
import asyncio

# Setup logging
logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages active WebSocket connections mapped by session ID.
    Allows tools and other services to push updates to specific clients.
    """
    def __init__(self):
        # Map session_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """Register a new connection."""
        self.active_connections[session_id] = websocket
        logger.info(f"🔌 Registered WebSocket connection for Session ID: {session_id}")

    def disconnect(self, session_id: str):
        """Remove a connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"🔌 Unregistered WebSocket connection for Session ID: {session_id}")

    async def send_json(self, session_id: str, message: dict):
        """Send a JSON message to a specific session."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_json(message)
                logger.info(f"📤 Sent message to session {session_id}: {message.get('type', 'unknown')}")
            except Exception as e:
                logger.error(f"❌ Failed to send message to session {session_id}: {e}")
                # Optional: Disconnect if broken?
        else:
            logger.warning(f"⚠️ Attempted to send to non-existent session: {session_id}")

    async def send_stage_update(self, session_id: str, stage_index: int):
        """Helper to send a standard stage update message."""
        payload = {
            "type": "stage_update",
            "current_stage": stage_index
        }
        await self.send_json(session_id, payload)

# Global singleton instance
manager = ConnectionManager()

import asyncio
from typing import Dict, Optional
from fastapi import WebSocket
import logging

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
        """Register a new connection, replacing any existing session socket."""
        existing = self.active_connections.get(session_id)
        if existing and existing is not websocket:
            logger.warning(
                "Replacing existing WebSocket for Session ID: %s (ghost session cleanup)",
                session_id,
            )
            try:
                await existing.send_json(
                    {
                        "type": "session_reset",
                        "reason": "A new connection replaced this session.",
                    }
                )
            except Exception:
                # Existing socket may already be half-closed.
                pass

            try:
                await existing.close(code=1008, reason="Session replaced by newer connection")
            except Exception:
                pass

        self.active_connections[session_id] = websocket
        logger.info("Registered WebSocket connection for Session ID: %s", session_id)

    def disconnect(self, session_id: str, websocket: Optional[WebSocket] = None):
        """Remove a connection if it matches the currently active socket."""
        current = self.active_connections.get(session_id)
        if not current:
            return

        if websocket is not None and current is not websocket:
            logger.info("Skipping disconnect for stale socket on Session ID: %s", session_id)
            return

        del self.active_connections[session_id]
        logger.info("Unregistered WebSocket connection for Session ID: %s", session_id)

    async def send_json(self, session_id: str, message: dict):
        """Send a JSON message to a specific session."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_json(message)
                logger.info(
                    "Sent message to session %s: %s",
                    session_id,
                    message.get("type", "unknown"),
                )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Failed to send message to session %s: %s", session_id, e)
        else:
            logger.warning("Attempted to send to non-existent session: %s", session_id)

    async def send_stage_update(self, session_id: str, stage_index: int):
        """Helper to send a standard stage update message."""
        payload = {
            "type": "stage_update",
            "current_stage": stage_index,
        }
        await self.send_json(session_id, payload)


# Global singleton instance
manager = ConnectionManager()

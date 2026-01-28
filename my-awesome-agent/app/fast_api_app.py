"""FastAPI application with ADK Bidi-streaming."""

import asyncio
import json
import logging
import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import socket

import backoff
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from google.adk.agents.live_request_queue import LiveRequest, LiveRequestQueue
from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService, InMemorySessionService
from google.cloud import logging as google_cloud_logging
from pydantic import BaseModel
from vertexai.agent_engines import _utils
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.genai import types
from google.genai.types import ContextWindowCompressionConfig, SlidingWindow
from websockets.exceptions import ConnectionClosedError

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")

from .agent import app as adk_app
from .connection_manager import manager as connection_manager

# Logging setup
if os.environ.get("K_SERVICE"):
    logging_client = google_cloud_logging.Client()
    logging_client.setup_logging()
else:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="NxtGig AI Accelerator", version="2.0.0")

# CORS
cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:9002,https://nxtgig.tech").split(",")]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Session Service
CLOUD_SQL_CONNECTION_NAME = os.getenv("CLOUD_SQL_CONNECTION_NAME", "kossip-helpers-270615:asia-south1:dev-query")
DB_USER = os.getenv("DB_USER", "adk_sessions_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "(;G*&ftrQ}Bd(\"iQ")
DB_NAME = os.getenv("DB_NAME", "adk_sessions")
CLOUD_SQL_PROXY_PORT = os.getenv("CLOUD_SQL_PROXY_PORT", "3308")
USE_CLOUD_SQL = os.getenv("USE_CLOUD_SQL", "false").lower() == "true"

try:
    if USE_CLOUD_SQL:
        if os.environ.get("K_SERVICE"):
            DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@/{DB_NAME}?unix_socket=/cloudsql/{CLOUD_SQL_CONNECTION_NAME}"
        else:
             # Fail fast if local proxy not running
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                if s.connect_ex(('localhost', int(CLOUD_SQL_PROXY_PORT))) != 0:
                     raise Exception(f"Port {CLOUD_SQL_PROXY_PORT} not open")
            DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@localhost:{CLOUD_SQL_PROXY_PORT}/{DB_NAME}"
        
        session_service = DatabaseSessionService(db_url=DATABASE_URL)
        logger.info("DatabaseSessionService initialized")
    else:
        raise Exception("USE_CLOUD_SQL is not true")
except Exception as e:
    logger.warning(f"DatabaseSessionService failed or disabled, using InMemorySessionService: {e}")
    session_service = InMemorySessionService()

# Artifact Service
logs_bucket_name = os.getenv("LOGS_BUCKET_NAME")
artifact_service = GcsArtifactService(bucket_name=logs_bucket_name) if logs_bucket_name else InMemoryArtifactService()

# Memory Service
memory_service = InMemoryMemoryService()

# Runner
runner = Runner(
    app=adk_app,
    session_service=session_service,
    artifact_service=artifact_service,
    memory_service=memory_service,
)

logger.info(f"App initialized: {adk_app.name}, Agent: {adk_app.root_agent.name}")


class AgentSession:
    """Manages bidirectional communication between client and agent."""

    def __init__(self, websocket: WebSocket) -> None:
        self.websocket = websocket
        self.input_queue: asyncio.Queue[dict] = asyncio.Queue()
        self.user_id: str | None = None
        self.project_id: str | None = None
        self.session_id: str | None = None

    async def receive_from_client(self) -> None:
        """Listen for messages from client and queue them."""
        while True:
            try:
                message = await self.websocket.receive()

                if "text" in message:
                    data = json.loads(message["text"])
                    if isinstance(data, dict):
                        # Skip setup messages - they're for backend logging only
                        if "setup" in data:
                            # Extract project_id from setup if available
                            if "project_id" in data:
                                self.project_id = data["project_id"]
                                logger.info(f"📌 Project ID set from setup: {self.project_id}")
                            elif "setup" in data and isinstance(data["setup"], dict) and "project_id" in data["setup"]:
                                self.project_id = data["setup"]["project_id"]
                                logger.info(f"📌 Project ID set from setup.project_id: {self.project_id}")
                            continue
                        await self.input_queue.put(data)

                elif "bytes" in message:
                    await self.input_queue.put({"binary_data": message["bytes"]})

            except (ConnectionClosedError, WebSocketDisconnect):
                logger.info(f"Client disconnected: {self.session_id}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {e}")
                break
            except Exception as e:
                logger.error(f"Error receiving from client: {e}")
                break

    async def run_agent(self) -> None:
        """Run the agent with input queue."""
        try:
            # Send setup complete
            await self.websocket.send_json({"setupComplete": {}})

            # Wait for first request with user_id
            first_request = await self.input_queue.get()
            self.user_id = first_request.get("user_id")
            if not self.user_id:
                raise ValueError("The first request must have a user_id.")

            first_live_request = first_request.get("live_request")

            # Use project_id as session_id if available
            if self.project_id:
                self.session_id = self.project_id
                logger.info(f"📌 Using project_id as session_id: {self.session_id}")
            else:
                self.session_id = first_request.get("session_id")
                logger.info(f"📌 No project_id, using provided session_id: {self.session_id}")

            # Create session if needed
            if not self.session_id:
                session = await session_service.create_session(
                    app_name=adk_app.name,
                    user_id=self.user_id,
                )
                self.session_id = session.id
            else:
                session = await session_service.get_session(
                    app_name=adk_app.name,
                    user_id=self.user_id,
                    session_id=self.session_id
                )
                if not session:
                    session = await session_service.create_session(
                        app_name=adk_app.name,
                        user_id=self.user_id,
                        session_id=self.session_id
                    )

            self.session = session
            # Register connection with manager so tools can find it
            await connection_manager.connect(self.session_id, self.websocket)
            
            await self.websocket.send_json({"session_id": self.session_id})

            # Create LiveRequestQueue
            live_request_queue = LiveRequestQueue()

            # Add first request if present
            if first_live_request and isinstance(first_live_request, dict):
                live_request_queue.send(LiveRequest.model_validate(first_live_request))

            # Forward requests from input_queue to live_request_queue (like Triage backend)
            async def _forward_requests() -> None:
                while True:
                    request = await self.input_queue.get()
                    live_request = LiveRequest.model_validate(request)
                    live_request_queue.send(live_request)


            async def _forward_events() -> None:
                
                events_async = runner.run_live(
                    user_id=self.user_id,
                    session_id=self.session_id,
                    live_request_queue=live_request_queue,
                )


                async for event in events_async:
                    # Send event to client
                    try:
                        event_dict = _utils.dump_event_for_json(event)
                        await self.websocket.send_json(event_dict)
                    except Exception as e:
                        logger.error(f"Error sending event: {e}")
                        break

                    # ADK Runner already persists events to session automatically
                    # since it was initialized with session_service in fast_api_app.py.
                    # Manual append_event calls here create timestamp conflicts (stale session error).

            # Run both tasks
            requests_task = asyncio.create_task(_forward_requests())
            try:
                await _forward_events()
            finally:
                requests_task.cancel()
                try:
                    await requests_task
                except asyncio.CancelledError:
                    pass
                if live_request_queue:
                    live_request_queue.close()
                if self.session_id:
                    connection_manager.disconnect(self.session_id)

        except Exception as e:
            logger.error(f"Error in agent: {e}")
            await self.websocket.send_json({"error": str(e)})


def get_connect_and_run_callable(websocket: WebSocket) -> Callable:
    """Create callable with retry logic."""

    async def on_backoff(details: backoff._typing.Details) -> None:
        await websocket.send_json({"status": f"Retrying in {details['wait']}s..."})

    @backoff.on_exception(backoff.expo, ConnectionClosedError, max_tries=10, on_backoff=on_backoff)
    async def connect_and_run() -> None:
        session = AgentSession(websocket)
        await asyncio.gather(
            session.receive_from_client(),
            session.run_agent(),
        )

    return connect_and_run


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint."""
    await websocket.accept()
    connect_and_run = get_connect_and_run_callable(websocket)
    await connect_and_run()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "NxtGig AI Accelerator",
        "version": "2.0.0",
        "endpoints": {"health": "/health", "websocket": "/ws"}
    }


@app.get("/health")
async def health_check():
    """Health check."""
    return {
        "status": "healthy",
        "service": "nxtgig-ai-accelerator",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting on {host}:{port}")
    uvicorn.run(app, host=host, port=port)

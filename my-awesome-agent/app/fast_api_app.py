"""FastAPI application with ADK Bidi-streaming."""

import asyncio
import json
import logging
import os
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import socket
from collections import defaultdict, deque

import backoff
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from google.adk.agents.live_request_queue import LiveRequest, LiveRequestQueue
from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService, InMemorySessionService
from google.adk.events.event import Event, EventActions
from google.adk.agents.invocation_context import new_invocation_context_id
from google.cloud import logging as google_cloud_logging
from pydantic import BaseModel
from vertexai.agent_engines import _utils
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.genai import Client, types
from google.genai.types import (
    ContextWindowCompressionConfig, SlidingWindow, SpeechConfig, VoiceConfig,
    PrebuiltVoiceConfig, RealtimeInputConfig, AutomaticActivityDetection,
    ActivityHandling, TurnCoverage, StartSensitivity, EndSensitivity,
)
from websockets.exceptions import ConnectionClosedError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import aiomysql

# Load environment variables
env_path = Path(__file__).parent / ".env"
if not env_path.exists():
    env_path = Path.cwd() / ".env"
load_dotenv(env_path)

from .agent import app as adk_app
from .connection_manager import manager as connection_manager

# Logging setup
if os.environ.get("K_SERVICE"):
    # Use ADC in Cloud Run - explicitly pass project to avoid service account file lookup
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    logging_client = google_cloud_logging.Client(project=project_id) if project_id else google_cloud_logging.Client()
    logging_client.setup_logging()
else:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

# GenAI client (Vertex AI)
USE_VERTEX_AI = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"
GENAI_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GENAI_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("GOOGLE_CLOUD_REGION")
genai_client: Client | None = None

if USE_VERTEX_AI:
    genai_client = Client(
        vertexai=True,
        project=GENAI_PROJECT,
        location=GENAI_LOCATION,
    )
    logger.info("GenAI client initialized for Vertex AI.")

# FastAPI app
app = FastAPI(title="NxtGig AI Accelerator", version="2.0.0")

# Rate Limiter Setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:9002,https://nxtgig.tech")
cors_origins = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()]

# Log origins for debugging
logger.info(f"Configuring CORS with origins: {cors_origins}")

# Workaround for wildcard with credentials
if "*" in cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,  # Wildcard cannot use credentials
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASS") or os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
USE_DB = (
    os.getenv("USE_DB", "").lower() == "true"
    or os.getenv("USE_LOCAL_DB", "").lower() == "true"
    or os.getenv("USE_CLOUD_SQL", "").lower() == "true"
)

# These will be initialized in startup_event
session_service = None
runner = None
artifact_service = None
memory_service = None

logger.info(f"App initialized: {adk_app.name}, Agent: {adk_app.root_agent.name}")

# Language code mapping for Indic languages (only supported languages)
LANGUAGE_CODE_MAP = {
    "hindi": "hi-IN",
    "telugu": "te-IN",
    "tamil": "ta-IN",
    "marathi": "mr-IN",
    "english": "en-US",
}

# Language-specific voice configuration for better UX (Gemini-supported voices only)
VOICE_CONFIG_MAP = {
    "hi-IN": "Zephyr",      # Hindi voice
    "te-IN": "Puck",        # Telugu voice
    "ta-IN": "Charon",      # Tamil voice
    "mr-IN": "Kore",        # Marathi voice
    "en-US": "Aoede",       # English voice (default)
}

def get_language_code(user_language: str | None) -> str:
    """Map user language preference to BCP-47 language code."""
    if not user_language:
        return "en-US"
    lang_lower = user_language.lower().strip()
    return LANGUAGE_CODE_MAP.get(lang_lower, "en-US")

def get_voice_name(language_code: str) -> str:
    """Map language code to appropriate voice name with fallback."""
    return VOICE_CONFIG_MAP.get(language_code, "Aoede")  # Fallback to English voice


class AgentSession:
    """Manages bidirectional communication between client and agent."""

    def __init__(self, websocket: WebSocket, session_service: any, runner: any, artifact_service: any) -> None:
        self.websocket = websocket
        self.session_service = session_service
        self.runner = runner
        self.artifact_service = artifact_service
        self.input_queue: asyncio.Queue[dict] = asyncio.Queue()
        self.setup_ready = asyncio.Event()
        self.user_id_ready = asyncio.Event()
        self.user_id: str | None = None
        self.project_id: str | None = None
        self.session_id: str | None = None
        self.session = None
        self.setup_payload: dict | None = None
        self.user_name: str | None = None
        self.user_language: str | None = None
        self.message_count: int = 0  # Track message count for session resume recovery
        self.has_cleared_resuming: bool = False  # Track if we've cleared is_resuming flag

    def _validate_setup_payload(self) -> tuple[bool, str]:
        """Validate setup payload before starting session processing."""
        if not isinstance(self.setup_payload, dict):
            return False, "Missing setup payload."

        setup = self.setup_payload.get("setup")
        if not isinstance(setup, dict):
            return False, "Invalid setup payload format."

        user_id = self.setup_payload.get("user_id") or setup.get("user_id")
        session_id = (
            self.setup_payload.get("session_id")
            or self.setup_payload.get("project_id")
            or setup.get("session_id")
            or setup.get("project_id")
        )

        if not isinstance(user_id, str) or not user_id.strip():
            return False, "Invalid user_id in setup payload."

        if not isinstance(session_id, str) or not session_id.strip():
            return False, "Invalid session_id in setup payload."

        return True, ""

    def _update_identifiers(self, payload: dict) -> None:
        setup_payload = payload.get("setup") if isinstance(payload.get("setup"), dict) else {}

        user_id = payload.get("user_id") or setup_payload.get("user_id")
        session_id = payload.get("session_id") or setup_payload.get("session_id")
        project_id = payload.get("project_id") or setup_payload.get("project_id")
        
        # New: Capture name and language
        user_name = payload.get("user_name") or setup_payload.get("user_name")
        user_language = payload.get("user_language") or setup_payload.get("user_language")

        if user_name:
            self.user_name = user_name
        if user_language:
            self.user_language = user_language

        if not session_id and project_id:
            session_id = project_id

        if user_id:
            if self.user_id and self.user_id != user_id:
                logger.warning(
                    "Ignoring conflicting user_id '%s' (already '%s').",
                    user_id,
                    self.user_id,
                )
            else:
                self.user_id = user_id

        if session_id:
            if self.session_id and self.session_id != session_id:
                logger.warning(
                    "Ignoring conflicting session_id '%s' (already '%s').",
                    session_id,
                    self.session_id,
                )
            else:
                self.session_id = session_id

        if project_id:
            if self.project_id and self.project_id != project_id:
                logger.warning(
                    "Ignoring conflicting project_id '%s' (already '%s').",
                    project_id,
                    self.project_id,
                )
            else:
                self.project_id = project_id

        if self.user_id:
            self.user_id_ready.set()

    async def receive_from_client(self) -> None:
        """Listen for messages from client and queue them."""
        while True:
            try:
                message = await self.websocket.receive()

                if "text" in message:
                    data = json.loads(message["text"])
                    if isinstance(data, dict):
                        # Handle setup messages to initialize IDs for session/runner
                        if "setup" in data:
                            self.setup_payload = data
                            self._update_identifiers(data)
                            logger.info(
                                "Setup received for user_id=%s session_id=%s",
                                self.user_id,
                                self.session_id,
                            )
                            self.setup_ready.set()
                            continue
                        # Fallback: capture identifiers from non-setup messages if present
                        self._update_identifiers(data)
                        
                        # Session Resume Recovery: Clear resuming flag after first user message
                        self.message_count += 1
                        if not self.has_cleared_resuming and self.session and self.message_count >= 1:
                            session_state = getattr(self.session, 'state', {})
                            if session_state.get("is_resuming"):
                                logger.info("🔄 Clearing is_resuming flag after first user message")
                                try:
                                    event = Event(
                                        invocation_id=new_invocation_context_id(),
                                        author="system",
                                        actions=EventActions(state_delta={"is_resuming": False})
                                    )
                                    await self.runner.session_service.append_event(session=self.session, event=event)
                                    self.has_cleared_resuming = True
                                except Exception as e:
                                    logger.error(f"Failed to clear is_resuming flag: {e}")
                        
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
            # Require explicit setup handshake before running the session.
            try:
                await asyncio.wait_for(self.setup_ready.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                await self.websocket.send_json(
                    {
                        "type": "session_error",
                        "code": "setup_timeout",
                        "message": "Session setup timed out. Please reconnect.",
                    }
                )
                await self.websocket.close(code=1008, reason="Session setup timeout")
                return

            is_valid_setup, setup_error = self._validate_setup_payload()
            if not is_valid_setup:
                await self.websocket.send_json(
                    {
                        "type": "session_error",
                        "code": "invalid_setup",
                        "message": setup_error,
                    }
                )
                await self.websocket.close(code=1008, reason="Invalid setup payload")
                return

            if not self.user_id:
                raise ValueError("Setup must include a user_id.")

            session_init_started = time.monotonic()
            logger.info(
                "Initializing session for user_id=%s requested_session_id=%s",
                self.user_id,
                self.session_id,
            )

            # Create session if needed
            if not self.session_id:
                session = await self.session_service.create_session(
                    app_name=adk_app.name,
                    user_id=self.user_id,
                )
                self.session_id = session.id
            else:
                session = await self.session_service.get_session(
                    app_name=adk_app.name,
                    user_id=self.user_id,
                    session_id=self.session_id
                )
                if not session:
                    session = await self.session_service.create_session(
                        app_name=adk_app.name,
                        user_id=self.user_id,
                        session_id=self.session_id
                    )

            self.session = session
            logger.info(
                "Session ready user_id=%s session_id=%s (latency_ms=%.1f)",
                self.user_id,
                self.session_id,
                (time.monotonic() - session_init_started) * 1000,
            )
            # Register connection with manager so tools can find it
            await connection_manager.connect(self.session_id, self.websocket)

            # Ensure context variables required by agent instructions always exist.
            if not self.user_name:
                self.user_name = "User"
            if not self.user_language:
                self.user_language = "english"

            # Handshake confirmation: session is validated and accepted.
            await self.websocket.send_json(
                {
                    "type": "session_confirmed",
                    "session_id": self.session_id,
                    "user_id": self.user_id,
                }
            )

            # Store user context in session state.
            if self.session_id:
                state_delta = {
                    "user_name": self.user_name,
                    "user_language": self.user_language,
                    # Initialize current_stage_index for Hard State Guard.
                    "current_stage_index": 0,
                }

                # Make state update non-fatal.
                try:
                    event = Event(
                        invocation_id=new_invocation_context_id(),
                        author="system",
                        actions=EventActions(state_delta=state_delta)
                    )
                    await self.runner.session_service.append_event(session=self.session, event=event)
                except Exception as e:
                    logger.error(f"Failed to update session state with user info: {e}")
                    # Continue execution even if state update fails

            # Send setup complete after session/runner are ready
            await self.websocket.send_json({"setupComplete": {}})
            
            await self.websocket.send_json({"session_id": self.session_id})

            # Create LiveRequestQueue
            live_request_queue = LiveRequestQueue()

            # Forward requests from input_queue to live_request_queue (like Triage backend)
            async def _forward_requests() -> None:
                while True:
                    request = await self.input_queue.get()
                    if isinstance(request, dict) and isinstance(request.get("live_request"), dict):
                        request = request["live_request"]
                    live_request = LiveRequest.model_validate(request)
                    live_request_queue.send(live_request)


            async def _forward_events() -> None:
                def _env_int(name: str, default: int) -> int:
                    raw = os.getenv(name)
                    if raw is None:
                        return default
                    try:
                        return int(raw)
                    except ValueError:
                        logger.warning(f"Invalid integer for {name}={raw!r}, using default {default}")
                        return default

                def _is_audio_part(part: object) -> bool:
                    if not isinstance(part, dict):
                        return False
                    inline_data = part.get("inline_data") or part.get("inlineData")
                    if not isinstance(inline_data, dict):
                        return False
                    mime_type = inline_data.get("mime_type") or inline_data.get("mimeType") or ""
                    return isinstance(mime_type, str) and mime_type.startswith("audio/")

                def _strip_audio_parts(payload: dict) -> bool:
                    """Remove audio parts from known content containers. Returns True if any were removed."""
                    removed = False

                    def _strip_parts(container: dict, key: str) -> None:
                        nonlocal removed
                        parts = container.get(key)
                        if not isinstance(parts, list):
                            return
                        filtered_parts = [part for part in parts if not _is_audio_part(part)]
                        if len(filtered_parts) != len(parts):
                            container[key] = filtered_parts
                            removed = True

                    content = payload.get("content")
                    if isinstance(content, dict):
                        _strip_parts(content, "parts")

                    for server_key in ("serverContent", "server_content"):
                        server_content = payload.get(server_key)
                        if not isinstance(server_content, dict):
                            continue
                        for model_key in ("modelTurn", "model_turn"):
                            model_turn = server_content.get(model_key)
                            if isinstance(model_turn, dict):
                                _strip_parts(model_turn, "parts")

                    return removed

                def _event_has_audio(payload: dict) -> bool:
                    content = payload.get("content")
                    if isinstance(content, dict):
                        parts = content.get("parts")
                        if isinstance(parts, list) and any(_is_audio_part(part) for part in parts):
                            return True

                    for server_key in ("serverContent", "server_content"):
                        server_content = payload.get(server_key)
                        if not isinstance(server_content, dict):
                            continue
                        for model_key in ("modelTurn", "model_turn"):
                            model_turn = server_content.get(model_key)
                            if not isinstance(model_turn, dict):
                                continue
                            parts = model_turn.get("parts")
                            if isinstance(parts, list) and any(_is_audio_part(part) for part in parts):
                                return True

                    return False

                def _has_relayable_payload(payload: dict) -> bool:
                    """True if payload still has non-audio data worth forwarding to the client."""
                    if payload.get("input_transcription") or payload.get("output_transcription"):
                        return True
                    if payload.get("interrupted") or payload.get("turn_complete"):
                        return True
                    if payload.get("actions") or payload.get("tool_call") or payload.get("toolCall"):
                        return True

                    content = payload.get("content")
                    if isinstance(content, dict):
                        parts = content.get("parts")
                        if isinstance(parts, list) and len(parts) > 0:
                            return True

                    for server_key in ("serverContent", "server_content"):
                        server_content = payload.get(server_key)
                        if not isinstance(server_content, dict):
                            continue
                        if server_content.get("interrupted") or server_content.get("turnComplete") or server_content.get("turn_complete"):
                            return True
                        for model_key in ("modelTurn", "model_turn"):
                            model_turn = server_content.get(model_key)
                            if not isinstance(model_turn, dict):
                                continue
                            parts = model_turn.get("parts")
                            if isinstance(parts, list) and len(parts) > 0:
                                return True

                    return False

                # Get language code for speech output
                language_code = get_language_code(self.user_language)
                voice_name = get_voice_name(language_code)
                logger.info(f"Using language: {language_code}, voice: {voice_name} for user: {self.user_language}")

                # Lower endpointing latency so agent replies faster after user stops speaking.
                prefix_padding_ms = _env_int("VAD_PREFIX_PADDING_MS", 250)
                silence_duration_ms = _env_int("VAD_SILENCE_DURATION_MS", 650)
                # Keep barge-in gate active only briefly to avoid stuck muted output.
                barge_in_gate_hold_ms = _env_int("BARGE_IN_GATE_HOLD_MS", 350)

                # Configure speech output with language-specific voices and VAD
                run_config = RunConfig(
                    streaming_mode=StreamingMode.BIDI,
                    speech_config=SpeechConfig(
                        voice_config=VoiceConfig(
                            prebuilt_voice_config=PrebuiltVoiceConfig(
                                voice_name=voice_name
                            )
                        ),
                        language_code=language_code,
                    ),
                    response_modalities=["AUDIO"],
                    input_audio_transcription={},
                    output_audio_transcription={},
                    realtime_input_config=RealtimeInputConfig(
                        automatic_activity_detection=AutomaticActivityDetection(
                            # Reduce false positives from background noise
                            start_of_speech_sensitivity=StartSensitivity.START_SENSITIVITY_LOW,
                            # Allow longer pauses without cutting off user mid-thought
                            end_of_speech_sensitivity=EndSensitivity.END_SENSITIVITY_LOW,
                            # Require real speech before committing start-of-speech
                            prefix_padding_ms=prefix_padding_ms,
                            # End user turn after configured silence duration
                            silence_duration_ms=silence_duration_ms,
                        ),
                        # User speech interrupts agent output (barge-in)
                        activity_handling=ActivityHandling.START_OF_ACTIVITY_INTERRUPTS,
                        # Only count actual speech as user turn, not ambient noise
                        turn_coverage=TurnCoverage.TURN_INCLUDES_ONLY_ACTIVITY,
                    ),
                )

                events_async = self.runner.run_live(
                    user_id=self.user_id,
                    session_id=self.session_id,
                    live_request_queue=live_request_queue,
                    run_config=run_config,
                )

                # Barge-in gate: suppress outgoing audio when user speech is active.
                user_speaking = False
                last_user_speech_at = 0.0

                async for event in events_async:
                    try:
                        now = time.monotonic()

                        # Detect user speech and activate gate.
                        if hasattr(event, "input_transcription") and event.input_transcription:
                            user_speaking = True
                            last_user_speech_at = now

                        # Auto-release gate if no new user speech signal arrives.
                        if (
                            user_speaking
                            and last_user_speech_at > 0
                            and (now - last_user_speech_at) * 1000 >= barge_in_gate_hold_ms
                        ):
                            user_speaking = False

                        # Interrupted or turn_complete always resets gate.
                        if getattr(event, "interrupted", False) or getattr(event, "turn_complete", False):
                            user_speaking = False

                        event_dict = _utils.dump_event_for_json(event)

                        # If model output is already available, release gate immediately.
                        if user_speaking:
                            has_output_transcription = bool(
                                event_dict.get("output_transcription")
                                or event_dict.get("outputTranscription")
                                or getattr(event, "output_transcription", None)
                            )
                            if has_output_transcription or _event_has_audio(event_dict):
                                user_speaking = False

                        # While user is speaking, strip audio but keep non-audio signals.
                        if user_speaking:
                            removed_audio = _strip_audio_parts(event_dict)
                            if removed_audio and not _has_relayable_payload(event_dict):
                                continue

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
                    connection_manager.disconnect(self.session_id, self.websocket)

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error in agent: {e}\n{error_details}")
            await self.websocket.send_json({"error": str(e), "details": error_details if os.getenv("DEBUG") == "true" else None})
        finally:
            # Save conversation transcript on session end
            if self.session:
                await self._save_conversation_transcript()
    
    async def _save_conversation_transcript(self) -> None:
        """Save conversation transcript for debugging and compliance."""
        try:
            # Re-fetch the latest session to include all events appended during runner.run_live
            current_session = await self.session_service.get_session(
                app_name=adk_app.name,
                user_id=self.user_id,
                session_id=self.session_id
            )
            
            if not current_session or not hasattr(current_session, 'events') or not current_session.events:
                logger.info("No events to save for transcript")
                return
            
            transcripts = []
            transcripts.append(f"Session ID: {self.session_id}")
            transcripts.append(f"Language: {self.user_language or 'N/A'}")
            transcripts.append(f"Session Started: {getattr(current_session, 'created_at', 'N/A')}")
            transcripts.append(f"\n{'='*80}\n")
            
            for event in current_session.events:
                # Extract user input transcription
                if hasattr(event, 'input_transcription') and event.input_transcription and event.input_transcription.text:
                    transcripts.append(f"\n[USER]: {event.input_transcription.text}\n")
                
                # Extract agent output transcription
                if hasattr(event, 'output_transcription') and event.output_transcription and event.output_transcription.text:
                    transcripts.append(f"[AGENT]: {event.output_transcription.text}\n")
            
            transcript_content = "\n".join(transcripts)
            
            # Create types.Part for artifact service
            artifact_part = types.Part.from_bytes(
                data=transcript_content.encode('utf-8'),
                mime_type='text/plain'
            )
            
            # Save to artifact service with correct signature
            await self.artifact_service.save_artifact(
                app_name=adk_app.name,
                user_id=self.user_id,
                filename=f"transcript_{self.session_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.txt",
                artifact=artifact_part,
                session_id=self.session_id,
            )
            
            logger.info(f"💾 Conversation transcript saved for session {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to save conversation transcript: {e}")


def get_connect_and_run_callable(websocket: WebSocket, session_service: any, runner: any, artifact_service: any) -> Callable:
    """Create callable with retry logic."""

    async def on_backoff(details: backoff._typing.Details) -> None:
        await websocket.send_json({"status": f"Retrying in {details['wait']}s..."})

    @backoff.on_exception(backoff.expo, ConnectionClosedError, max_tries=10, on_backoff=on_backoff)
    async def connect_and_run() -> None:
        session = AgentSession(websocket, session_service, runner, artifact_service)
        await asyncio.gather(
            session.receive_from_client(),
            session.run_agent(),
        )

    return connect_and_run


# In-memory rate limiting for WebSocket connections
rate_limit_store: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10))
RATE_LIMIT_WINDOW = 60  # 60 seconds
RATE_LIMIT_MAX = 10  # 10 connections per window


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint with manual rate limiting."""
    client_ip = websocket.client.host if websocket.client else "unknown"
    
    # Check rate limit before accepting connection
    current_time = datetime.now(timezone.utc).timestamp()
    timestamps = rate_limit_store[client_ip]
    
    # Remove timestamps outside the window
    while timestamps and current_time - timestamps[0] > RATE_LIMIT_WINDOW:
        timestamps.popleft()
    
    # Check if limit exceeded
    if len(timestamps) >= RATE_LIMIT_MAX:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        await websocket.close(code=1008, reason="Rate limit exceeded")
        return
    
    # Record this connection attempt
    timestamps.append(current_time)
    
    await websocket.accept()
    connect_and_run = get_connect_and_run_callable(
        websocket, 
        websocket.app.state.session_service, 
        websocket.app.state.runner,
        websocket.app.state.artifact_service
    )
    await connect_and_run()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "NxtGig AI Accelerator",
        "version": "2.0.0",
        "endpoints": {"health": "/health", "websocket": "/ws"}
    }


@app.get("/config/stages")
async def get_stages_config():
    """Get stages configuration."""
    config_path = Path(__file__).parent / "config" / "stages_config.json"
    if not config_path.exists():
        return JSONResponse(status_code=404, content={"error": "Config file not found"})
    
    with open(config_path, "r") as f:
        return json.load(f)


@app.on_event("startup")
async def startup_event():
    """Initialize everything on the running event loop."""
    global session_service, runner, artifact_service, memory_service
    
    # 1. Database Session Service
    try:
        if USE_DB:
            if not DB_USER or not DB_PASSWORD or not DB_NAME:
                raise ValueError("DB_USER, DB_PASS/DB_PASSWORD, and DB_NAME must be set when USE_DB is true.")

            db_port_int = int(DB_PORT)

            if DB_HOST.startswith("/cloudsql") or os.getenv("USE_CLOUD_SQL", "").lower() == "true":
                instance_connection_name = DB_HOST.split("/cloudsql/")[-1] if "/cloudsql/" in DB_HOST else os.getenv("CLOUD_SQL_CONNECTION_NAME")

                if instance_connection_name:
                    unix_socket_path = f"/cloudsql/{instance_connection_name}"
                    logger.info(f"💾 Using Cloud SQL via Unix socket: {unix_socket_path}")

                    async def get_cloud_sql_conn():
                        conn = await aiomysql.connect(
                            unix_socket=unix_socket_path,
                            user=DB_USER,
                            password=DB_PASSWORD,
                            db=DB_NAME,
                        )
                        return conn

                    session_service = DatabaseSessionService(
                        db_url="mysql+aiomysql://",
                        async_creator=get_cloud_sql_conn
                    )
                else:
                    logger.info(f"💾 USE_CLOUD_SQL is true, using standard TCP to {DB_HOST}")
                    DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{db_port_int}/{DB_NAME}"
                    session_service = DatabaseSessionService(db_url=DATABASE_URL)
            else:
                DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{db_port_int}/{DB_NAME}"
                session_service = DatabaseSessionService(db_url=DATABASE_URL)

            logger.info(f"✅ DatabaseSessionService initialized successfully for {DB_HOST}")
        else:
            raise Exception("Database disabled")
    except Exception as e:
        logger.error(f"❌ DatabaseSessionService initialization failed: {e}")
        logger.warning("⚠️ Falling back to InMemorySessionService")
        session_service = InMemorySessionService()

    # 2. Artifact Service
    logs_bucket_name = os.getenv("LOGS_BUCKET_NAME")
    artifact_service = GcsArtifactService(bucket_name=logs_bucket_name) if logs_bucket_name else InMemoryArtifactService()

    # 3. Memory Service
    memory_service = InMemoryMemoryService()

    # 4. Runner
    runner = Runner(
        app=adk_app,
        session_service=session_service,
        artifact_service=artifact_service,
        memory_service=memory_service,
    )

    # Store in app state for access in endpoints
    app.state.session_service = session_service
    app.state.runner = runner
    app.state.artifact_service = artifact_service
    
    logger.info("Startup complete: Services initialized on running event loop.")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down services.")


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

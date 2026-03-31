"""Compatibility patch for routing live audio through the GenAI audio channel."""

from __future__ import annotations

import logging

from google.genai import types

logger = logging.getLogger(__name__)

_PATCH_ATTR = "_voice_agent_live_audio_routing_patched"


async def _patched_send_realtime(self, input):
    """Route audio blobs via `audio=` and other blobs via `media=`."""
    if isinstance(input, types.Blob):
        mime_type = (input.mime_type or "").lower()
        if mime_type.startswith("audio/"):
            logger.debug("Sending LLM audio blob via dedicated audio channel.")
            await self._gemini_session.send_realtime_input(audio=input)
            return

        logger.debug("Sending LLM Blob.")
        await self._gemini_session.send_realtime_input(media=input)
        return

    if isinstance(input, types.ActivityStart):
        logger.debug("Sending LLM activity start signal.")
        await self._gemini_session.send_realtime_input(activity_start=input)
        return

    if isinstance(input, types.ActivityEnd):
        logger.debug("Sending LLM activity end signal.")
        await self._gemini_session.send_realtime_input(activity_end=input)
        return

    raise ValueError("Unsupported input type: %s" % type(input))


def patch_adk_live_audio_routing() -> bool:
    """Patch ADK's Gemini live connection once for safer audio transport."""
    from google.adk.models.gemini_llm_connection import GeminiLlmConnection

    current = GeminiLlmConnection.send_realtime
    if getattr(current, _PATCH_ATTR, False):
        return False

    setattr(_patched_send_realtime, _PATCH_ATTR, True)
    GeminiLlmConnection.send_realtime = _patched_send_realtime
    logger.info(
        "Patched ADK live audio routing to use the dedicated audio channel."
    )
    return True

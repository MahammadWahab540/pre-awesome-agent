from __future__ import annotations

import pytest
from google.genai import types

from app.utils.live_audio_patch import patch_adk_live_audio_routing


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def send_realtime_input(self, **kwargs) -> None:
        self.calls.append(kwargs)


@pytest.mark.asyncio
async def test_audio_blob_routes_to_audio_channel() -> None:
    patch_adk_live_audio_routing()

    from google.adk.models.gemini_llm_connection import GeminiLlmConnection

    session = _FakeSession()
    connection = GeminiLlmConnection(session)

    await connection.send_realtime(
        types.Blob(data=b"\x00\x00", mime_type="audio/pcm;rate=16000")
    )

    assert session.calls == [
        {"audio": types.Blob(data=b"\x00\x00", mime_type="audio/pcm;rate=16000")}
    ]


@pytest.mark.asyncio
async def test_non_audio_blob_still_routes_to_media_channel() -> None:
    patch_adk_live_audio_routing()

    from google.adk.models.gemini_llm_connection import GeminiLlmConnection

    session = _FakeSession()
    connection = GeminiLlmConnection(session)

    await connection.send_realtime(
        types.Blob(data=b"jpeg", mime_type="image/jpeg")
    )

    assert session.calls == [
        {"media": types.Blob(data=b"jpeg", mime_type="image/jpeg")}
    ]

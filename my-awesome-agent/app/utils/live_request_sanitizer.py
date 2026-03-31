"""Helpers for validating live requests before they reach Gemini Live."""

from __future__ import annotations

import base64
import binascii
import logging
from typing import Any

logger = logging.getLogger(__name__)

PCM_16KHZ_MIME_TYPE = "audio/pcm;rate=16000"


def sanitize_live_request_payload(request: Any) -> Any | None:
    """Return a normalized live request or ``None`` when it should be dropped.

    Gemini Live will terminate the session if it receives a malformed audio
    frame. We defensively validate browser audio chunks here so a single bad
    chunk is dropped instead of crashing the whole call.
    """
    if not isinstance(request, dict):
        return request

    blob = request.get("blob")
    if not isinstance(blob, dict):
        return request

    mime_type = blob.get("mimeType") or blob.get("mime_type")
    if not isinstance(mime_type, str):
        return request

    normalized_mime_type = mime_type.lower().strip()
    if not normalized_mime_type.startswith("audio/"):
        return request

    if not normalized_mime_type.startswith("audio/pcm"):
        logger.warning("Dropping live audio chunk with unsupported mime type: %s", mime_type)
        return None

    data = blob.get("data")
    if not isinstance(data, str) or not data.strip():
        logger.warning("Dropping live audio chunk with missing base64 payload.")
        return None

    compact_data = "".join(data.split())
    try:
        decoded = base64.b64decode(compact_data, validate=True)
    except binascii.Error:
        padding = "=" * ((4 - len(compact_data) % 4) % 4)
        try:
            decoded = base64.b64decode(f"{compact_data}{padding}", validate=False)
        except binascii.Error:
            logger.warning("Dropping live audio chunk with invalid base64 payload.")
            return None

    if not decoded:
        logger.warning("Dropping empty live audio chunk.")
        return None

    if len(decoded) % 2 != 0:
        logger.warning(
            "Dropping live audio chunk with odd PCM byte length: %s",
            len(decoded),
        )
        return None

    sanitized_blob = dict(blob)
    sanitized_blob["data"] = base64.b64encode(decoded).decode("ascii")
    sanitized_blob["mimeType"] = PCM_16KHZ_MIME_TYPE
    sanitized_blob.pop("mime_type", None)

    sanitized_request = dict(request)
    sanitized_request["blob"] = sanitized_blob
    return sanitized_request

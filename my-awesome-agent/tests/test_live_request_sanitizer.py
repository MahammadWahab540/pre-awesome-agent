import base64

from app.utils.live_request_sanitizer import (
    PCM_16KHZ_MIME_TYPE,
    sanitize_live_request_payload,
)


def test_passthrough_for_non_blob_requests():
    request = {"content": {"parts": [{"text": "hello"}]}}

    assert sanitize_live_request_payload(request) == request


def test_drops_audio_with_invalid_base64():
    request = {
        "blob": {
            "mimeType": "audio/pcm;rate=16000",
            "data": "%%%not-base64%%%",
        }
    }

    assert sanitize_live_request_payload(request) is None


def test_drops_audio_with_odd_pcm_byte_length():
    request = {
        "blob": {
            "mimeType": "audio/pcm;rate=16000",
            "data": base64.b64encode(b"\x01").decode("ascii"),
        }
    }

    assert sanitize_live_request_payload(request) is None


def test_normalizes_valid_pcm_audio():
    payload = b"\x00\x00\x01\x00"
    request = {
        "blob": {
            "mimeType": "audio/pcm",
            "mime_type": "audio/pcm",
            "data": base64.b64encode(payload).decode("ascii"),
        }
    }

    sanitized = sanitize_live_request_payload(request)

    assert sanitized is not None
    assert sanitized["blob"]["mimeType"] == PCM_16KHZ_MIME_TYPE
    assert "mime_type" not in sanitized["blob"]
    assert base64.b64decode(sanitized["blob"]["data"]) == payload

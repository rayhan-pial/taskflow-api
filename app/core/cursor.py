import base64
import json

from app.core.exceptions import api_error


def encode_cursor(data: dict) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(token: str) -> dict:
    try:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(padded.encode())
        data = json.loads(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        raise api_error(
            status_code=400,
            code="invalid_cursor",
            message="Cursor is malformed.",
        ) from exc
    if not isinstance(data, dict):
        raise api_error(
            status_code=400,
            code="invalid_cursor",
            message="Cursor is malformed.",
        )
    return data

"""Small HTTP helpers for OpenAI-compatible servers (stdlib only)."""

from __future__ import annotations

import io
import json
import os
import socket
import urllib.error
import urllib.request
import uuid
import wave
from collections.abc import Iterator

from .config import Backend
from .errors import BackendError


def api_key(b: Backend, role: str) -> str | None:
    if not b.api_key_env:
        return None
    key = os.environ.get(b.api_key_env, "").strip()
    if not key:
        raise BackendError(f"set the {b.api_key_env} environment variable (needed by {role})")
    return key


def _headers(b: Backend, role: str, kind: str) -> dict[str, str]:
    headers = {"Content-Type": kind}
    key = api_key(b, role)
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def post(b: Backend, role: str, path: str, body: bytes, kind: str, timeout: float = 120.0):
    """POST to {base_url}{path}; returns the open response. Errors name what to fix."""
    if not b.base_url:
        raise BackendError(f"{role}: set {role}.base_url in config.toml")
    url = b.base_url + path
    request = urllib.request.Request(url, data=body, headers=_headers(b, role, kind), method="POST")
    try:
        return urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            hint = f"check the {b.api_key_env} environment variable" if b.api_key_env else "this server wants an API key: set api_key_env"
            raise BackendError(f"{role}: {url} refused the key (HTTP {exc.code}); {hint}") from None
        detail = exc.read()[:200].decode("utf-8", "replace")
        raise BackendError(f"{role}: {url} answered HTTP {exc.code}: {detail}. Check {role}.model and {role}.base_url in config.toml") from None
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise BackendError(f"{role}: cannot reach {url} ({reason}). Is the server running? Check {role}.base_url in config.toml") from None


def post_json(b: Backend, role: str, path: str, payload: dict, timeout: float = 120.0):
    return post(b, role, path, json.dumps(payload).encode(), "application/json", timeout)


def sse_data(response) -> Iterator[dict]:
    """Yield each JSON event of a text/event-stream response until [DONE]."""
    with response:
        for raw in response:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                return
            yield json.loads(data)


def wav_bytes(pcm: bytes, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()


def multipart(fields: dict[str, str], file_field: str, filename: str, data: bytes) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'
                 f"Content-Type: audio/wav\r\n\r\n".encode() + data + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"

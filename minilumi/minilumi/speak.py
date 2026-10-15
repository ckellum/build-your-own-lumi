"""Speak: turn a sentence into audio (mono s16le PCM plus its sample rate)."""

from __future__ import annotations

import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path

import numpy as np

from .config import Backend
from .errors import BackendError
from .http import post_json

Speaker = Callable[[str], tuple[bytes, int]]
KOKORO_FILES = {
    "kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
}
CACHE = Path.home() / ".cache" / "minilumi"


def make_speaker(b: Backend) -> Speaker:
    if b.kind == "openai":
        return _openai(b)
    if b.kind == "kokoro-local":
        return _kokoro_local(b)
    raise BackendError(f"unknown speak.kind {b.kind!r}; use 'openai' or 'kokoro-local'")


def _openai(b: Backend) -> Speaker:
    def speak(text: str) -> tuple[bytes, int]:
        payload = {"model": b.model, "input": text, "voice": b.voice or "alloy", "response_format": "pcm"}
        with post_json(b, "speak", "/audio/speech", payload) as response:
            pcm = response.read()
        return pcm[: len(pcm) // 2 * 2], 24000     # OpenAI-style "pcm" is 24 kHz mono s16le
    return speak


def _download(name: str, url: str) -> Path:
    path = CACHE / name
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        print(f"downloading {name} (one time only)...", file=sys.stderr, flush=True)
        partial = path.with_suffix(".part")
        urllib.request.urlretrieve(url, partial)
        partial.rename(path)
    return path


def _kokoro_local(b: Backend) -> Speaker:
    try:
        from kokoro_onnx import Kokoro
    except ImportError:
        raise BackendError("speak: install local speech first: uv sync --extra local") from None
    try:
        model, voices = (_download(name, url) for name, url in KOKORO_FILES.items())
    except OSError as exc:
        raise BackendError(f"speak: could not download the Kokoro voice model ({exc})") from None
    kokoro = Kokoro(str(model), str(voices))

    def speak(text: str) -> tuple[bytes, int]:
        samples, rate = kokoro.create(text, voice=b.voice or "af_heart", speed=1.0, lang="en-us")
        pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2").tobytes()
        return pcm, int(rate)
    return speak

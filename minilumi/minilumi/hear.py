"""Hear: turn a recorded utterance (16 kHz mono s16le) into text."""

from __future__ import annotations

import json
from collections.abc import Callable

import numpy as np

from .config import Backend
from .errors import BackendError
from .http import multipart, post, wav_bytes
from .listen import SAMPLE_RATE


def make_hearer(b: Backend) -> Callable[[bytes], str]:
    if b.kind == "openai":
        return _openai(b)
    if b.kind == "whisper-local":
        return _whisper_local(b)
    raise BackendError(f"unknown hear.kind {b.kind!r}; use 'openai' or 'whisper-local'")


def _openai(b: Backend) -> Callable[[bytes], str]:
    def hear(pcm: bytes) -> str:
        body, kind = multipart({"model": b.model, "language": "en"}, "file", "speech.wav",
                               wav_bytes(pcm, SAMPLE_RATE))
        with post(b, "hear", "/audio/transcriptions", body, kind) as response:
            return json.loads(response.read()).get("text", "").strip()
    return hear


def _whisper_local(b: Backend) -> Callable[[bytes], str]:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise BackendError("hear: install local speech first: uv sync --extra local") from None
    try:
        # CPU on purpose: "auto" picks an NVIDIA GPU and then fails mid-visit if CUDA libraries are missing.
        model = WhisperModel(b.model, device="cpu", compute_type="int8")   # downloads once, then cached
    except Exception as exc:     # network, disk or model-name problems from the downloader
        raise BackendError(f"hear: could not load the Whisper model {b.model!r} ({exc}). "
                           f"Check your internet connection for the first download, or hear.model in config.toml") from None

    def hear(pcm: bytes) -> str:
        audio = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
        segments, _ = model.transcribe(audio, language="en", beam_size=1, vad_filter=False)
        return " ".join(s.text.strip() for s in segments).strip()
    return hear

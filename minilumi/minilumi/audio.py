"""Microphone in, speaker out, or a WAV file standing in for the microphone."""

from __future__ import annotations

import queue
import time
import wave
from collections.abc import Iterator
from pathlib import Path

import numpy as np

from .listen import FRAME_MS, SAMPLE_RATE

FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000
NO_MIC = "No microphone found (or permission denied). Try: uv run minilumi run --input samples/hello.wav --mute"
NO_PERMISSION = ("The microphone is sending pure silence, which usually means your terminal has no microphone "
                 "permission (macOS: System Settings > Privacy & Security > Microphone). " + NO_MIC.split(". ", 1)[1])


class AudioUnavailable(RuntimeError):
    """No usable microphone or speaker; the message says what to try."""


def _sounddevice():
    try:
        import sounddevice
    except (ImportError, OSError) as exc:      # OSError: the PortAudio library itself is missing
        raise AudioUnavailable(f"audio is unavailable ({exc}). Try --input file.wav and --mute") from None
    return sounddevice


class MicSource:
    """The default microphone, as 20 ms frames of 16 kHz mono s16le."""

    def __init__(self):
        sd = _sounddevice()
        self._queue: queue.Queue[bytes] = queue.Queue()
        try:
            self._stream = sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                                             blocksize=FRAME_SAMPLES,
                                             callback=lambda data, *_: self._queue.put(bytes(data)))
            self._stream.start()
        except Exception:      # PortAudioError and friends: no device, or permission denied
            raise AudioUnavailable(NO_MIC) from None

    def frames(self) -> Iterator[bytes]:
        def raw() -> Iterator[bytes]:
            while True:
                yield self._queue.get()
        return guard_silence(raw())

    def drain(self) -> None:
        """Forget everything heard so far (e.g. Lumi's own voice while she spoke)."""
        while not self._queue.empty():
            self._queue.get_nowait()

    def close(self) -> None:
        self._stream.stop()
        self._stream.close()


def guard_silence(frames: Iterator[bytes], seconds: float = 1.0) -> Iterator[bytes]:
    """A real microphone always hears a little noise. If the first second is exact digital
    silence, the OS is almost certainly blocking the mic (macOS does this without an error)."""
    needed = int(seconds * 1000 / FRAME_MS)
    first: list[bytes] = []
    for frame in frames:
        first.append(frame)
        if len(first) == needed:
            break
    if len(first) == needed and not any(f.strip(b"\0") for f in first):
        raise AudioUnavailable(NO_PERMISSION)
    yield from first
    yield from frames


class WavSource:
    """A WAV file played into minilumi instead of the microphone, followed by 3 s of silence."""

    def __init__(self, path: Path):
        try:
            with wave.open(str(path), "rb") as w:
                channels, width, rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
                raw = w.readframes(w.getnframes())
        except (FileNotFoundError, wave.Error, EOFError) as exc:
            raise AudioUnavailable(f"cannot read {path}: {exc}") from None
        if width != 2:
            raise AudioUnavailable(f"{path} must be 16-bit PCM WAV")
        samples = np.frombuffer(raw, dtype="<i2").reshape(-1, channels).mean(axis=1)
        if rate != SAMPLE_RATE:
            positions = np.arange(0, len(samples), rate / SAMPLE_RATE)
            samples = np.interp(positions, np.arange(len(samples)), samples)
        samples = np.concatenate([samples, np.zeros(SAMPLE_RATE * 3)])
        pcm = samples.clip(-32768, 32767).astype("<i2").tobytes()
        step = FRAME_SAMPLES * 2
        self._frames = [pcm[i:i + step] for i in range(0, len(pcm) - step + 1, step)]

    def frames(self) -> Iterator[bytes]:
        yield from self._frames

    def drain(self) -> None:
        pass

    def close(self) -> None:
        pass


class Player:
    """Plays audio on the default output device and waits until it has finished."""

    def __init__(self):
        self._sd = _sounddevice()

    def play(self, pcm: bytes, sample_rate: int) -> None:
        try:
            self._sd.play(np.frombuffer(pcm, dtype="<i2"), sample_rate)
            self._sd.wait()
        except Exception as exc:
            raise AudioUnavailable(f"cannot play audio ({exc}). Try --mute") from None


class SilentPlayer:
    """--mute: plays nothing but takes as long as the audio would, so the screen stays in step."""

    def play(self, pcm: bytes, sample_rate: int) -> None:
        time.sleep(len(pcm) / 2 / sample_rate)


def envelope(pcm: bytes, sample_rate: int, step_ms: int = 20) -> list[float]:
    """Loudness per step, 0..1, for moving the avatar's mouth in time with the audio."""
    samples = np.frombuffer(pcm, dtype="<i2").astype(np.float64)
    step = max(1, sample_rate * step_ms // 1000)
    count = len(samples) // step
    if count == 0:
        return []
    levels = np.sqrt((samples[: count * step].reshape(count, step) ** 2).mean(axis=1))
    top = levels.max()
    return [round(float(v), 3) for v in (levels / top if top else levels)]

"""Knowing when someone has finished talking.

The room is measured all the time (a low percentile of recent loudness), so a speaker
in a noisy hall must be louder than the hall to start a turn, while a quiet room lets a
soft voice through. A turn ends after a stretch of quiet; coughs and clicks are dropped.
"""

from __future__ import annotations

from collections import deque

import numpy as np

FRAME_MS = 20
SAMPLE_RATE = 16000
FRAME_BYTES = SAMPLE_RATE * FRAME_MS // 1000 * 2
MIN_START_LEVEL = 200.0     # never start on anything quieter than this, however silent the room


def rms(frame: bytes) -> float:
    samples = np.frombuffer(frame, dtype="<i2").astype(np.float64)
    return float(np.sqrt(np.mean(samples * samples))) if samples.size else 0.0


def peak(frame: bytes) -> int:
    samples = np.frombuffer(frame, dtype="<i2").astype(np.int32)
    return int(np.abs(samples).max()) if samples.size else 0


class Endpointer:
    """Feed 20 ms frames of 16 kHz mono s16le audio; get back each finished utterance."""

    def __init__(self, start_ratio: float = 4.0, keep_ratio: float = 2.0, end_silence_ms: int = 700,
                 preroll_ms: int = 300, min_speech_ms: int = 250, min_peak: float = 1500.0,
                 room_window_ms: int = 1500):
        self.start_ratio = start_ratio
        self.keep_ratio = keep_ratio
        self.end_frames = end_silence_ms // FRAME_MS
        self.min_speech_frames = -(-min_speech_ms // FRAME_MS)
        self.min_peak = min_peak
        self._room = deque(maxlen=room_window_ms // FRAME_MS)
        self._preroll = deque(maxlen=preroll_ms // FRAME_MS)
        self._reset()

    def _reset(self) -> None:
        self._speaking = False
        self._frames: list[bytes] = []
        self._voiced = 0
        self._quiet = 0
        self._peak = 0
        self._room_level = 0.0

    @property
    def speaking(self) -> bool:
        """True while an utterance is being collected."""
        return self._speaking

    def room_level(self) -> float:
        return float(np.percentile(self._room, 20)) if self._room else 0.0

    def feed(self, frame: bytes) -> bytes | None:
        level = rms(frame)
        if not self._speaking:
            room = self.room_level() if self._room else level
            if level > max(self.start_ratio * room, MIN_START_LEVEL):
                self._speaking = True
                self._room_level = room
                self._frames = list(self._preroll) + [frame]
                self._voiced, self._peak = 1, peak(frame)
                self._preroll.clear()
                return None
            self._room.append(level)
            self._preroll.append(frame)
            return None

        self._frames.append(frame)
        if level > max(self.keep_ratio * self._room_level, MIN_START_LEVEL / 2):
            self._voiced += 1
            self._quiet = 0
            self._peak = max(self._peak, peak(frame))
            return None
        self._quiet += 1
        if self._quiet < self.end_frames:
            return None
        utterance = b"".join(self._frames)
        keep = self._voiced >= self.min_speech_frames and self._peak >= self.min_peak
        self._reset()
        return utterance if keep else None

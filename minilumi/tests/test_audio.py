import numpy as np
import pytest

from minilumi.audio import AudioUnavailable, guard_silence

ZERO = b"\0\0" * 320


def test_digital_silence_at_start_means_no_mic_permission():
    with pytest.raises(AudioUnavailable, match="permission"):
        list(guard_silence(iter([ZERO] * 60)))


def test_real_room_noise_passes_through():
    noise = (np.random.default_rng(0).normal(0, 30, 320)).astype("<i2").tobytes()
    frames = [ZERO] * 10 + [noise] * 60
    assert len(list(guard_silence(iter(frames)))) == 70


def test_truncated_stereo_wav_still_reads(tmp_path):
    import wave
    from minilumi.audio import WavSource
    p = tmp_path / "s.wav"
    with wave.open(str(p), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b"\x01\x00" * 3201)            # odd number of samples: last frame cut in half
    assert len(list(WavSource(p).frames())) > 0

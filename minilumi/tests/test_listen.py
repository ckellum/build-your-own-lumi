import numpy as np

from minilumi.listen import FRAME_MS, SAMPLE_RATE, Endpointer

N = SAMPLE_RATE * FRAME_MS // 1000


def tone(amp):
    return (np.sin(np.arange(N) / 3) * amp).astype("<i2").tobytes()


def noise(amp, seed=0):
    return np.random.default_rng(seed).normal(0, amp, N).clip(-32768, 32767).astype("<i2").tobytes()


def quiet(count, amp=100, offset=0):
    return [noise(amp, offset + i) for i in range(count)]


def run(ep, frames):
    return [u for u in (ep.feed(f) for f in frames) if u]


def test_speech_after_quiet_room_is_one_utterance():
    got = run(Endpointer(), quiet(50) + [tone(8000)] * 40 + quiet(50, offset=99))
    assert len(got) == 1
    assert len(got[0]) >= 40 * N * 2          # every speech frame kept, plus preroll


def test_short_cough_is_dropped():
    assert run(Endpointer(), quiet(50) + [tone(8000)] * 5 + quiet(50, offset=99)) == []


def test_loud_room_alone_never_triggers():
    assert run(Endpointer(), quiet(200, amp=1200)) == []


def test_quiet_talker_in_quiet_room_is_heard():
    got = run(Endpointer(), quiet(50, amp=60) + [tone(2500)] * 30 + quiet(50, amp=60, offset=99))
    assert len(got) == 1


def test_two_sentences_with_a_short_pause_stay_one_turn():
    frames = quiet(50) + [tone(8000)] * 30 + quiet(15, offset=7) + [tone(8000)] * 30 + quiet(50, offset=99)
    assert len(run(Endpointer(), frames)) == 1


def test_two_turns_separated_by_long_silence_are_two_utterances():
    frames = quiet(50) + [tone(8000)] * 30 + quiet(60, offset=7) + [tone(8000)] * 30 + quiet(50, offset=99)
    assert len(run(Endpointer(), frames)) == 2

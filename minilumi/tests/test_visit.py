import re
from datetime import datetime
from pathlib import Path

import numpy as np
from conftest import FastPlayer, ListScreen, ListSource

from minilumi.event import load_event
from minilumi.listen import FRAME_MS, SAMPLE_RATE
from minilumi.visit import Visit

EV = load_event(Path(__file__).resolve().parents[1] / "example-event")
N = SAMPLE_RATE * FRAME_MS // 1000
PER_SECOND = 1000 // FRAME_MS


def quiet(seconds):
    return [np.zeros(N, dtype="<i2").tobytes()] * int(seconds * PER_SECOND)


def talk(seconds):
    return [(np.sin(np.arange(N) / 3) * 8000).astype("<i2").tobytes()] * int(seconds * PER_SECOND)


def frames_for(*utterances):
    frames = quiet(1)
    for seconds in utterances:
        frames += talk(seconds) + quiet(1.5)
    return frames


def make(heard, reply=("It's in the Maple Room. ", "Enjoy!")):
    said, heard = [], iter(heard)
    thoughts = []

    def think(messages):
        thoughts.append([dict(m) for m in messages])
        return iter(reply)

    visit = Visit(event=EV, hear=lambda pcm: next(heard), think=think,
                  speak=lambda text: (said.append(text) or (b"\0\0" * 240, 24000)),
                  player=FastPlayer(), screen=ListScreen(), now=lambda: datetime(2030, 5, 14, 9, 50))
    return visit, said, thoughts


def test_known_badge_is_greeted_with_their_next_session():
    visit, said, _ = make(["goodbye"])
    visit.run("EX-0001", ListSource(frames_for(1.0)))
    assert said[0].startswith("Hi Ada!")
    assert "Voice Interfaces 101" in said[0] and "10:00 AM" in said[0] and "Maple Room" in said[0]


def test_answer_is_spoken_sentence_by_sentence_then_goodbye_ends_the_visit():
    visit, said, _ = make(["where is my session", "goodbye"])
    convo = visit.run("EX-0001", ListSource(frames_for(1.0, 1.0)))
    assert "It's in the Maple Room." in said and "Enjoy!" in said
    assert re.search(r"\bbye\b", said[-1], re.I)
    assert [m["role"] for m in convo] == ["user", "assistant"]


def test_first_question_carries_who_and_when_but_the_system_prompt_does_not():
    visit, _, thoughts = make(["where is my session", "goodbye"])
    visit.run("EX-0001", ListSource(frames_for(1.0, 1.0)))
    first = thoughts[0][0]["content"]
    assert "Ada Park" in first and "9:50 AM" in first and "where is my session" in first


def test_unknown_badge_still_gets_a_visit():
    visit, said, _ = make(["goodbye"])
    visit.run("NOPE-1", ListSource(frames_for(1.0)))
    assert said[0] == "Hi there! I'm Lumi. Ask me about sessions, rooms, or lunch."


def test_silence_asks_still_there_then_ends():
    visit, said, _ = make([])
    convo = visit.run(None, ListSource(quiet(46)))
    assert "Still there?" in said
    assert convo == []


def test_mic_is_drained_after_lumi_speaks_so_she_does_not_hear_herself():
    visit, _, _ = make(["where is my session", "goodbye"])
    source = ListSource(frames_for(1.0, 1.0))
    visit.run("EX-0001", source)
    assert source.drained >= 2


def test_screen_gets_heard_and_say_messages_with_lip_sync_envelope():
    visit, _, _ = make(["where is my session", "goodbye"])
    visit.run("EX-0001", ListSource(frames_for(1.0, 1.0)))
    kinds = [m["type"] for m in visit.screen.messages]
    assert "heard" in kinds and "say" in kinds and kinds[-1] == "state"
    say = next(m for m in visit.screen.messages if m["type"] == "say")
    assert isinstance(say["envelope"], list) and say["step_ms"] == 20

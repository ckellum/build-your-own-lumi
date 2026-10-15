"""One visit: greet, then listen, think and speak until goodbye or silence."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime

from .audio import envelope
from .event import Event, spoken_time
from .listen import FRAME_MS, Endpointer

GOODBYE = re.compile(r"\b(bye|goodbye|that's all|that is all|see you)\b", re.I)
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
# "Dr." or "a.m." end in a dot but don't end the sentence.
ABBREVIATIONS = re.compile(r"(?:\b(?:Dr|Mr|Mrs|Ms|St|vs|etc|e\.g|i\.e)|\b[ap]\.m)\.$", re.I)
UNKNOWN_GREETING = "Hi there! I'm Lumi. Ask me about sessions, rooms, or lunch."
ASK_AGAIN = "Sorry, could you ask that again?"


def sentences(chunks: Iterator[str]) -> Iterator[str]:
    """Regroup streamed text into whole sentences, so speech can start before the reply is finished."""
    buffer = ""
    for chunk in chunks:
        buffer += chunk
        parts = SENTENCE_END.split(buffer)
        pending = ""
        for done in parts[:-1]:
            pending = f"{pending} {done}".strip() if pending else done.strip()
            if pending and not ABBREVIATIONS.search(pending):
                yield pending
                pending = ""
        buffer = f"{pending} {parts[-1]}" if pending else parts[-1]
    if buffer.strip():
        yield buffer.strip()


@dataclass
class Visit:
    event: Event
    hear: Callable[[bytes], str]
    think: Callable[[list[dict]], Iterator[str]]
    speak: Callable[[str], tuple[bytes, int]]
    player: object
    screen: object
    now: Callable[[], datetime] = datetime.now
    still_there_s: float = 30.0
    give_up_s: float = 15.0

    def _state(self, state: str) -> None:
        self.screen.send({"type": "state", "state": state})

    def _say(self, text: str, source) -> None:
        pcm, rate = self.speak(text)
        self._state("speaking")
        self.screen.send({"type": "say", "text": text, "envelope": envelope(pcm, rate), "step_ms": 20})
        self.player.play(pcm, rate)
        source.drain()                       # don't hear Lumi's own voice as the next question

    def _greeting(self, badge: str | None) -> tuple[str, str | None]:
        person = self.event.attendee(badge) if badge else None
        if person is None:
            return UNKNOWN_GREETING, None
        first = person.name.split()[0]
        upcoming = self.event.next_sessions(self.now(), person.badge, limit=1)
        if not upcoming:
            return f"Hi {first}! Nothing else on your schedule today. What can I help with?", person.name
        s = upcoming[0]
        return (f"Hi {first}! Next up for you: {s.title} at {spoken_time(s.start)}, {s.room}. "
                f"What can I help with?"), person.name

    def _context(self, name: str | None, badge: str | None) -> str:
        upcoming = self.event.next_sessions(self.now(), badge if name else None)
        listed = "; ".join(f"{s.title} at {spoken_time(s.start)} in the {s.room}" for s in upcoming) or "none"
        who = f"Visitor: {name}." if name else "Visitor: not signed in."
        return f"[{who} Now: {spoken_time(self.now())}. Their next sessions: {listed}.]\n"

    def run(self, badge: str | None, source) -> list[dict]:
        conversation: list[dict] = []
        greeting, name = self._greeting(badge)
        self.screen.send({"type": "visitor", "name": name})
        self._say(greeting, source)
        endpointer = Endpointer()
        quiet_frames, asked = 0, False
        self._state("listening")
        for frame in source.frames():
            utterance = endpointer.feed(frame)
            if utterance is None:
                if endpointer.speaking:          # someone is mid-sentence: not silence
                    quiet_frames = 0
                    continue
                quiet_frames += 1
                waited = quiet_frames * FRAME_MS / 1000
                if not asked and waited >= self.still_there_s:
                    self._say("Still there?", source)
                    self._state("listening")
                    asked, quiet_frames = True, 0
                elif asked and waited >= self.give_up_s:
                    break
                continue
            quiet_frames, asked = 0, False
            self._state("thinking")
            text = self.hear(utterance).strip()
            if not text:
                self._state("listening")
                continue
            self.screen.send({"type": "heard", "text": text})
            if GOODBYE.search(text):
                self._say(f"Bye{', ' + name.split()[0] if name else ''}! Enjoy the event.", source)
                break
            prefix = self._context(name, badge) if not conversation else ""
            asked = conversation + [{"role": "user", "content": prefix + text}]
            reply = []
            for sentence in sentences(self.think(asked)):
                reply.append(sentence)
                self._say(sentence, source)
            if reply:
                conversation[:] = asked + [{"role": "assistant", "content": " ".join(reply)}]
            else:        # the model said nothing: ask again, and keep the history valid (no empty turns)
                self._say(ASK_AGAIN, source)
            self._state("listening")
        self.screen.send({"type": "visitor", "name": None})
        self._state("idle")
        return conversation

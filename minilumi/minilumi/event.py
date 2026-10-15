"""The event Lumi knows about: rooms, sessions and attendees, loaded from CSV files."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

PERSONA = (
    "You are Lumi, a friendly voice concierge at an event. People talk to you out loud and hear your answers "
    "spoken, so answer in one to three short sentences, with no lists, no markdown and no emoji. "
    "Use only the event facts below; if you don't know something, say so and suggest the help desk."
)


@dataclass(frozen=True)
class Room:
    name: str
    floor: str
    directions: str


@dataclass(frozen=True)
class Session:
    title: str
    room: str
    start: datetime
    end: datetime
    speaker: str


@dataclass(frozen=True)
class Attendee:
    badge: str
    name: str
    sessions: tuple[str, ...]


def _badge(raw: str) -> str:
    return raw.strip().upper()


def spoken_time(t: datetime) -> str:
    return t.strftime("%I:%M %p").lstrip("0")


@dataclass(frozen=True)
class Event:
    about: str
    rooms: tuple[Room, ...]
    sessions: tuple[Session, ...]
    attendees: dict[str, Attendee]

    def attendee(self, badge: str) -> Attendee | None:
        return self.attendees.get(_badge(badge))

    def next_sessions(self, now: datetime, badge: str | None = None, limit: int = 3) -> list[Session]:
        person = self.attendee(badge) if badge else None
        upcoming = [s for s in self.sessions if s.end > now and (person is None or s.title in person.sessions)]
        return sorted(upcoming, key=lambda s: s.start)[:limit]

    def system_prompt(self) -> str:
        rooms = "\n".join(f"- {r.name} (floor {r.floor}): {r.directions}" for r in self.rooms)
        sessions = "\n".join(
            f"- {s.title}: {spoken_time(s.start)} to {spoken_time(s.end)}, {s.room}"
            + (f", with {s.speaker}" if s.speaker else "")
            for s in sorted(self.sessions, key=lambda s: s.start))
        return f"{PERSONA}\n\nAbout the event:\n{self.about}\n\nRooms:\n{rooms}\n\nSessions:\n{sessions}\n"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def load_event(directory: Path) -> Event:
    directory = Path(directory)
    rooms = tuple(Room(r["name"], r["floor"], r["directions"]) for r in _rows(directory / "rooms.csv"))
    sessions = tuple(
        Session(r["title"], r["room"], datetime.fromisoformat(r["start"]), datetime.fromisoformat(r["end"]),
                r.get("speaker", ""))
        for r in _rows(directory / "sessions.csv"))
    attendees = {}
    for r in _rows(directory / "attendees.csv"):
        titles = tuple(t.strip() for t in r.get("sessions", "").split(";") if t.strip())
        attendees[_badge(r["badge"])] = Attendee(_badge(r["badge"]), r["name"], titles)
    about = (directory / "event.txt").read_text(encoding="utf-8").strip()
    return Event(about, rooms, sessions, attendees)

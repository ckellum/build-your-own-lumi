"""The event Lumi knows about: rooms, sessions and attendees, loaded from CSV files."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path

from .config import ConfigError

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


def spoken_day(t: datetime | date) -> str:
    """"Tuesday, May 14": how a day is said aloud (and how the model is told which day it is)."""
    return f"{t:%A, %B} {t.day}"


@dataclass(frozen=True)
class Event:
    about: str
    rooms: tuple[Room, ...]
    sessions: tuple[Session, ...]
    attendees: dict[str, Attendee]
    persona: str = PERSONA          # a folder's persona.txt replaces it (e.g. a personal assistant)

    def attendee(self, badge: str) -> Attendee | None:
        return self.attendees.get(_badge(badge))

    def next_sessions(self, now: datetime, badge: str | None = None, limit: int = 3) -> list[Session]:
        person = self.attendee(badge) if badge else None
        upcoming = [s for s in self.sessions if s.end > now and (person is None or s.title in person.sessions)]
        return sorted(upcoming, key=lambda s: s.start)[:limit]

    def system_prompt(self) -> str:
        rooms = "\n".join(f"- {r.name} (floor {r.floor}): {r.directions}" for r in self.rooms)
        several_days = len({s.start.date() for s in self.sessions}) > 1      # then each line says which day
        sessions = "\n".join(
            f"- {spoken_day(s.start) + ': ' if several_days else ''}{s.title}: "
            f"{spoken_time(s.start)} to {spoken_time(s.end)}, {s.room}"
            + (f", with {s.speaker}" if s.speaker else "")
            for s in sorted(self.sessions, key=lambda s: s.start))
        return f"{self.persona}\n\nFacts:\n{self.about}\n\nRooms and places:\n{rooms}\n\nSchedule:\n{sessions}\n"


def _read_text(path: Path) -> str:
    """UTF-8 (with or without BOM), or the Windows encoding Excel uses when it saves CSV."""
    data = path.read_bytes()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252")


def _rows(path: Path, columns: tuple[str, ...]) -> list[tuple[int, dict[str, str]]]:
    """(row number, row) pairs; row 1 is the header. Mistakes raise ConfigError naming file and row."""
    try:
        reader = csv.DictReader(io.StringIO(_read_text(path)))
        header = [h.strip() for h in reader.fieldnames or []]
    except FileNotFoundError:
        raise ConfigError(f"{path} is missing") from None
    for column in columns:
        if column not in header:
            raise ConfigError(f"{path.name} is missing the '{column}' column (it has: {', '.join(header)})")
    rows = []
    for number, row in enumerate(reader, start=2):
        if None in row:
            raise ConfigError(f"{path.name} row {number} has too many commas; put quotes around text that contains one")
        rows.append((number, {(k or "").strip(): (v or "").strip() for k, v in row.items()}))
    return rows


def _time(path: Path, number: int, row: dict[str, str], column: str) -> datetime:
    value = row[column]
    try:
        if len(value) <= 5:                 # "08:30": a daily routine, so it means today
            return datetime.combine(date.today(), time.fromisoformat(value.zfill(5)))
        return datetime.fromisoformat(value)
    except ValueError:
        raise ConfigError(f"{path.name} row {number}: {column} must look like 2030-05-14 10:00 (or 10:00 for today), "
                          f"not {value!r}") from None


def load_event(directory: Path) -> Event:
    directory = Path(directory)
    path = directory / "rooms.csv"
    rooms = tuple(Room(r["name"], r["floor"], r["directions"]) for _, r in _rows(path, ("name", "floor", "directions")))
    path = directory / "sessions.csv"
    sessions = tuple(
        Session(r["title"], r["room"], _time(path, n, r, "start"), _time(path, n, r, "end"), r.get("speaker", ""))
        for n, r in _rows(path, ("title", "room", "start", "end")))
    attendees = {}
    for _, r in _rows(directory / "attendees.csv", ("badge", "name")):
        titles = tuple(t.strip() for t in r.get("sessions", "").split(";") if t.strip())
        attendees[_badge(r["badge"])] = Attendee(_badge(r["badge"]), r["name"], titles)
    try:
        about = _read_text(directory / "event.txt").strip()
    except FileNotFoundError:
        raise ConfigError(f"{directory / 'event.txt'} is missing") from None
    persona_file = directory / "persona.txt"
    persona = _read_text(persona_file).strip() if persona_file.exists() else PERSONA
    return Event(about, rooms, sessions, attendees, persona)

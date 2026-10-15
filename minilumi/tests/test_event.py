from datetime import datetime
from pathlib import Path

from minilumi.event import load_event

EV = load_event(Path(__file__).resolve().parents[1] / "example-event")


def test_badge_lookup_ignores_case_and_spaces():
    assert EV.attendee("  ex-0001 ").name == "Ada Park"
    assert EV.attendee("nope") is None


def test_next_sessions_for_attendee_are_upcoming_and_theirs():
    got = EV.next_sessions(datetime(2030, 5, 14, 9, 50), "EX-0001")
    assert [s.title for s in got] == ["Voice Interfaces 101", "Prompting for Speech"]


def test_next_sessions_without_badge_are_everyones_upcoming():
    now = datetime(2030, 5, 14, 9, 50)
    got = EV.next_sessions(now)
    assert len(got) == 3 and all(s.end > now for s in got)
    assert got == sorted(got, key=lambda s: s.start)


def test_session_in_progress_still_counts_as_next():
    got = EV.next_sessions(datetime(2030, 5, 14, 10, 20), "EX-0001")
    assert got[0].title == "Voice Interfaces 101"


def test_system_prompt_has_rooms_and_sessions_but_no_attendees():
    p = EV.system_prompt()
    assert "Maple Room" in p and "Voice Interfaces 101" in p and "10:00 AM" in p
    assert "Ada Park" not in p

---
description: Turn your event's agenda, rooms and attendees (in any format) into Lumi's event files
argument-hint: [paste or describe your event]
---

Make Lumi's event files from what the user gives you:

$ARGUMENTS

If that's empty, ask them to paste their agenda, room list and attendees in any form (a spreadsheet
copy, an email, a web page, notes) or to describe the event.

1. Read `minilumi/example-event/` to see the exact format, and the "Event files" section of CLAUDE.md.
2. Write the files into `minilumi/my-event/` (it's git-ignored, so real names stay off GitHub):
   `rooms.csv`, `sessions.csv`, `attendees.csv` and `event.txt`. Put quotes around text with commas.
3. **Don't invent facts.** If something Lumi needs is missing, ask, in one short list: the date, how
   to walk to each room from the entrance (written the way you'd say it), where lunch, restrooms and
   Wi-Fi are. If they don't have attendees yet, make one test badge for them (`ME-0001`) and say so.
4. Set `event_dir = "my-event"` in `minilumi/config.toml`.
5. Check it loads: `uv run python -c "from minilumi.event import load_event; e = load_event('my-event'); print(len(e.rooms), 'rooms,', len(e.sessions), 'sessions,', len(e.attendees), 'attendees')"`
   from `minilumi/`. Fix any error it names (file and row).
6. Check that every session's room exists and every attendee's session titles match exactly, and
   list any that don't.
7. Show the user a short summary (counts and two or three sample rows, not the whole attendee list)
   and how to try it: `uv run minilumi run --preset <preset> --input samples/hello.wav --badge <one of
   their badges> --mute --no-screen`. The greeting should name that person's next session (and its day,
   if it isn't today). The recording itself asks about "Voice Interfaces 101" from the example event,
   so tell them not to expect a real answer to it; for that, run live and ask about their own sessions.

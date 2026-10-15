# Build Your Own Lumi

You're helping someone build **minilumi**, a small voice concierge: a badge scan (or Enter) starts a
visit, the visitor asks a question out loud, and Lumi answers out loud with a talking face in the
browser. Many people using this are beginners. Explain what you're doing in plain words, show changes
before making them, and prefer teaching over doing everything silently.

## Layout

- `minilumi/`: the kit. **Run every `uv` command from this folder.**
  - `config.toml`: three presets (`workstation`, `laptop`, `cloud`), each with `hear`, `think` and
    `speak` backends, plus `event_dir` (which folder of event files to load) and `screen_port`.
  - `minilumi/listen.py`: when the visitor has finished talking. `hear.py`: speech to text.
    `think.py`: the language model (OpenAI-compatible servers, or Anthropic). `speak.py`: text to
    speech. `visit.py`: the conversation loop. `screen.py` and `ui/`: the face, over Server-Sent Events.
    `event.py`: loads the event files and builds the system prompt. `cli.py`: `check` and `run`.
  - `example-event/`: made-up "Example Con" data. `examples/my-day/`: a made-up personal assistant.
  - `samples/hello.wav`, `samples/my-day.wav`: recorded questions for testing with no microphone.
    `hello.wav` asks "Hi Lumi, where's Voice Interfaces 101?", a session in `example-event/` only.
- `index.html`, `css/`, `js/`: the guide website (GitHub Pages). `talk/`: the slides.
- `tools/leak-check.py`: a pre-push check that keeps private data out of the repo.

## Event files

A folder with `rooms.csv` (`name,floor,directions`), `sessions.csv` (`title,room,start,end,speaker`),
`attendees.csv` (`badge,name,sessions`, with session titles separated by `;`), `event.txt` (free-text
facts) and, optionally, `persona.txt` (replaces the default personality). Times look like
`2030-05-14 10:00`, or `10:00` for "today". Text with a comma must be in double quotes. `room` in
sessions.csv must match a `name` in rooms.csv, and every title in `attendees.csv` must match a session
title exactly. Directions are spoken aloud, so write them the way you'd say them.

## Commands (from `minilumi/`)

- Tests: `uv run pytest -q` (they need no models, microphone or network). Keep them passing.
- Check each backend once: `uv run minilumi check --preset laptop`
- One visit from a recording, no audio or screen: `uv run minilumi run --preset laptop --input samples/hello.wav --badge EX-0001 --mute --no-screen`
- Live, with the face at http://127.0.0.1:8765/: `uv run minilumi run --preset laptop`
- Install: `uv sync --extra local` for laptop (speech runs in-process), `uv sync` for workstation or cloud.

`run` without `--input` waits for Enter and uses the real microphone. Don't start it on the user's
behalf unless they asked; tell them the command instead.

## Rules

- **Real people's data goes in `minilumi/my-event/` only.** It's git-ignored. Never commit it, never
  copy it into `example-event/`, tests or docs, and never echo attendee lists back in full.
- **API keys come from environment variables** (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`), never from
  `config.toml` or the chat. If a key is missing, tell the user how to set it themselves.
- Answers are spoken: personas must ask for one to three short sentences, with no lists, markdown or emoji.
- Don't change model choices in `config.toml` unless the user asks.
- After changing code, run `uv run pytest -q` and show the result.

# minilumi

A small voice concierge you can run on your own computer: scan a badge (or press Enter),
ask a question out loud, and Lumi answers out loud, with a talking avatar in your browser.

```
microphone → hear (speech to text) → think (language model) → speak (text to speech) → speaker + screen
```

Full walkthrough: **https://ckellum.github.io/build-your-own-lumi/**

## Install

You need [uv](https://docs.astral.sh/uv/) (it installs the right Python for you).

```bash
git clone https://github.com/ckellum/build-your-own-lumi
cd build-your-own-lumi/minilumi
uv sync                  # cloud or workstation preset
uv sync --extra local    # laptop preset: Whisper and Kokoro run inside minilumi
```

Linux also needs PortAudio for the microphone and speaker: `sudo apt install libportaudio2`.

## Pick a preset

Presets live in `config.toml`. Each one says what hears, what thinks and what speaks.

| Preset | For | Hear | Think | Speak |
|---|---|---|---|---|
| `workstation` | 64 GB+ unified memory or a 24 GB+ GPU | your own Whisper/Parakeet server | your own llama.cpp server | your own Kokoro server |
| `laptop` | 32 GB RAM, or an 8–12 GB GPU, incl. Apple Silicon | faster-whisper, in-process | Ollama | Kokoro, in-process |
| `cloud` | any computer, no GPU | OpenAI-compatible API | Claude | OpenAI-compatible API |

For **laptop**, install [Ollama](https://ollama.com) and pull the model named in `config.toml`:

```bash
ollama pull qwen3:1.7b
```

For **cloud**, set your keys as environment variables (never in the file):

```bash
export ANTHROPIC_API_KEY=...
export OPENAI_API_KEY=...
```

More RAM? `ollama pull qwen3:8b` gives better answers; set `model` under
`[presets.laptop.think]` to match.

## Run

```bash
uv run minilumi check --preset laptop      # tries each backend once: ✓ or ✗ with what to fix
uv run minilumi run --preset laptop        # then open http://127.0.0.1:8765/ for the avatar
```

Press Enter to start a visit, or type a badge ID such as `EX-0001`. A USB barcode or QR scanner
types like a keyboard, so scanning a badge works with no extra code. Say "goodbye" to end a visit;
after 30 seconds of silence Lumi asks "Still there?" and ends the visit 15 seconds later.

No microphone handy? Feed it a recording:

```bash
uv run minilumi run --preset laptop --input samples/hello.wav --badge EX-0001
```

`--mute` skips playing audio; `--no-screen` skips the avatar page.

## Make it yours

Copy `example-event/` to `my-event/` (git-ignored, so real data stays out of git) and set
`event_dir = "my-event"` in `config.toml`. Then edit `event.txt` (anything Lumi should know),
`rooms.csv` (with spoken directions), `sessions.csv` and `attendees.csv` (badge, name, sessions).
Excel works: a CSV saved on Windows is read correctly, and a mistake names the file and row.
Lumi's personality is the `PERSONA` line at the top of `minilumi/event.py`.

## Not just events

`examples/my-day/` turns Lumi into a personal assistant for a made-up household (today's
calendar, places, house facts, its own `persona.txt`). Try it:

```bash
# in config.toml: event_dir = "examples/my-day"
uv run minilumi run --preset laptop --input samples/my-day.wav --badge ME --mute --no-screen
```

Any folder can include a `persona.txt` to replace Lumi's personality, and schedule times written
as just `09:30` mean today, so a daily routine never goes stale.

## Troubleshooting

- **"No microphone found (or permission denied)"**: on macOS, allow your terminal in
  System Settings → Privacy & Security → Microphone. On Windows, check Settings → Privacy → Microphone.
- **"cannot reach http://... Check think.base_url"**: the model server isn't running, or the URL in
  `config.toml` is wrong. For Ollama, run `ollama serve`.
- **Lumi hears herself**: use a headset or a directional mic; minilumi ignores what the mic heard while she spoke.
- **Slow first answer**: the first request loads the model. Later answers are faster.

## Tests

```bash
uv run pytest -q
```

MIT licensed.

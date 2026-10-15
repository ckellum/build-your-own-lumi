---
description: Give Lumi a new name, personality and voice, then hear it
argument-hint: [describe who she should be]
---

Give Lumi a new personality: $ARGUMENTS

If that's empty, ask who she should be: a name, a tone (warm, playful, formal, a character), and
where she works (an event, a front desk, a kitchen counter...).

1. Find the event folder from `event_dir` in `minilumi/config.toml`. If it's `example-event`, copy it
   to `minilumi/my-event/` first and point `event_dir` there, so the example stays untouched.
2. Write `persona.txt` in that folder. Start from the default `PERSONA` in `minilumi/minilumi/event.py`
   and keep its rules: answers are spoken, so one to three short sentences, no lists, no markdown, no
   emoji, and only facts from the event files ("if you don't know, say so"). Then add the new name,
   tone and any catchphrase. If the name isn't Lumi, add "If someone calls you Lumi, answer happily
   anyway." (people will, and the sample recordings do). Keep it under about 120 words.
   With a new name, also offer to update the one fixed line that says "I'm Lumi": `UNKNOWN_GREETING`
   in `minilumi/minilumi/visit.py` (the greeting for an unknown badge). Show the change first.
3. Suggest three Kokoro voices that fit (for example `af_heart`, `af_bella`, `am_michael`, `bf_emma`,
   `bm_george`), and set the one they pick as `voice` under the preset's `speak` in `config.toml`.
   The cloud preset uses OpenAI voices instead (`alloy`, `nova`, `shimmer`...).
4. Run the no-microphone test with their preset, but without `--mute` so they hear her:
   `uv run minilumi run --preset <preset> --input samples/hello.wav --badge EX-0001 --no-screen`
   (use one of their own badge IDs if they have a my-event folder with attendees). The recording asks
   "Hi Lumi, where's Voice Interfaces 101?", a session from the example event. If their event doesn't
   have it, say so: the run shows her voice and tone, and the live run (`uv run minilumi run --preset
   <preset>`) is where to ask about their own sessions.
5. Ask if they want it more or less over the top, and adjust.

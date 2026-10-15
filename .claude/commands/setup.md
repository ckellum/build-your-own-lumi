---
description: Install the kit, run its tests, and check each model for a preset
argument-hint: [workstation | laptop | cloud]
---

Set up minilumi for the **$ARGUMENTS** preset. If no preset was given, ask which one fits: `laptop`
(32 GB RAM or an 8–12 GB GPU, everything local), `workstation` (64 GB+ or a 24 GB+ GPU, model
servers) or `cloud` (any computer, API keys). Explain each step in a sentence as you go.

1. Check that `uv` is installed (`uv --version`). If it isn't, give the install command for this
   operating system from the README and wait for the user to run it.
2. In `minilumi/`, run `uv sync --extra local` for laptop, or `uv sync` for workstation and cloud.
   On Linux, if audio fails later, the fix is `sudo apt install libportaudio2`. Ask before running sudo.
3. Run `uv run pytest -q` and report the result. All tests should pass.
4. Make sure the preset's models are reachable:
   - laptop: is Ollama installed and running (`ollama list`)? Pull the model named under
     `[presets.laptop.think]` in `config.toml` if it's missing. The first run downloads speech
     models of a few hundred MB.
   - workstation: ask where their hear, think and speak servers run, and update the `base_url`s.
   - cloud: check whether `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` are set, without printing them.
     If not, tell the user how to set them; never ask them to paste a key into the chat.
5. Run `uv run minilumi check --preset <preset>`. For each ✗, explain the cause in plain words and fix
   what you can, then check again.
6. Finish with the no-microphone test: `uv run minilumi run --preset <preset> --input samples/hello.wav --badge EX-0001 --mute --no-screen`,
   and tell them what to try next: `uv run minilumi run --preset <preset>` and open http://127.0.0.1:8765/.

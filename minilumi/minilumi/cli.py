"""minilumi run | check"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .audio import AudioUnavailable, MicSource, Player, SilentPlayer, WavSource
from .config import ConfigError, load_config
from .errors import BackendError
from .event import load_event
from .hear import make_hearer
from .screen import NoScreen, Screen
from .speak import make_speaker
from .think import make_thinker
from .visit import Visit

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config.toml"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="minilumi", description="A small voice concierge.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, text in (("run", "start the concierge"), ("check", "test each model backend once")):
        p = commands.add_parser(name, help=text)
        p.add_argument("--preset", help="workstation, laptop or cloud (default: from config.toml)")
        p.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="path to config.toml")
    run = commands.choices["run"]
    run.add_argument("--input", type=Path, help="use a WAV file instead of the microphone (one visit)")
    run.add_argument("--badge", help="with --input: the badge to greet")
    run.add_argument("--mute", action="store_true", help="don't play audio")
    run.add_argument("--no-screen", action="store_true", help="don't serve the avatar page")
    return parser


class Echo:
    """Passes screen messages on, and prints the conversation in the terminal."""

    def __init__(self, screen):
        self._screen = screen

    def send(self, message: dict) -> None:
        if message.get("type") == "heard":
            print(f"You: {message['text']}", flush=True)
        elif message.get("type") == "say":
            print(f"Lumi: {message['text']}", flush=True)
        self._screen.send(message)

    def stop(self) -> None:
        self._screen.stop()


def _check(args) -> int:
    cfg = load_config(args.config, args.preset)
    event = load_event(cfg.event_dir)
    probes = {
        "hear": lambda: make_hearer(cfg.hear)(b"\0\0" * 8000),
        "think": lambda: "".join(make_thinker(cfg.think, event.system_prompt())(
            [{"role": "user", "content": "Say OK."}])),
        "speak": lambda: make_speaker(cfg.speak)("OK."),
    }
    ok = True
    for role, probe in probes.items():
        try:
            probe()
            print(f"✓ {role}: {getattr(cfg, role).kind} {getattr(cfg, role).model}")
        except BackendError as exc:
            ok = False
            print(f"✗ {exc}")
    return 0 if ok else 1


def _run(args, stdin) -> int:
    cfg = load_config(args.config, args.preset)
    event = load_event(cfg.event_dir)
    source = WavSource(args.input) if args.input else None
    player = SilentPlayer() if args.mute else Player()
    hear, think, speak = make_hearer(cfg.hear), make_thinker(cfg.think, event.system_prompt()), make_speaker(cfg.speak)
    try:
        screen = NoScreen() if args.no_screen else Screen(cfg.screen_port)
    except OSError:
        raise ConfigError(f"screen_port {cfg.screen_port} is busy (is another minilumi running?); "
                          f"change screen_port in config.toml or use --no-screen") from None
    if not args.no_screen:
        screen.start()
        print(f"screen: open http://127.0.0.1:{screen.port}/ in a browser", flush=True)
    visit = Visit(event=event, hear=hear, think=think, speak=speak, player=player, screen=Echo(screen))
    try:
        if source is not None:
            visit.run(args.badge, source)
            return 0
        print("Press Enter to start a visit, or type (or scan) a badge ID. Ctrl-C quits.", flush=True)
        for line in stdin:
            mic = MicSource()
            try:
                visit.run(line.strip() or None, mic)
            finally:
                mic.close()
            print("Visit over. Press Enter or scan a badge for the next one.", flush=True)
        return 0
    finally:
        screen.stop()


def main(argv: list[str] | None = None, stdin=None) -> int:
    args = _parser().parse_args(argv)
    for stream in (sys.stdout, sys.stderr):      # e.g. a Windows console that can't print ✓
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    try:
        if args.command == "check":
            return _check(args)
        return _run(args, stdin or sys.stdin)
    except (ConfigError, BackendError, AudioUnavailable) as exc:
        print(f"minilumi: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())

"""Reads config.toml: which backend hears, which thinks, which speaks."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


class ConfigError(ValueError):
    """The config file is missing something; the message names what."""


@dataclass(frozen=True)
class Backend:
    kind: str              # hear: whisper-local | openai; think: openai | anthropic; speak: kokoro-local | openai
    model: str
    base_url: str = ""     # for kind "openai"
    api_key_env: str = ""  # name of the environment variable holding the key ("" = no key needed)
    voice: str = ""        # speak only


@dataclass(frozen=True)
class Config:
    preset: str
    hear: Backend
    think: Backend
    speak: Backend
    event_dir: Path
    screen_port: int = 8765


def _require(table: dict, key: str, where: str, path: Path):
    if key not in table:
        raise ConfigError(f"missing {where + '.' if where else ''}{key} in {path}")
    return table[key]


def _backend(table: dict, where: str, path: Path) -> Backend:
    return Backend(
        kind=_require(table, "kind", where, path),
        model=_require(table, "model", where, path),
        base_url=table.get("base_url", "").rstrip("/"),
        api_key_env=table.get("api_key_env", ""),
        voice=table.get("voice", ""),
    )


def load_config(path: Path, preset: str | None = None) -> Config:
    path = Path(path)
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path} is not valid TOML: {exc}") from None
    presets = data.get("presets", {})
    name = preset or _require(data, "default_preset", "", path).strip()
    if name not in presets:
        raise ConfigError(f"unknown preset {name!r}; choose one of: {', '.join(sorted(presets))}")
    chosen = presets[name]
    roles = {role: _backend(_require(chosen, role, f"presets.{name}", path), f"presets.{name}.{role}", path)
             for role in ("hear", "think", "speak")}
    return Config(
        preset=name,
        event_dir=(path.parent / _require(data, "event_dir", "", path)).resolve(),
        screen_port=int(data.get("screen_port", 8765)),
        **roles,
    )

from pathlib import Path

import pytest

from minilumi.config import ConfigError, load_config

ROOT = Path(__file__).resolve().parents[1]


def test_default_preset_loads():
    cfg = load_config(ROOT / "config.toml")
    assert cfg.preset == "laptop"
    assert cfg.think.kind == "openai" and cfg.hear.kind == "whisper-local" and cfg.speak.kind == "kokoro-local"


@pytest.mark.parametrize("name", ["workstation", "laptop", "cloud"])
def test_every_preset_loads(name):
    assert load_config(ROOT / "config.toml", name).preset == name


def test_unknown_preset_lists_choices():
    with pytest.raises(ConfigError, match="cloud, laptop, workstation"):
        load_config(ROOT / "config.toml", "potato")


def test_missing_key_is_named(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text('default_preset = "x"\nevent_dir = "e"\n[presets.x.hear]\nkind="openai"\nmodel="m"\n'
                 '[presets.x.speak]\nkind="openai"\nmodel="m"\n')
    with pytest.raises(ConfigError, match="presets.x.think"):
        load_config(p)


def test_event_dir_is_relative_to_the_config_file():
    cfg = load_config(ROOT / "config.toml")
    assert cfg.event_dir == ROOT / "example-event"


def test_cloud_think_uses_anthropic_key_env():
    cfg = load_config(ROOT / "config.toml", "cloud")
    assert cfg.think.kind == "anthropic" and cfg.think.api_key_env == "ANTHROPIC_API_KEY"

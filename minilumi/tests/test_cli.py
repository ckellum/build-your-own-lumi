import io

from minilumi import cli
from minilumi.audio import AudioUnavailable


class NoMic:
    def __init__(self, *a, **k):
        raise AudioUnavailable("No microphone found (or permission denied). Try: minilumi run --input sample.wav")


def test_missing_mic_is_one_line_and_exit_2(monkeypatch, capsys):
    monkeypatch.setattr(cli, "MicSource", NoMic)
    assert cli.main(["run", "--preset", "workstation", "--no-screen", "--mute"], stdin=io.StringIO("\n")) == 2
    err = capsys.readouterr().err
    assert "No microphone" in err and "Traceback" not in err


def test_bad_preset_is_one_line_and_exit_2(capsys):
    assert cli.main(["run", "--preset", "potato"]) == 2
    assert "choose one of" in capsys.readouterr().err


def test_missing_input_file_is_one_line_and_exit_2(capsys):
    assert cli.main(["run", "--preset", "workstation", "--no-screen", "--input", "nope.wav"]) == 2
    assert "nope.wav" in capsys.readouterr().err


def test_unreachable_backend_during_a_visit_is_one_line_and_exit_2(tmp_path, capsys):
    cfg = tmp_path / "c.toml"
    event = (cli.DEFAULT_CONFIG.parent / "example-event").as_posix()
    cfg.write_text(f'default_preset = "x"\nevent_dir = "{event}"\n'
                   + "".join(f'[presets.x.{r}]\nkind = "openai"\nmodel = "m"\nbase_url = "http://127.0.0.1:9/v1"\n'
                             for r in ("hear", "think", "speak")))
    wav = tmp_path / "in.wav"
    import wave
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(b"\0\0" * 16000)
    assert cli.main(["run", "--config", str(cfg), "--no-screen", "--mute", "--input", str(wav)]) == 2
    err = capsys.readouterr().err
    assert "speak.base_url" in err and "Traceback" not in err


def test_missing_audio_library_is_one_line_and_exit_2(monkeypatch, capsys):
    import minilumi.audio as audio

    def no_portaudio():
        raise AudioUnavailable("audio is unavailable (PortAudio library not found). Try --input file.wav and --mute")
    monkeypatch.setattr(audio, "_sounddevice", no_portaudio)
    assert cli.main(["run", "--preset", "workstation", "--no-screen"], stdin=io.StringIO("\n")) == 2
    err = capsys.readouterr().err
    assert "--mute" in err and "Traceback" not in err


def _talking_wav(path):
    import wave
    import numpy as np
    quiet = np.zeros(16000, dtype="<i2")
    voice = (np.sin(np.arange(16000) / 3) * 8000).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(np.concatenate([quiet, voice, quiet]).tobytes())


def test_conversation_is_echoed_to_the_terminal(fake, tmp_path, capsys):
    cfg = tmp_path / "c.toml"
    event = (cli.DEFAULT_CONFIG.parent / "example-event").as_posix()
    cfg.write_text(f'default_preset = "x"\nevent_dir = "{event}"\n'
                   + "".join(f'[presets.x.{r}]\nkind = "openai"\nmodel = "m"\nbase_url = "{fake.url}"\n'
                             for r in ("hear", "think", "speak")))
    _talking_wav(tmp_path / "in.wav")
    assert cli.main(["run", "--config", str(cfg), "--no-screen", "--mute", "--input", str(tmp_path / "in.wav"),
                     "--badge", "EX-0001"]) == 0
    out = capsys.readouterr().out
    assert "Lumi: Hi Ada!" in out and "You: hello" in out and "Lumi: Hi there." in out

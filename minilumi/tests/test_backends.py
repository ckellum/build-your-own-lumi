import pytest

from minilumi.config import Backend
from minilumi.errors import BackendError
from minilumi.hear import make_hearer
from minilumi.speak import make_speaker
from minilumi.think import make_thinker

USER = [{"role": "user", "content": "hi"}]


def test_openai_hear_sends_wav_and_returns_trimmed_text(fake):
    hear = make_hearer(Backend("openai", "whisper-1", fake.url))
    assert hear(b"\0\0" * 1600) == "hello"
    seen = fake.requests[-1]
    assert seen.path == "/v1/audio/transcriptions"
    assert b"RIFF" in seen.body and b'name="model"' in seen.body


def test_openai_think_streams_and_strips_think_tags(fake):
    think = make_thinker(Backend("openai", "m", fake.url), "sys")
    assert "".join(think(USER)) == "Hi there."
    body = fake.requests[-1].json
    assert body["messages"][0] == {"role": "system", "content": "sys"}
    assert body["stream"] is True and body["model"] == "m"


def test_openai_speak_asks_for_wav_and_returns_its_pcm_and_rate(fake):
    pcm, sr = make_speaker(Backend("openai", "kokoro", fake.url, voice="af_heart"))("hi")
    assert sr == 22050 and len(pcm) == 4410
    body = fake.requests[-1].json
    assert body["voice"] == "af_heart" and body["response_format"] == "wav"


def test_api_key_is_sent_as_bearer(fake, monkeypatch):
    monkeypatch.setenv("MY_KEY", "sk-test")
    make_hearer(Backend("openai", "w", fake.url, api_key_env="MY_KEY"))(b"\0\0")
    assert fake.requests[-1].headers["Authorization"] == "Bearer sk-test"


def test_unreachable_server_names_the_config_key():
    think = make_thinker(Backend("openai", "m", "http://127.0.0.1:9/v1"), "sys")
    with pytest.raises(BackendError, match="think.base_url"):
        list(think(USER))


def test_rejected_key_names_the_env_var(fake_401, monkeypatch):
    monkeypatch.setenv("MY_KEY", "wrong")
    hear = make_hearer(Backend("openai", "w", fake_401.url, api_key_env="MY_KEY"))
    with pytest.raises(BackendError, match="MY_KEY"):
        hear(b"\0\0")


def test_missing_api_key_names_the_env_var(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(BackendError, match="ANTHROPIC_API_KEY"):
        make_thinker(Backend("anthropic", "claude-haiku-5-5", api_key_env="ANTHROPIC_API_KEY"), "sys")


def test_unknown_kind_is_explained():
    with pytest.raises(BackendError, match="hear.kind"):
        make_hearer(Backend("telepathy", "x"))


def test_think_tags_split_across_chunks_are_removed():
    from minilumi.think import strip_thinking
    assert "".join(strip_thinking(iter(["<thi", "nk>plan</th", "ink>", "Hello", " <", "b>"]))) == "Hello <b>"


def test_local_whisper_runs_on_cpu(monkeypatch):
    import sys, types
    seen = {}

    class FakeModel:
        def __init__(self, name, **kw):
            seen.update(kw)

        def transcribe(self, audio, **kw):
            return [types.SimpleNamespace(text=" hi ")], None
    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeModel))
    assert make_hearer(Backend("whisper-local", "base.en"))(b"\0\0" * 1600) == "hi"
    assert seen["device"] == "cpu"


def test_local_whisper_download_failure_is_explained(monkeypatch):
    import sys, types

    def boom(*a, **k):
        raise OSError("network is unreachable")
    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=boom))
    with pytest.raises(BackendError, match="hear.*Whisper"):
        make_hearer(Backend("whisper-local", "base.en"))


def test_claude_is_asked_not_to_think_for_spoken_answers(monkeypatch):
    import anthropic
    seen = {}

    class FakeStream:
        text_stream = iter(["Hi."])
        def __enter__(self): return self
        def __exit__(self, *a): return False

    class FakeClient:
        def __init__(self, **k):
            self.messages = self

        def stream(self, **kw):
            seen.update(kw)
            return FakeStream()
    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    think = make_thinker(Backend("anthropic", "claude-haiku-5-5", api_key_env="ANTHROPIC_API_KEY"), "sys")
    assert "".join(think(USER)) == "Hi."
    assert seen["thinking"] == {"type": "disabled"}

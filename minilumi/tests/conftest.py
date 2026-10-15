import pytest

from fake_server import FakeOpenAI


@pytest.fixture
def fake():
    server = FakeOpenAI()
    yield server
    server.close()


@pytest.fixture
def fake_401():
    server = FakeOpenAI(status=401)
    yield server
    server.close()


class FastPlayer:
    """Plays nothing, instantly; remembers what it was given."""
    def __init__(self):
        self.played = []

    def play(self, pcm, sample_rate):
        self.played.append((len(pcm), sample_rate))


class ListScreen:
    def __init__(self):
        self.messages = []

    def send(self, message):
        self.messages.append(message)


class ListSource:
    """An audio source made from a list of 20 ms frames."""
    def __init__(self, frames):
        self._frames = list(frames)
        self.drained = 0

    def frames(self):
        yield from self._frames

    def drain(self):
        self.drained += 1

    def close(self):
        pass

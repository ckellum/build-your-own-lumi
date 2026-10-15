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

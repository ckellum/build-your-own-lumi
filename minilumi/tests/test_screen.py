import json
import threading
import urllib.request

from minilumi.screen import Screen


def test_page_is_served_and_events_reach_the_browser():
    screen = Screen(0)
    screen.start()
    try:
        page = urllib.request.urlopen(f"http://127.0.0.1:{screen.port}/", timeout=5).read().decode()
        assert "<main" in page and "app.js" in page
        got = []
        stream = urllib.request.urlopen(f"http://127.0.0.1:{screen.port}/events", timeout=5)

        def read_two():
            while len(got) < 2:
                line = stream.readline().decode().strip()
                if line.startswith("data:"):
                    got.append(json.loads(line[5:]))
        reader = threading.Thread(target=read_two)
        reader.start()
        screen.send({"type": "say", "text": "Hello", "envelope": [0.5], "step_ms": 20})
        reader.join(5)
        assert got[0] == {"type": "state", "state": "idle"}          # newcomers get the current state first
        assert got[1]["text"] == "Hello"
    finally:
        screen.stop()

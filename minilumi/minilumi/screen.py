"""The kiosk screen: a tiny local web server that pushes Lumi's state to a browser page."""

from __future__ import annotations

import json
import queue
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

UI_DIR = Path(__file__).with_name("ui")


class Screen:
    def __init__(self, port: int):
        self.port = port
        self._clients: list[queue.Queue[str]] = []
        self._lock = threading.Lock()
        self._last_state = json.dumps({"type": "state", "state": "idle"})
        screen = self

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(UI_DIR), **kwargs)

            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path != "/events":
                    return super().do_GET()
                inbox: queue.Queue[str] = queue.Queue()
                with screen._lock:          # register before answering, so nothing sent meanwhile is lost
                    inbox.put(screen._last_state)
                    screen._clients.append(inbox)
                try:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    while True:
                        try:
                            data = inbox.get(timeout=15)
                        except queue.Empty:
                            data = None
                        self.wfile.write(b": ping\n\n" if data is None else f"data: {data}\n\n".encode())
                        self.wfile.flush()
                except (ConnectionError, OSError):    # browser tab closed (Windows raises ConnectionAbortedError)
                    pass
                finally:
                    with screen._lock:
                        screen._clients.remove(inbox)

        self._server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self._server.daemon_threads = True
        self.port = self._server.server_port

    def start(self) -> None:
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def send(self, message: dict) -> None:
        data = json.dumps(message)
        with self._lock:
            if message.get("type") == "state":
                self._last_state = data
            for inbox in self._clients:
                inbox.put(data)

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


class NoScreen:
    def send(self, message: dict) -> None:
        pass

    def stop(self) -> None:
        pass

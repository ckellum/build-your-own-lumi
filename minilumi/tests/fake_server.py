"""A tiny OpenAI-compatible server for tests: canned answers, and a record of every request."""

from __future__ import annotations

import io
import json
import wave
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


@dataclass
class Seen:
    path: str
    headers: dict
    body: bytes

    @property
    def json(self):
        return json.loads(self.body)


CHAT_CHUNKS = ["<think>x</think>Hi", " there", "."]


class FakeOpenAI:
    def __init__(self, status: int = 200):
        self.requests: list[Seen] = []
        self.status = status
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                fake.requests.append(Seen(self.path, dict(self.headers), body))
                if fake.status != 200:
                    self.send_response(fake.status)
                    self.end_headers()
                    self.wfile.write(b'{"error": "nope"}')
                    return
                if self.path.endswith("/audio/transcriptions"):
                    self._send(b'{"text": " hello "}', "application/json")
                elif self.path.endswith("/chat/completions"):
                    lines = [f"data: {json.dumps({'choices': [{'delta': {'content': c}}]})}\n\n" for c in CHAT_CHUNKS]
                    self._send("".join(lines + ["data: [DONE]\n\n"]).encode(), "text/event-stream")
                elif self.path.endswith("/audio/speech"):
                    buf = io.BytesIO()
                    with wave.open(buf, "wb") as w:
                        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
                        w.writeframes(b"\x01\x00" * 2205)
                    self._send(buf.getvalue(), "audio/wav")
                else:
                    self.send_response(404)
                    self.end_headers()

            def _send(self, data: bytes, kind: str):
                self.send_response(200)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()

"""Think: send the conversation to a language model and stream the reply back."""

from __future__ import annotations

from collections.abc import Callable, Iterator

from .config import Backend
from .errors import BackendError
from .http import api_key, post_json, sse_data

Thinker = Callable[[list[dict]], Iterator[str]]


def make_thinker(b: Backend, system: str) -> Thinker:
    if b.kind == "openai":
        return _openai(b, system)
    if b.kind == "anthropic":
        return _anthropic(b, system)
    raise BackendError(f"unknown think.kind {b.kind!r}; use 'openai' or 'anthropic'")


def strip_thinking(chunks: Iterator[str]) -> Iterator[str]:
    """Drop <think>...</think> blocks (some small models think out loud) even when split across chunks."""
    buffer, inside = "", False
    for chunk in chunks:
        buffer += chunk
        while True:
            tag = "</think>" if inside else "<think>"
            at = buffer.find(tag)
            if at >= 0:
                if not inside and at:
                    yield buffer[:at]
                buffer, inside = buffer[at + len(tag):], not inside
                continue
            keep = next((n for n in range(len(tag) - 1, 0, -1) if buffer.endswith(tag[:n])), 0)
            if not inside and len(buffer) > keep:
                yield buffer[:len(buffer) - keep]
            buffer = buffer[len(buffer) - keep:] if keep else ""
            break
    if buffer and not inside:
        yield buffer


def _openai(b: Backend, system: str) -> Thinker:
    def think(messages: list[dict]) -> Iterator[str]:
        payload = {"model": b.model, "stream": True, "max_tokens": 300, "temperature": 0.6,
                   "messages": [{"role": "system", "content": system}, *messages],
                   "chat_template_kwargs": {"enable_thinking": False}}

        def chunks() -> Iterator[str]:
            for event in sse_data(post_json(b, "think", "/chat/completions", payload)):
                choices = event.get("choices") or [{}]
                text = (choices[0].get("delta") or {}).get("content")
                if text:
                    yield text
        yield from strip_thinking(chunks())
    return think


def _anthropic(b: Backend, system: str) -> Thinker:
    key = api_key(b, "think")
    try:
        import anthropic
    except ImportError:
        raise BackendError("think: the anthropic package is missing: uv sync") from None
    client = anthropic.Anthropic(api_key=key)

    def think(messages: list[dict]) -> Iterator[str]:
        try:
            with client.messages.stream(model=b.model, max_tokens=300, system=system, messages=messages) as stream:
                yield from stream.text_stream
        except anthropic.AuthenticationError:
            raise BackendError(f"think: Anthropic refused the key; check {b.api_key_env}") from None
        except anthropic.APIConnectionError as exc:
            raise BackendError(f"think: cannot reach Anthropic ({exc})") from None
        except anthropic.APIStatusError as exc:
            raise BackendError(f"think: Anthropic answered HTTP {exc.status_code}; check think.model") from None
    return think

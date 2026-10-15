"""Errors that tell the person running minilumi what to fix."""


class BackendError(RuntimeError):
    """A model backend failed; the message says what to check."""

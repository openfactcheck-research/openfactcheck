"""Errors raised by the RARR components."""


class RARRError(Exception):
    """Base class for errors raised by the RARR components."""


class RARRConfigError(RARRError):
    """An optional dependency or configuration the RARR components need is missing."""

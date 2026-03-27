"""Tests for main module."""

from openfactcheck.main import greet


def test_greet():
    """Greet function returns expected message."""
    assert greet() == "Hello from OpenFactCheck v2"


def test_greet_not_empty():
    """Greet function returns non-empty string."""
    assert len(greet()) > 0


def test_greet_contains_version():
    """Greet function mentions v2."""
    assert "v2" in greet()

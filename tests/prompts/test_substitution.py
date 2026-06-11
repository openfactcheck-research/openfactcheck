"""Tests for the placeholder substitution engine."""

from __future__ import annotations

import pytest

from openfactcheck.prompts._substitution import find_placeholders, substitute


# ---------------------------------------------------------------------------
# Placeholder recognition + substitution
# ---------------------------------------------------------------------------


def test_find_placeholders_basic() -> None:
    """Finds every placeholder name in a template."""
    assert find_placeholders("Hi {{name}}, your claim is {{claim}}.") == {"name", "claim"}


def test_find_placeholders_ignores_whitespace_variants() -> None:
    """`{{ name }}` with spaces still matches."""
    assert find_placeholders("Hi {{ name }}") == {"name"}


def test_find_placeholders_skips_escaped() -> None:
    r"""``\{\{name\}\}`` is an escape, not a placeholder."""
    assert find_placeholders(r"Literal \{\{name\}\} here") == set()


def test_substitute_replaces_placeholders() -> None:
    """A single placeholder substitutes to ``str(value)``."""
    assert substitute("Hi {{name}}!", {"name": "Alice"}) == "Hi Alice!"


def test_substitute_stringifies_values() -> None:
    """Non-string values are stringified."""
    assert substitute("count={{n}}", {"n": 42}) == "count=42"


def test_substitute_handles_whitespace_inside_braces() -> None:
    """`{{ name }}` renders the same as ``{{name}}``."""
    assert substitute("Hi {{ name }}", {"name": "Alice"}) == "Hi Alice"


def test_substitute_replaces_every_occurrence() -> None:
    """Repeated placeholders are all replaced."""
    assert substitute("{{x}} and {{x}}", {"x": "A"}) == "A and A"


def test_substitute_missing_key_raises_keyerror() -> None:
    """A missing variable propagates a KeyError (callers wrap it)."""
    with pytest.raises(KeyError):
        substitute("Hi {{name}}", {})


# ---------------------------------------------------------------------------
# Escape contract
# ---------------------------------------------------------------------------


def test_escape_strips_backslashes() -> None:
    r"""``\{\{name\}\}`` renders as literal ``{{name}}`` with backslashes removed."""
    assert substitute(r"\{\{name\}\}", {"name": "Alice"}) == "{{name}}"


def test_escape_does_not_substitute_even_when_name_is_declared() -> None:
    r"""An escaped reference does not substitute even if the name is supplied."""
    assert substitute(r"\{\{name\}\}", {"name": "Alice"}) == "{{name}}"


def test_escape_and_real_placeholder_mixed() -> None:
    r"""One escaped and one real placeholder render correctly in the same string."""
    assert substitute(r"\{\{name\}\} is {{name}}", {"name": "Alice"}) == "{{name}} is Alice"

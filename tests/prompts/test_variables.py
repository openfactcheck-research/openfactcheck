"""Tests for VariableSpec and the ``.string`` factory."""

from __future__ import annotations

from openfactcheck.prompts import VariableSpec


def test_defaults_required_and_string() -> None:
    """Plain constructor defaults to a required string variable."""
    spec = VariableSpec(name="claim")

    assert spec.name == "claim"
    assert spec.type == "string"
    assert spec.required is True


def test_string_factory_defaults_required() -> None:
    """``VariableSpec.string('x')`` is equivalent to ``VariableSpec('x')``."""
    assert VariableSpec.string("claim") == VariableSpec(name="claim", type="string", required=True)


def test_string_factory_optional() -> None:
    """``VariableSpec.string('x', required=False)`` flips required off."""
    spec = VariableSpec.string("note", required=False)

    assert spec.required is False


def test_default_is_empty_string_unless_set() -> None:
    """A spec's default is an empty string when not specified."""
    assert VariableSpec.string("x").default == ""


def test_string_factory_threads_default() -> None:
    """The string factory carries a custom default through."""
    spec = VariableSpec.string("tone", required=False, default="neutral")

    assert spec.required is False
    assert spec.default == "neutral"


def test_variable_spec_is_frozen_and_hashable() -> None:
    """Immutable dataclass with slots — can't be mutated after construction, can be used as dict key."""
    spec = VariableSpec.string("claim")
    with __import__("pytest").raises((AttributeError, __import__("dataclasses").FrozenInstanceError)):
        spec.required = False  # type: ignore[misc]
    {spec: 1}  # hashable because frozen dataclass auto-generates __hash__.

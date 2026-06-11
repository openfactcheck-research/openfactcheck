"""Tests for the prompts error hierarchy + stdlib catch compatibility."""

from __future__ import annotations

from pathlib import Path

import pytest

from openfactcheck.prompts import (
    PromptError,
    PromptFormatError,
    PromptNotFoundError,
    PromptValidationError,
    PromptVariableError,
)


def test_format_error_inherits_value_error() -> None:
    """``PromptFormatError`` is catchable as ``ValueError``."""
    error = PromptFormatError(path=None, line=1, reason="bad")
    assert isinstance(error, ValueError)
    assert isinstance(error, PromptError)


def test_validation_error_inherits_value_error() -> None:
    """``PromptValidationError`` is catchable as ``ValueError``."""
    error = PromptValidationError(path=None, line=None, reason="bad")
    assert isinstance(error, ValueError)
    assert isinstance(error, PromptError)


def test_not_found_error_inherits_file_not_found() -> None:
    """``PromptNotFoundError`` is catchable as ``FileNotFoundError``."""
    error = PromptNotFoundError("verifier", (Path("/tmp/verifier.md"),))
    assert isinstance(error, FileNotFoundError)
    assert isinstance(error, PromptError)
    assert error.prompt_name == "verifier"


def test_variable_error_inherits_key_error() -> None:
    """``PromptVariableError`` is catchable as ``KeyError``."""
    error = PromptVariableError("sample", missing=("claim",))
    assert isinstance(error, KeyError)
    assert isinstance(error, PromptError)
    assert error.missing == ("claim",)


def test_base_prompt_error_catches_every_subclass() -> None:
    """Every subclass is catchable as ``PromptError``."""
    specifics: list[PromptError] = [
        PromptFormatError(path=None, line=None, reason="bad"),
        PromptValidationError(path=None, line=None, reason="bad"),
        PromptNotFoundError("x", ()),
        PromptVariableError("x", missing=("y",)),
    ]
    for exc in specifics:
        with pytest.raises(PromptError):
            raise exc


def test_format_error_message_shape() -> None:
    """Format-error message uses the pinned ``<path>:<line>: <reason>`` shape."""
    error = PromptFormatError(
        path=Path("/tmp/verifier.md"),
        line=14,
        reason="missing H1",
        expected="# System Prompt",
        got="## System Prompt",
    )
    msg = str(error)
    assert "/tmp/verifier.md:14: missing H1" in msg
    assert "expected: # System Prompt" in msg
    assert "got:      ## System Prompt" in msg


def test_inline_location_when_no_path() -> None:
    """Without a path, the error header uses the inline location marker."""
    error = PromptValidationError(path=None, line=None, reason="bad")
    assert str(error).startswith("(python): bad")

"""Tests for the filled Prompt value."""

from __future__ import annotations

import pytest

from openfactcheck.messages import SystemMessage, UserMessage
from openfactcheck.prompts import Prompt


def test_Prompt_to_messages_returns_list_copy() -> None:
    """to_messages returns the stored messages as a fresh list."""
    messages = (SystemMessage(content="S"), UserMessage(content="U"))
    prompt = Prompt(name="t", messages=messages)

    result = prompt.to_messages()

    assert result == list(messages)
    assert isinstance(result, list)


def test_Prompt_to_string_is_role_labeled() -> None:
    """to_string renders '<role>: <content>' joined by blank lines."""
    prompt = Prompt(name="t", messages=(SystemMessage(content="S"), UserMessage(content="U")))

    assert prompt.to_string() == "system: S\n\nuser: U"


def test_Prompt_variables_used_is_a_frozen_copy() -> None:
    """variables_used is an immutable copy; mutating the source dict does not leak."""
    source = {"x": "1"}
    prompt = Prompt(name="t", messages=(UserMessage(content="U"),), variables_used=source)
    source["x"] = "mutated"

    assert dict(prompt.variables_used) == {"x": "1"}
    with pytest.raises(TypeError):
        prompt.variables_used["x"] = "no"  # type: ignore[index]

"""Tests for LLM message types."""

import pytest
from pydantic import ValidationError

from openfactcheck.messages import (
    AssistantMessage,
    SystemMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)


def test_SystemMessage_defaults() -> None:
    """SystemMessage sets role automatically."""
    msg = SystemMessage(content="You are helpful.")

    assert msg.role == "system"
    assert msg.content == "You are helpful."


def test_UserMessage_defaults() -> None:
    """UserMessage sets role automatically."""
    msg = UserMessage(content="Hello.")

    assert msg.role == "user"


def test_AssistantMessage_defaults() -> None:
    """AssistantMessage sets role and tool_calls defaults."""
    msg = AssistantMessage(content="Hi there.")

    assert msg.role == "assistant"
    assert msg.tool_calls is None


def test_AssistantMessage_with_tool_calls() -> None:
    """AssistantMessage accepts tool_calls."""
    tc = ToolCall(id="tc_1", name="search", arguments='{"q": "test"}')

    msg = AssistantMessage(content="", tool_calls=[tc])

    assert msg.tool_calls is not None
    assert len(msg.tool_calls) == 1
    assert msg.tool_calls[0].name == "search"


def test_ToolMessage_requires_tool_call_id() -> None:
    """ToolMessage requires tool_call_id."""
    msg = ToolMessage(content="result", tool_call_id="tc_1")

    assert msg.role == "tool"
    assert msg.tool_call_id == "tc_1"


def test_ToolMessage_missing_tool_call_id() -> None:
    """ToolMessage without tool_call_id raises ValidationError."""
    with pytest.raises(ValidationError):
        ToolMessage(content="result")  # type: ignore[call-arg]


def test_message_forbids_extra_fields() -> None:
    """Extra fields are rejected on all message types."""
    with pytest.raises(ValidationError, match="extra"):
        SystemMessage(content="hi", unexpected="field")  # type: ignore[call-arg]


def test_ToolCall_forbids_extra_fields() -> None:
    """Extra fields are rejected on ToolCall."""
    with pytest.raises(ValidationError, match="extra"):
        ToolCall(id="1", name="f", arguments="{}", extra="bad")  # type: ignore[call-arg]


def test_message_serialization_round_trip() -> None:
    """Messages serialize to dict and back."""
    msg = AssistantMessage(
        content="hello",
        tool_calls=[ToolCall(id="1", name="f", arguments="{}")],
    )

    data = msg.model_dump()
    restored = AssistantMessage.model_validate(data)

    assert restored == msg

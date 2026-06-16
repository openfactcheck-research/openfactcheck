"""Tests for LLM response types."""

import pytest
from pydantic import TypeAdapter, ValidationError

from openfactcheck.messages import AssistantMessage
from openfactcheck.chat.responses import ChatResponse, FinishReason, StreamEnd, StreamEvent, TextDelta, Usage


def test_Usage_frozen() -> None:
    """Usage is immutable."""
    usage = Usage(input_tokens=10, output_tokens=5)

    with pytest.raises(ValidationError):
        usage.input_tokens = 99  # type: ignore[misc] - frozen rejects mutation.


def test_FinishReason_values() -> None:
    """FinishReason contains expected values."""
    assert FinishReason.STOP == "stop"
    assert FinishReason.TOOL_CALLS == "tool_calls"
    assert FinishReason.LENGTH == "length"
    assert FinishReason.CONTENT_FILTER == "content_filter"
    assert FinishReason.ERROR == "error"


def test_ChatResponse_minimal() -> None:
    """ChatResponse with required fields only."""
    msg = AssistantMessage(content="hello")

    response = ChatResponse(message=msg, model="gpt-4o", provider="openai")

    assert response.message.content == "hello"
    assert response.model == "gpt-4o"
    assert response.provider == "openai"
    assert response.usage is None
    assert response.finish_reason is None


def test_ChatResponse_full() -> None:
    """ChatResponse with all fields."""
    msg = AssistantMessage(content="hi")
    usage = Usage(input_tokens=10, output_tokens=5)

    response = ChatResponse(
        message=msg,
        model="gpt-4o",
        provider="openai",
        usage=usage,
        finish_reason=FinishReason.STOP,
    )

    assert response.usage is not None
    assert response.usage.input_tokens == 10
    assert response.finish_reason == FinishReason.STOP


def test_ChatResponse_frozen() -> None:
    """ChatResponse is immutable."""
    msg = AssistantMessage(content="hi")
    response = ChatResponse(message=msg, model="gpt-4o", provider="openai")

    with pytest.raises(ValidationError):
        response.model = "other"  # type: ignore[misc] - frozen rejects mutation.


def test_ChatResponse_forbids_extra() -> None:
    """ChatResponse rejects extra fields."""
    msg = AssistantMessage(content="hi")

    with pytest.raises(ValidationError, match="extra"):
        ChatResponse(message=msg, model="gpt-4o", provider="openai", extra="bad")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Stream events
# ---------------------------------------------------------------------------


def test_TextDelta_defaults() -> None:
    """TextDelta sets type automatically."""
    event = TextDelta(content="hello")

    assert event.type == "text"
    assert event.content == "hello"


def test_StreamEnd_defaults() -> None:
    """StreamEnd sets type automatically and allows empty finish."""
    event = StreamEnd()

    assert event.type == "end"
    assert event.finish_reason is None
    assert event.usage is None


def test_StreamEnd_with_usage() -> None:
    """StreamEnd carries usage and finish_reason."""
    event = StreamEnd(
        finish_reason=FinishReason.STOP,
        usage=Usage(input_tokens=10, output_tokens=5),
    )

    assert event.finish_reason == FinishReason.STOP
    assert event.usage is not None
    assert event.usage.output_tokens == 5


def test_StreamEvent_discriminated_union_text() -> None:
    """StreamEvent parses TextDelta from raw dict by type field."""
    adapter = TypeAdapter(StreamEvent)

    event = adapter.validate_python({"type": "text", "content": "hello"})

    assert isinstance(event, TextDelta)


def test_StreamEvent_discriminated_union_end() -> None:
    """StreamEvent parses StreamEnd from raw dict by type field."""
    adapter = TypeAdapter(StreamEvent)

    event = adapter.validate_python({"type": "end", "finish_reason": "stop"})

    assert isinstance(event, StreamEnd)
    assert event.finish_reason == FinishReason.STOP


def test_StreamEvent_rejects_unknown_type() -> None:
    """StreamEvent rejects an unknown discriminator value."""
    adapter = TypeAdapter(StreamEvent)

    with pytest.raises(ValidationError):
        adapter.validate_python({"type": "unknown", "content": "x"})


def test_TextDelta_forbids_extra() -> None:
    """TextDelta rejects extra fields."""
    with pytest.raises(ValidationError, match="extra"):
        TextDelta(content="hi", bad="x")  # type: ignore[call-arg]


def test_TextDelta_frozen() -> None:
    """TextDelta is immutable."""
    event = TextDelta(content="hi")

    with pytest.raises(ValidationError):
        event.content = "other"  # type: ignore[misc] - frozen.

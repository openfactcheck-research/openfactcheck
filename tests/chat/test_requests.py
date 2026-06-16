"""Tests for ChatRequest."""

import pytest
from pydantic import ValidationError

from openfactcheck.chat.config import OpenAIConfig, RuntimeConfig
from openfactcheck.messages import UserMessage
from openfactcheck.chat.requests import ChatRequest


def test_ChatRequest_minimal() -> None:
    """ChatRequest requires messages and config, defaults runtime."""
    request = ChatRequest(
        messages=[UserMessage(content="Hi")],
        config=OpenAIConfig(model="gpt-4o"),
    )

    assert len(request.messages) == 1
    assert request.config.model == "gpt-4o"
    assert isinstance(request.runtime, RuntimeConfig)
    assert request.runtime.max_retries == 2


def test_ChatRequest_custom_runtime() -> None:
    """ChatRequest accepts a custom runtime."""
    runtime = RuntimeConfig(timeout=15.0, max_retries=5)

    request = ChatRequest(
        messages=[UserMessage(content="Hi")],
        config=OpenAIConfig(model="gpt-4o"),
        runtime=runtime,
    )

    assert request.runtime is runtime


def test_ChatRequest_frozen() -> None:
    """ChatRequest is immutable."""
    request = ChatRequest(
        messages=[UserMessage(content="Hi")],
        config=OpenAIConfig(model="gpt-4o"),
    )

    with pytest.raises(ValidationError):
        request.messages = []  # type: ignore[misc] - frozen rejects mutation.


def test_ChatRequest_forbids_extra() -> None:
    """ChatRequest rejects extra fields."""
    with pytest.raises(ValidationError, match="extra"):
        ChatRequest(
            messages=[UserMessage(content="Hi")],
            config=OpenAIConfig(model="gpt-4o"),
            unknown="bad",  # type: ignore[call-arg]
        )

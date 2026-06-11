"""Tests for Anthropic backend normalization."""

from types import SimpleNamespace

import pytest

from openfactcheck.chat.backends.anthropic.normalize import (
    map_error,
    to_anthropic_messages,
    to_chat_response,
)
from openfactcheck.chat.errors import (
    AuthenticationError,
    ProviderError,
    RateLimitError,
    UnsupportedFeatureError,
)
from openfactcheck.chat.messages import AssistantMessage, SystemMessage, ToolMessage, UserMessage
from openfactcheck.chat.responses import FinishReason


def test_to_anthropic_messages_extracts_system() -> None:
    """SystemMessage is pulled out of the list and returned separately."""
    messages = [
        SystemMessage(content="sys"),
        UserMessage(content="hi"),
        AssistantMessage(content="hello"),
    ]

    system, result = to_anthropic_messages(messages)

    assert system == "sys"
    assert result == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]


def test_to_anthropic_messages_without_system() -> None:
    """No SystemMessage means system=None."""
    messages = [UserMessage(content="hi")]

    system, result = to_anthropic_messages(messages)

    assert system is None
    assert result == [{"role": "user", "content": "hi"}]


def test_to_anthropic_messages_rejects_multiple_systems() -> None:
    """Anthropic allows only one system prompt."""
    messages = [
        SystemMessage(content="first"),
        SystemMessage(content="second"),
        UserMessage(content="hi"),
    ]

    with pytest.raises(UnsupportedFeatureError, match="single system message"):
        to_anthropic_messages(messages)


def test_to_anthropic_messages_rejects_tool_messages() -> None:
    """Tool messages are not yet supported in the Anthropic backend."""
    messages = [
        UserMessage(content="hi"),
        ToolMessage(content="result", tool_call_id="tc_1"),
    ]

    with pytest.raises(UnsupportedFeatureError, match="tool messages"):
        to_anthropic_messages(messages)


def test_to_chat_response_basic() -> None:
    """A minimal Anthropic Message maps to ChatResponse."""
    response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="Hello!")],
        usage=SimpleNamespace(input_tokens=10, output_tokens=3),
        stop_reason="end_turn",
    )

    result = to_chat_response(response, model="claude-sonnet-4-6", provider="anthropic")

    assert result.message.content == "Hello!"
    assert result.model == "claude-sonnet-4-6"
    assert result.provider == "anthropic"
    assert result.finish_reason == FinishReason.STOP
    assert result.usage is not None
    assert result.usage.input_tokens == 10
    assert result.usage.output_tokens == 3


def test_to_chat_response_concatenates_text_blocks() -> None:
    """Multiple text blocks are joined; non-text blocks are skipped."""
    response = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="Part one. "),
            SimpleNamespace(type="thinking", thinking="ignored"),
            SimpleNamespace(type="text", text="Part two."),
        ],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        stop_reason="end_turn",
    )

    result = to_chat_response(response, model="claude-sonnet-4-6", provider="anthropic")

    assert result.message.content == "Part one. Part two."


def test_to_chat_response_tool_use_becomes_json() -> None:
    """A forced-tool reply JSON-encodes the tool input into the message content."""
    response = SimpleNamespace(
        content=[SimpleNamespace(type="tool_use", id="tu_1", name="Person", input={"name": "Ada", "age": 36})],
        usage=SimpleNamespace(input_tokens=10, output_tokens=3),
        stop_reason="tool_use",
    )

    result = to_chat_response(response, model="claude-sonnet-4-6", provider="anthropic")

    assert result.message.content == '{"name": "Ada", "age": 36}'


def test_to_chat_response_rejects_blocks_without_text_or_tool_use() -> None:
    """A response with neither text nor tool_use blocks raises UnsupportedFeatureError."""
    response = SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking="...")],
        usage=SimpleNamespace(input_tokens=10, output_tokens=3),
        stop_reason="end_turn",
    )

    with pytest.raises(UnsupportedFeatureError, match="no text or tool_use blocks"):
        to_chat_response(response, model="claude-sonnet-4-6", provider="anthropic")


def test_to_chat_response_max_tokens_maps_to_length() -> None:
    """Anthropic 'max_tokens' stop reason maps to FinishReason.LENGTH."""
    response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="truncated")],
        usage=SimpleNamespace(input_tokens=5, output_tokens=50),
        stop_reason="max_tokens",
    )

    result = to_chat_response(response, model="claude-sonnet-4-6", provider="anthropic")

    assert result.finish_reason == FinishReason.LENGTH


def _build_response(status_code: int) -> object:
    """Minimal httpx.Response-like object for constructing Anthropic SDK errors."""
    import httpx  # noqa: PLC0415

    return httpx.Response(status_code=status_code, request=httpx.Request("POST", "https://api.anthropic.com"))


def test_map_error_authentication() -> None:
    """Anthropic auth errors map to AuthenticationError."""
    from anthropic import AuthenticationError as AnthropicAuth

    err = AnthropicAuth(message="bad key", response=_build_response(401), body=None)

    mapped = map_error(err)

    assert isinstance(mapped, AuthenticationError)


def test_map_error_rate_limit() -> None:
    """Anthropic rate limit errors map to RateLimitError."""
    from anthropic import RateLimitError as AnthropicRateLimit

    err = AnthropicRateLimit(message="slow down", response=_build_response(429), body=None)

    mapped = map_error(err)

    assert isinstance(mapped, RateLimitError)


def test_map_error_not_found_maps_to_provider_error() -> None:
    """Anthropic not-found errors map to ProviderError (not ProviderNotFoundError)."""
    from anthropic import NotFoundError as AnthropicNotFound

    err = AnthropicNotFound(message="no such model", response=_build_response(404), body=None)

    mapped = map_error(err)

    assert isinstance(mapped, ProviderError)


def test_map_error_generic_falls_through_to_provider_error() -> None:
    """An unrecognized exception maps to ProviderError."""
    mapped = map_error(RuntimeError("boom"))

    assert isinstance(mapped, ProviderError)

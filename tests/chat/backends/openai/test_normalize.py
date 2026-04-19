"""Tests for OpenAI backend normalization."""

from types import SimpleNamespace

from openfactcheck.chat.backends.openai.normalize import (
    map_error,
    to_chat_response,
    to_openai_messages,
)
from openfactcheck.chat.errors import (
    AuthenticationError,
    ProviderError,
    RateLimitError,
)
from openfactcheck.chat.messages import AssistantMessage, SystemMessage, ToolMessage, UserMessage
from openfactcheck.chat.responses import FinishReason


def test_to_openai_messages_converts_all_types() -> None:
    """All our message types map to OpenAI-style dicts."""
    messages = [
        SystemMessage(content="sys"),
        UserMessage(content="hi"),
        AssistantMessage(content="hello"),
        ToolMessage(content="result", tool_call_id="tc_1"),
    ]

    result = to_openai_messages(messages)

    assert result == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "tool", "content": "result", "tool_call_id": "tc_1"},
    ]


def test_to_chat_response_basic() -> None:
    """A minimal ChatCompletion-shaped response maps to ChatResponse."""
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="Hello!", tool_calls=None),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=3),
    )

    result = to_chat_response(response, model="gpt-4o", provider="openai")

    assert result.message.content == "Hello!"
    assert result.model == "gpt-4o"
    assert result.provider == "openai"
    assert result.finish_reason == FinishReason.STOP
    assert result.usage is not None
    assert result.usage.input_tokens == 10
    assert result.usage.output_tokens == 3


def _build_response(status_code: int) -> object:
    """Minimal httpx.Response-like object for constructing OpenAI SDK errors."""
    import httpx  # noqa: PLC0415

    return httpx.Response(status_code=status_code, request=httpx.Request("POST", "https://api.openai.com"))


def test_map_error_authentication() -> None:
    """OpenAI auth errors map to AuthenticationError."""
    from openai import AuthenticationError as OpenAIAuth

    err = OpenAIAuth(message="bad key", response=_build_response(401), body=None)

    mapped = map_error(err)

    assert isinstance(mapped, AuthenticationError)


def test_map_error_rate_limit() -> None:
    """OpenAI rate limit errors map to RateLimitError."""
    from openai import RateLimitError as OpenAIRateLimit

    err = OpenAIRateLimit(message="slow down", response=_build_response(429), body=None)

    mapped = map_error(err)

    assert isinstance(mapped, RateLimitError)


def test_map_error_not_found() -> None:
    """OpenAI not-found errors map to ProviderError (not ProviderNotFoundError, which is for our registry)."""
    from openai import NotFoundError as OpenAINotFound

    err = OpenAINotFound(message="no such model", response=_build_response(404), body=None)

    mapped = map_error(err)

    assert isinstance(mapped, ProviderError)


def test_map_error_generic_falls_through_to_provider_error() -> None:
    """An unrecognized exception maps to ProviderError."""
    mapped = map_error(RuntimeError("boom"))

    assert isinstance(mapped, ProviderError)

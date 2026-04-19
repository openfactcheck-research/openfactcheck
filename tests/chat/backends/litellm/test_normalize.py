"""Tests for litellm normalization — our types ↔ litellm types."""

from types import SimpleNamespace

from openfactcheck.chat.backends.litellm.normalize import (
    map_error,
    to_chat_response,
    to_openai_messages,
)
from openfactcheck.chat.errors import (
    AuthenticationError,
    ProviderError,
    ProviderNotFoundError,
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
    """A minimal litellm-shaped response maps to ChatResponse."""
    litellm_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="Hello!", tool_calls=None),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=3),
    )

    response = to_chat_response(litellm_response, model="gpt-4o", provider="openai")

    assert response.message.content == "Hello!"
    assert response.model == "gpt-4o"
    assert response.provider == "openai"
    assert response.finish_reason == FinishReason.STOP
    assert response.usage is not None
    assert response.usage.input_tokens == 10
    assert response.usage.output_tokens == 3


def test_map_error_authentication() -> None:
    """litellm auth errors map to AuthenticationError."""
    from litellm.exceptions import AuthenticationError as LitellmAuth  # noqa: PLC0415

    err = LitellmAuth(message="bad key", llm_provider="openai", model="gpt-4o")

    mapped = map_error(err)

    assert isinstance(mapped, AuthenticationError)


def test_map_error_rate_limit() -> None:
    """litellm rate limit errors map to RateLimitError."""
    from litellm.exceptions import RateLimitError as LitellmRateLimit  # noqa: PLC0415

    err = LitellmRateLimit(message="slow down", llm_provider="openai", model="gpt-4o")

    mapped = map_error(err)

    assert isinstance(mapped, RateLimitError)


def test_map_error_bad_request_is_provider_not_found() -> None:
    """litellm bad-request errors (bad model, etc.) map to ProviderNotFoundError."""
    from litellm.exceptions import BadRequestError as LitellmBadRequest  # noqa: PLC0415

    err = LitellmBadRequest(message="unknown model", model="fake", llm_provider="openai")

    mapped = map_error(err)

    assert isinstance(mapped, ProviderNotFoundError)


def test_map_error_generic_falls_through_to_provider_error() -> None:
    """An unrecognized exception maps to ProviderError."""
    mapped = map_error(RuntimeError("boom"))

    assert isinstance(mapped, ProviderError)

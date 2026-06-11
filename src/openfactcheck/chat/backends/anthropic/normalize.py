"""Translate between our types and the ``anthropic`` SDK types.

This module and ``openfactcheck.chat.backends.anthropic.backend`` are the
only places in this package that touch ``anthropic`` SDK types directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from openfactcheck.chat.errors import (
    AuthenticationError,
    ProviderError,
    RateLimitError,
    UnsupportedFeatureError,
)
from openfactcheck.chat.messages import AssistantMessage, SystemMessage, UserMessage
from openfactcheck.chat.responses import ChatResponse, FinishReason, StreamEnd, Usage

if TYPE_CHECKING:
    from anthropic.types import Message as AnthropicMessage

    from openfactcheck.chat.config import ProviderName
    from openfactcheck.chat.errors import ChatModelError
    from openfactcheck.chat.messages import Message


class AnthropicInputMessage(TypedDict):
    """Anthropic-style input message matching what ``messages.create`` expects."""

    role: str
    content: str


def to_anthropic_messages(messages: list[Message]) -> tuple[str | None, list[AnthropicInputMessage]]:
    """Convert our messages to Anthropic-style dicts. System prompt is returned separately.

    Anthropic's API takes the system prompt as a top-level ``system=`` param,
    not inside the messages list. Exactly one SystemMessage is allowed.
    """
    system: str | None = None
    result: list[AnthropicInputMessage] = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            if system is not None:
                raise UnsupportedFeatureError(
                    "Anthropic supports a single system message; multiple SystemMessages were provided."
                )
            system = msg.content
        elif isinstance(msg, UserMessage):
            result.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AssistantMessage):
            # Tool-call conversion deferred until tool calling is implemented.
            result.append({"role": "assistant", "content": msg.content})
        else:  # ToolMessage.
            raise UnsupportedFeatureError("Anthropic backend does not yet support tool messages.")
    return system, result


def to_chat_response(
    response: AnthropicMessage,
    model: str,
    provider: ProviderName,
) -> ChatResponse:
    """Convert an Anthropic ``Message`` to our ChatResponse."""
    text_parts = [block.text for block in response.content if block.type == "text"]
    if not text_parts:
        raise UnsupportedFeatureError(
            "Anthropic response contained no text blocks (only thinking/tool_use). "
            "Non-text content is not yet supported."
        )
    content = "".join(text_parts)

    usage = Usage(
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
    finish_reason = _to_finish_reason(response.stop_reason)

    return ChatResponse(
        message=AssistantMessage(content=content, tool_calls=None),
        model=model,
        provider=provider,
        usage=usage,
        finish_reason=finish_reason,
    )


def to_stream_end(stop_reason: str | None, input_tokens: int, output_tokens: int) -> StreamEnd:
    """Build the terminal StreamEnd event from accumulated stream state."""
    usage: Usage | None = None
    if input_tokens or output_tokens:
        usage = Usage(input_tokens=input_tokens, output_tokens=output_tokens)
    return StreamEnd(finish_reason=_to_finish_reason(stop_reason), usage=usage)


_STOP_REASON_TO_FINISH: dict[str, FinishReason] = {
    "end_turn": FinishReason.STOP,
    "stop_sequence": FinishReason.STOP,
    "max_tokens": FinishReason.LENGTH,
    "tool_use": FinishReason.TOOL_CALLS,
    "refusal": FinishReason.CONTENT_FILTER,
}


def _to_finish_reason(raw: str | None) -> FinishReason | None:
    """Convert a raw Anthropic stop_reason string to our enum, if recognized."""
    if raw is None:
        return None
    return _STOP_REASON_TO_FINISH.get(raw)


def map_error(exc: Exception) -> ChatModelError:
    """Convert an Anthropic SDK exception to our error hierarchy."""
    from anthropic import APIConnectionError, APIError, APIStatusError
    from anthropic import AuthenticationError as AnthropicAuthError
    from anthropic import NotFoundError as AnthropicNotFoundError
    from anthropic import RateLimitError as AnthropicRateLimitError

    msg = str(exc)
    if isinstance(exc, AnthropicAuthError):
        return AuthenticationError(f"Authentication failed. Set the ANTHROPIC_API_KEY environment variable. ({msg})")
    if isinstance(exc, AnthropicRateLimitError):
        return RateLimitError(f"Rate limit exceeded. ({msg})")
    if isinstance(exc, AnthropicNotFoundError):
        # Upstream 404 (model/resource missing). Keep as ProviderError;
        # ProviderNotFoundError is reserved for our own provider-lookup layer.
        return ProviderError(f"Model not found. ({msg})")
    if isinstance(exc, (APIConnectionError, APIError, APIStatusError)):
        return ProviderError(f"API error. ({msg})")
    return ProviderError(msg)

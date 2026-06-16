"""Translate between our types and the ``openai`` SDK types.

This module and ``openfactcheck.chat.backends.openai.backend`` are the
only places in this package that touch ``openai`` SDK types directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Required, TypedDict

from openfactcheck.chat.errors import (
    AuthenticationError,
    ProviderError,
    RateLimitError,
)
from openfactcheck.chat.responses import ChatResponse, FinishReason, StreamEnd, Usage
from openfactcheck.messages import AssistantMessage, SystemMessage, ToolCall, UserMessage

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletion, ChatCompletionChunk

    from openfactcheck.chat.config import ProviderName
    from openfactcheck.chat.errors import ChatModelError
    from openfactcheck.messages import Message


class OpenAIMessage(TypedDict, total=False):
    """OpenAI-style message dict matching what ``chat.completions.create`` expects."""

    role: Required[str]
    content: Required[str]
    tool_call_id: str


def to_openai_messages(messages: list[Message]) -> list[OpenAIMessage]:
    """Convert our messages to OpenAI-style dicts."""
    result: list[OpenAIMessage] = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            result.append({"role": "system", "content": msg.content})
        elif isinstance(msg, UserMessage):
            result.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AssistantMessage):
            entry: OpenAIMessage = {"role": "assistant", "content": msg.content}
            # Tool call conversion deferred until tool calling is implemented.
            result.append(entry)
        else:  # ToolMessage.
            result.append({"role": "tool", "content": msg.content, "tool_call_id": msg.tool_call_id})
    return result


def to_chat_response(
    response: ChatCompletion,
    model: str,
    provider: ProviderName,
) -> ChatResponse:
    """Convert an OpenAI ``ChatCompletion`` to our ChatResponse."""
    choice = response.choices[0]
    message = choice.message

    tool_calls: list[ToolCall] | None = None
    if message.tool_calls:
        tool_calls = [
            ToolCall(id=tc.id, name=tc.function.name, arguments=tc.function.arguments) for tc in message.tool_calls
        ]

    usage: Usage | None = None
    if response.usage is not None:
        usage = Usage(
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )

    finish_reason = _to_finish_reason(choice.finish_reason)

    return ChatResponse(
        message=AssistantMessage(content=message.content or "", tool_calls=tool_calls),
        model=model,
        provider=provider,
        usage=usage,
        finish_reason=finish_reason,
    )


def to_stream_end(last_chunk: ChatCompletionChunk | None, accumulated_usage: object) -> StreamEnd:
    """Build the terminal StreamEnd event from the final OpenAI chunk."""
    finish_reason: FinishReason | None = None
    if last_chunk is not None and last_chunk.choices:
        finish_reason = _to_finish_reason(last_chunk.choices[0].finish_reason)

    usage: Usage | None = None
    if accumulated_usage is not None:
        usage = Usage(
            input_tokens=getattr(accumulated_usage, "prompt_tokens", 0),
            output_tokens=getattr(accumulated_usage, "completion_tokens", 0),
        )
    return StreamEnd(finish_reason=finish_reason, usage=usage)


_FINISH_REASON_BY_OPENAI: dict[str, FinishReason] = {
    "stop": FinishReason.STOP,
    "length": FinishReason.LENGTH,
    "tool_calls": FinishReason.TOOL_CALLS,
    "content_filter": FinishReason.CONTENT_FILTER,
}


def _to_finish_reason(raw: str | None) -> FinishReason | None:
    """Convert a raw OpenAI finish_reason string to our enum, if recognized."""
    if raw is None:
        return None
    return _FINISH_REASON_BY_OPENAI.get(raw)


def map_error(exc: Exception) -> ChatModelError:
    """Convert an OpenAI SDK exception to our error hierarchy."""
    from openai import APIConnectionError, APIError
    from openai import AuthenticationError as OpenAIAuthError
    from openai import NotFoundError as OpenAINotFoundError
    from openai import RateLimitError as OpenAIRateLimitError

    msg = str(exc)
    if isinstance(exc, OpenAIAuthError):
        return AuthenticationError(f"Authentication failed; check your API key. ({msg})")
    if isinstance(exc, OpenAINotFoundError):
        # Upstream 404 (model/resource missing). Keep as ProviderError;
        # ProviderNotFoundError is reserved for our own provider-lookup layer.
        return ProviderError(f"Model not found. ({msg})")
    if isinstance(exc, OpenAIRateLimitError):
        return RateLimitError(f"Rate limit exceeded. ({msg})")
    if isinstance(exc, (APIConnectionError, APIError)):
        return ProviderError(f"API error. ({msg})")
    return ProviderError(msg)

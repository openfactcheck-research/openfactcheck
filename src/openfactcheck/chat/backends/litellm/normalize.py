"""Translate between our message/response types and litellm's OpenAI-shaped dicts.

This module and ``openfactcheck.chat.backends.litellm.backend`` are the
only places in this package that touch litellm types directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Required, TypedDict

from openfactcheck.chat.errors import (
    AuthenticationError,
    ProviderError,
    ProviderNotFoundError,
    RateLimitError,
)
from openfactcheck.chat.messages import AssistantMessage, SystemMessage, ToolCall, UserMessage
from openfactcheck.chat.responses import ChatResponse, FinishReason, StreamEnd, Usage

if TYPE_CHECKING:
    from litellm.types.utils import ModelResponse, ModelResponseStream

    from openfactcheck.chat.config import ProviderName
    from openfactcheck.chat.errors import ChatModelError
    from openfactcheck.chat.messages import Message


class OpenAIMessage(TypedDict, total=False):
    """OpenAI-style message dict matching what litellm's ``completion`` expects."""

    role: Required[str]
    content: Required[str]
    tool_call_id: str


def to_openai_messages(messages: list[Message]) -> list[OpenAIMessage]:
    """Convert our messages to OpenAI-style dicts (what litellm expects)."""
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
    response: ModelResponse,
    model: str,
    provider: ProviderName,
) -> ChatResponse:
    """Convert a litellm ``ModelResponse`` to our ChatResponse."""
    choice = response.choices[0]
    message = choice.message

    tool_calls: list[ToolCall] | None = None
    raw_tool_calls = getattr(message, "tool_calls", None)
    if raw_tool_calls:
        tool_calls = [
            ToolCall(
                id=tc.id,
                name=tc.function.name or "",
                arguments=tc.function.arguments,
            )
            for tc in raw_tool_calls
        ]

    usage = _to_usage(getattr(response, "usage", None))
    finish_reason = _to_finish_reason(getattr(choice, "finish_reason", None))

    return ChatResponse(
        message=AssistantMessage(content=message.content or "", tool_calls=tool_calls),
        model=model,
        provider=provider,
        usage=usage,
        finish_reason=finish_reason,
    )


def to_stream_end(last_chunk: ModelResponseStream | None, accumulated_usage: object) -> StreamEnd:
    """Build the terminal StreamEnd event from the final litellm chunk."""
    finish_reason: FinishReason | None = None
    if last_chunk is not None and last_chunk.choices:
        finish_reason = _to_finish_reason(getattr(last_chunk.choices[0], "finish_reason", None))
    return StreamEnd(finish_reason=finish_reason, usage=_to_usage(accumulated_usage))


def _to_usage(raw: object) -> Usage | None:
    """Extract token counts from a litellm usage object, if present."""
    if raw is None:
        return None
    return Usage(
        input_tokens=getattr(raw, "prompt_tokens", 0),
        output_tokens=getattr(raw, "completion_tokens", 0),
    )


def _to_finish_reason(raw: object) -> FinishReason | None:
    """Convert a raw litellm finish_reason string to our enum, if recognized."""
    if raw in FinishReason.__members__.values():
        return FinishReason(raw)
    return None


def map_error(exc: Exception) -> ChatModelError:
    """Convert a litellm exception to our error hierarchy."""
    from litellm.exceptions import (
        AuthenticationError as LitellmAuthError,
    )
    from litellm.exceptions import (
        BadRequestError as LitellmBadRequestError,
    )
    from litellm.exceptions import (
        NotFoundError as LitellmNotFoundError,
    )
    from litellm.exceptions import (
        RateLimitError as LitellmRateLimitError,
    )

    msg = str(exc)
    if isinstance(exc, LitellmAuthError):
        return AuthenticationError(f"Authentication failed. Set the appropriate API key. ({msg})")
    if isinstance(exc, (LitellmNotFoundError, LitellmBadRequestError)):
        return ProviderNotFoundError(f"Model or provider not recognized. ({msg})")
    if isinstance(exc, LitellmRateLimitError):
        return RateLimitError(f"Rate limit exceeded. ({msg})")
    return ProviderError(msg)

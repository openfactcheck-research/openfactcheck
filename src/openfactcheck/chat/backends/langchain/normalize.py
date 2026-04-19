"""Translate between our message/response types and LangChain's.

This module and ``openfactcheck.chat.backends.langchain.imports`` are the
only places in the backend that touch LangChain types directly.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from openfactcheck.chat.messages import AssistantMessage, SystemMessage, ToolCall, UserMessage
from openfactcheck.chat.responses import ChatResponse, FinishReason, StreamEnd, Usage

if TYPE_CHECKING:
    from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage

    from openfactcheck.chat.config import ProviderName
    from openfactcheck.chat.messages import Message


def to_langchain_messages(messages: list[Message]) -> list[BaseMessage]:
    """Convert our messages to langchain message types."""
    from langchain_core.messages import AIMessage, HumanMessage
    from langchain_core.messages import SystemMessage as LCSystemMessage
    from langchain_core.messages import ToolMessage as LCToolMessage

    result: list[BaseMessage] = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            result.append(LCSystemMessage(content=msg.content))
        elif isinstance(msg, UserMessage):
            result.append(HumanMessage(content=msg.content))
        elif isinstance(msg, AssistantMessage):
            lc_msg = AIMessage(content=msg.content)
            # Tool call conversion deferred until tool calling is implemented.
            result.append(lc_msg)
        else:  # ToolMessage.
            result.append(LCToolMessage(content=msg.content, tool_call_id=msg.tool_call_id))
    return result


def to_chat_response(
    result: AIMessage,
    model: str,
    provider: ProviderName,
) -> ChatResponse:
    """Convert a langchain AIMessage to our ChatResponse."""
    tool_calls: list[ToolCall] | None = None
    if result.tool_calls:
        tool_calls = [
            ToolCall(
                id=tc["id"] or "",
                name=tc["name"],
                arguments=json.dumps(tc.get("args", {})),
            )
            for tc in result.tool_calls
        ]

    usage: Usage | None = None
    if hasattr(result, "usage_metadata") and result.usage_metadata:
        meta = result.usage_metadata
        usage = Usage(
            input_tokens=meta.get("input_tokens", 0),
            output_tokens=meta.get("output_tokens", 0),
        )

    finish_reason: FinishReason | None = None
    if hasattr(result, "response_metadata"):
        raw_reason = result.response_metadata.get("finish_reason")
        if raw_reason in FinishReason.__members__.values():
            finish_reason = FinishReason(raw_reason)

    content = result.content if isinstance(result.content, str) else ""
    return ChatResponse(
        message=AssistantMessage(content=content, tool_calls=tool_calls),
        model=model,
        provider=provider,
        usage=usage,
        finish_reason=finish_reason,
    )


def to_stream_end(chunk: AIMessageChunk | None) -> StreamEnd:
    """Build the terminal StreamEnd event from the final langchain chunk."""
    if chunk is None:
        return StreamEnd()

    finish_reason: FinishReason | None = None
    raw_reason = chunk.response_metadata.get("finish_reason")
    if raw_reason in FinishReason.__members__.values():
        finish_reason = FinishReason(raw_reason)

    usage: Usage | None = None
    if chunk.usage_metadata:
        usage = Usage(
            input_tokens=chunk.usage_metadata.get("input_tokens", 0),
            output_tokens=chunk.usage_metadata.get("output_tokens", 0),
        )

    return StreamEnd(finish_reason=finish_reason, usage=usage)

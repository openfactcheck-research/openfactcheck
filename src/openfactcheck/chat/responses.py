"""Response types for the chat layer.

Non-streaming calls ([`ChatClient.completion`][ChatClient.completion] and
[`ChatClient.acompletion`][ChatClient.acompletion]) return a
[`ChatResponse`][ChatResponse]. Streaming calls
([`ChatClient.stream`][ChatClient.stream] and
[`ChatClient.astream`][ChatClient.astream]) yield a sequence of
[`StreamEvent`][StreamEvent] values ending with a
[`StreamEnd`][StreamEnd] that carries the final
[`FinishReason`][FinishReason] and token [`Usage`][Usage].

Example:
    ```python
    from openfactcheck.chat import (
        ChatClient,
        OpenAIConfig,
        StreamEnd,
        TextDelta,
        UserMessage,
    )

    client = ChatClient(config=OpenAIConfig(model="gpt-4o"))

    # Non-streaming.
    response = client.completion([UserMessage(content="Hello")])
    print(response.message.content)

    # Streaming.
    for event in client.stream([UserMessage(content="Tell me a joke")]):
        match event:
            case TextDelta(content=chunk):
                print(chunk, end="")
            case StreamEnd(finish_reason=reason):
                print()
                print(f"done: {reason}")
    ```
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Discriminator

from openfactcheck.chat.messages import AssistantMessage  # noqa: TC001 - Pydantic needs this at runtime.


class Usage(BaseModel):
    """Token usage reported by a single model call."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    input_tokens: int
    """Tokens consumed by the prompt."""

    output_tokens: int
    """Tokens generated in the response."""


class FinishReason(StrEnum):
    """Why the model stopped generating.

    Values correspond to stop reasons reported by every supported provider,
    normalized into a single enum.
    """

    STOP = "stop"
    """Natural stop: the model decided the response was complete."""

    TOOL_CALLS = "tool_calls"
    """The model emitted tool calls and is waiting for their results before continuing."""

    LENGTH = "length"
    """Response was truncated to honor ``max_output_tokens`` or the provider's maximum."""

    CONTENT_FILTER = "content_filter"
    """Response was blocked or truncated by the provider's content policy."""

    ERROR = "error"
    """Generation aborted due to a provider or transport error."""


class ChatResponse(BaseModel):
    """Complete response from a non-streaming model call.

    Example:
        ```python
        response = client.completion([UserMessage(content="Hello")])
        print(response.message.content, response.usage.output_tokens)
        ```
    """

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    message: AssistantMessage
    """The model's reply."""

    model: str
    """Identifier of the model that produced the response, e.g. ``"gpt-4o"``."""

    provider: Literal["openai", "anthropic"]
    """Provider that served the response."""

    usage: Usage | None = None
    """Token counts, or ``None`` when the provider didn't report usage."""

    finish_reason: FinishReason | None = None
    """Why the model stopped, or ``None`` when the provider didn't report a reason."""


# ---------------------------------------------------------------------------
# Streaming events
# ---------------------------------------------------------------------------


class TextDelta(BaseModel):
    """A text fragment arriving during a streaming call.

    Concatenate every ``TextDelta.content`` in emission order to
    reconstruct the final message body.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    type: Literal["text"] = "text"
    """Event tag identifying this as a text chunk."""

    content: str
    """Text fragment from the model."""


class StreamEnd(BaseModel):
    """Terminal event for a stream. Carries completion metadata.

    Always emitted exactly once as the last event in the stream, even on
    non-``stop`` terminations.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    type: Literal["end"] = "end"
    """Event tag identifying this as the stream terminator."""

    finish_reason: FinishReason | None = None
    """Why the model stopped, or ``None`` when the provider didn't report a reason."""

    usage: Usage | None = None
    """Token counts, or ``None`` when the provider didn't report usage."""


StreamEvent = Annotated[
    TextDelta | StreamEnd,
    Discriminator("type"),
]
"""Events yielded by streaming calls.

[`StreamEnd`][StreamEnd] is always the last event; every event before it is
a [`TextDelta`][TextDelta].
"""

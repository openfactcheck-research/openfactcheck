"""Message types for the chat layer.

Build a conversation as a list of messages, each carrying a ``role`` that
identifies the sender, and pass it to a chat client to get a completion or
stream. Backend implementations convert messages to and from the underlying
provider format at the boundary.

Example:
    ```python
    from openfactcheck.messages import (
        AssistantMessage,
        SystemMessage,
        ToolCall,
        ToolMessage,
        UserMessage,
    )

    conversation = [
        SystemMessage(content="You are a fact-checker."),
        UserMessage(content="Is the sky blue?"),
        AssistantMessage(
            content="",
            tool_calls=[ToolCall(id="call_1", name="search", arguments='{"q": "sky color"}')],
        ),
        ToolMessage(content="Rayleigh scattering makes the sky blue.", tool_call_id="call_1"),
        AssistantMessage(content="Yes, due to Rayleigh scattering."),
    ]
    ```
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Discriminator


class ToolCall(BaseModel):
    """A tool invocation requested by the model.

    Emitted as part of an [`AssistantMessage`][AssistantMessage] when the
    model decides to call a tool. Match the resulting
    [`ToolMessage`][ToolMessage] back to this call by ``id``.

    Example:
        ```python
        call = ToolCall(id="call_1", name="search", arguments='{"q": "sky color"}')
        ```
    """

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    id: str
    """Unique identifier for this call, referenced by the matching [`ToolMessage`][ToolMessage]."""

    name: str
    """Name of the tool the model is asking to invoke."""

    arguments: str
    """JSON-encoded arguments for the tool.

    Kept as a string so arbitrary JSON round-trips across providers without
    type loss.
    """


class SystemMessage(BaseModel):
    """Instruction to the model, typically placed at the top of a conversation.

    Example:
        ```python
        SystemMessage(content="You are a fact-checker. Answer in one sentence.")
        ```
    """

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    role: Literal["system"] = "system"
    """Role tag identifying this as a system instruction."""

    content: str
    """Text of the system instruction."""


class UserMessage(BaseModel):
    """Input from the end user.

    Example:
        ```python
        UserMessage(content="Is the sky really blue?")
        ```
    """

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    role: Literal["user"] = "user"
    """Role tag identifying this as user input."""

    content: str
    """Text of the user's message."""


class AssistantMessage(BaseModel):
    """Reply from the model.

    Carries the natural-language response plus any tool calls the model
    wants to invoke before continuing.

    Example:
        ```python
        AssistantMessage(content="Yes, due to Rayleigh scattering.")
        ```
    """

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    role: Literal["assistant"] = "assistant"
    """Role tag identifying this as a model reply."""

    content: str
    """Text of the model's reply. May be empty when ``tool_calls`` is populated."""

    tool_calls: list[ToolCall] | None = None
    """Tools the model is requesting. ``None`` when the model replied with text only."""


class ToolMessage(BaseModel):
    """Result of a tool invocation, fed back to the model.

    Example:
        ```python
        ToolMessage(content="Rayleigh scattering makes the sky blue.", tool_call_id="call_1")
        ```
    """

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    role: Literal["tool"] = "tool"
    """Role tag identifying this as a tool result."""

    content: str
    """Text of the tool's output. Typically a JSON string or a natural-language summary."""

    tool_call_id: str
    """Identifier of the [`ToolCall`][ToolCall] this result is answering."""


Message = Annotated[
    SystemMessage | UserMessage | AssistantMessage | ToolMessage,
    Discriminator("role"),
]
"""Union of every message type that can appear in a conversation.

Callers build a ``list[Message]`` and pass it to a chat client; branch on
``role`` to distinguish the concrete type.
"""

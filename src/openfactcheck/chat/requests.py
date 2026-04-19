"""Request types for the chat layer.

A [`ChatRequest`][ChatRequest] bundles the messages, model configuration,
and runtime settings for a single chat call. End users rarely construct one
directly; [`ChatClient`][ChatClient] builds a request per call. Request
values surface when writing a custom [`ChatBackend`][ChatBackend].

Example:
    ```python
    from openfactcheck.chat import (
        ChatRequest,
        OpenAIConfig,
        RuntimeConfig,
        UserMessage,
    )

    request = ChatRequest(
        messages=[UserMessage(content="Hello")],
        config=OpenAIConfig(model="gpt-4o"),
        runtime=RuntimeConfig(timeout=30.0),
    )
    ```
"""

from pydantic import BaseModel, ConfigDict, Field

from openfactcheck.chat.config import ModelConfig, RuntimeConfig
from openfactcheck.chat.messages import Message


class ChatRequest(BaseModel):
    """A complete request for a single chat completion or stream.

    Example:
        ```python
        request = ChatRequest(
            messages=[UserMessage(content="Hello")],
            config=OpenAIConfig(model="gpt-4o"),
        )
        ```
    """

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    messages: list[Message]
    """Conversation history up to the point where the model should respond."""

    config: ModelConfig
    """Model-specific settings: provider, model name, and sampling parameters."""

    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    """Execution-level settings such as timeout and retries.

    Defaults to an empty [`RuntimeConfig`][RuntimeConfig].
    """

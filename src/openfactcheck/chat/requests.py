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
    )
    from openfactcheck.messages import UserMessage

    request = ChatRequest(
        messages=[UserMessage(content="Hello")],
        config=OpenAIConfig(model="gpt-4o"),
        runtime=RuntimeConfig(timeout=30.0),
    )
    ```
"""

from pydantic import BaseModel, ConfigDict, Field

from openfactcheck.chat.config import ModelConfig, RuntimeConfig
from openfactcheck.messages import Message


class ResponseFormat(BaseModel):
    """Schema a structured-output reply must conform to.

    Built from a Pydantic model by
    [`ChatClient.completion_as`][ChatClient.completion_as] and carried on the
    request so a backend can enforce it with the provider's native mechanism.
    The reply's content is then the JSON matching this schema.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", use_attribute_docstrings=True)

    name: str
    """Schema name, used as the json_schema name or the forced tool name."""

    json_schema: dict[str, object]
    """The JSON Schema the reply must satisfy, from the model's ``model_json_schema()``."""

    strict: bool = True
    """Whether to request strict schema enforcement where the provider supports it."""


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

    response_format: ResponseFormat | None = None
    """Optional structured-output schema.

    When set, the backend asks the model to return JSON matching the schema,
    and the reply's content is that JSON string. Unset for plain text replies.
    """

"""Public API for the chat layer.

Build a [`ChatClient`][ChatClient] with a provider-specific configuration
(for example [`OpenAIConfig`][OpenAIConfig]), send it a list of
[`Message`][Message] values, and receive a [`ChatResponse`][ChatResponse] or
a stream of [`StreamEvent`][StreamEvent] values. Failures raise
[`ChatModelError`][ChatModelError] subclasses.

Import everything from ``openfactcheck.chat`` directly; submodule paths are
not part of the public API.

Example:
    ```python
    from openfactcheck.chat import (
        ChatClient,
        OpenAIConfig,
        SystemMessage,
        UserMessage,
    )

    client = ChatClient(config=OpenAIConfig(model="gpt-4o"))
    response = client.completion(
        [
            SystemMessage(content="You are a fact-checker."),
            UserMessage(content="Is the sky blue?"),
        ]
    )
    print(response.message.content)
    ```
"""

from openfactcheck.chat.backends.anthropic import AnthropicBackend
from openfactcheck.chat.backends.base import ChatBackend
from openfactcheck.chat.backends.langchain import LangChainBackend
from openfactcheck.chat.backends.litellm import LiteLLMBackend
from openfactcheck.chat.backends.openai import OpenAIBackend
from openfactcheck.chat.client import ChatClient
from openfactcheck.chat.config import (
    AnthropicConfig,
    ModelConfig,
    OpenAIConfig,
    ProviderName,
    RuntimeConfig,
)
from openfactcheck.chat.errors import (
    AuthenticationError,
    ChatModelError,
    ProviderError,
    ProviderNotFoundError,
    RateLimitError,
    UnsupportedFeatureError,
)
from openfactcheck.chat.messages import (
    AssistantMessage,
    Message,
    SystemMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from openfactcheck.chat.providers.base import BaseProvider, ProviderCapabilities
from openfactcheck.chat.requests import ChatRequest
from openfactcheck.chat.responses import ChatResponse, FinishReason, StreamEnd, StreamEvent, TextDelta, Usage

__all__ = [
    "AnthropicBackend",
    "AnthropicConfig",
    "AssistantMessage",
    "AuthenticationError",
    "BaseProvider",
    "ChatBackend",
    "ChatClient",
    "ChatModelError",
    "ChatRequest",
    "ChatResponse",
    "FinishReason",
    "LangChainBackend",
    "LiteLLMBackend",
    "Message",
    "ModelConfig",
    "OpenAIBackend",
    "OpenAIConfig",
    "ProviderCapabilities",
    "ProviderError",
    "ProviderName",
    "ProviderNotFoundError",
    "RateLimitError",
    "RuntimeConfig",
    "StreamEnd",
    "StreamEvent",
    "SystemMessage",
    "TextDelta",
    "ToolCall",
    "ToolMessage",
    "UnsupportedFeatureError",
    "Usage",
    "UserMessage",
]
